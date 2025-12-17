"""Deploy command for Labrynth CLI."""

import asyncio
import hashlib
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from labrynth.cli.root import app
from labrynth.config.loader import load_config
from labrynth.core.registry import clear_registry, get_agents
from labrynth.database import AgentRepository, get_session, init_database
from labrynth.discovery.importer import discover_agents

console = Console()


def get_project_id(project_path: Path) -> str:
    """Generate a unique project ID from the project path."""
    # Use first 8 chars of md5 hash of absolute path
    path_str = str(project_path.resolve())
    return hashlib.md5(path_str.encode()).hexdigest()[:8]


def get_entrypoint(agent_name: str, imported_files: list[str], project_root: Path) -> str:
    """
    Get the entrypoint string for an agent.

    Format: module.path:function_name
    """
    # For now, we'll use the agent name as the function name
    # This works because agents are registered with their function names
    # In a more robust implementation, we'd track file -> agent mappings
    if imported_files:
        # Use the first file's module path as the base
        # This is a simplification - in practice you'd track which file
        # each agent came from
        module_path = imported_files[0].replace("/", ".").replace(".py", "")
        return f"{module_path}:{agent_name.replace('-', '_')}"
    return f"unknown:{agent_name}"


async def deploy_agents_to_db(project_path: Path) -> int:
    """Deploy discovered agents to the database."""
    # Load project config
    config = load_config(project_path)
    project_id = get_project_id(project_path)

    console.print(f"\n[bold blue]Deploying agents from:[/] {project_path}")
    console.print(f"[dim]Project ID: {project_id}[/]")
    console.print(f"[dim]Project name: {config.name}[/]\n")

    # Clear any existing agents in memory registry
    clear_registry()

    # Discover agents
    agent_count, imported_files = discover_agents(config.agents.paths, project_path)

    if agent_count == 0:
        console.print("[yellow]No agents found to deploy.[/]")
        console.print(f"[dim]Searched paths: {config.agents.paths}[/]")
        return 0

    console.print(f"[green]Found {agent_count} agent(s)[/]\n")

    # Initialize database
    await init_database()

    # Get agents from registry and deploy to database
    agents = get_agents()
    deployed_count = 0
    removed_count = 0

    async with get_session() as session:
        repo = AgentRepository(session)

        # Get current agent names from source
        current_agent_names = {agent_info.name for agent_info in agents.values()}

        # Get existing agents from database for this project
        existing_agents = await repo.get_by_project(project_id)
        existing_agent_names = {agent.name for agent in existing_agents}

        # Find and remove stale agents (in DB but not in source)
        stale_agent_names = existing_agent_names - current_agent_names
        for agent in existing_agents:
            if agent.name in stale_agent_names:
                await repo.delete(agent.id)
                removed_count += 1
                console.print(f"[yellow]Removed stale agent:[/] {agent.name}")

        for name, agent_info in agents.items():
            # Compute entrypoint
            entrypoint = get_entrypoint(name, imported_files, project_path)

            # Convert parameters to serializable format
            params_dict = {
                pname: pinfo.to_dict()
                for pname, pinfo in agent_info.parameters.items()
            }

            # Upsert agent
            await repo.upsert(
                project_id=project_id,
                name=agent_info.name,
                description=agent_info.description,
                entrypoint=entrypoint,
                tags=agent_info.tags,
                parameters=params_dict,
            )
            deployed_count += 1

    # Display results
    table = Table(title="Deployed Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Tags", style="yellow")
    table.add_column("Entrypoint", style="dim")

    for name, agent_info in agents.items():
        entrypoint = get_entrypoint(name, imported_files, project_path)
        table.add_row(
            agent_info.name,
            agent_info.description[:50] + "..." if len(agent_info.description) > 50 else agent_info.description,
            ", ".join(agent_info.tags) or "-",
            entrypoint,
        )

    console.print(table)
    console.print(f"\n[bold green]Successfully deployed {deployed_count} agent(s)![/]")
    if removed_count > 0:
        console.print(f"[yellow]Removed {removed_count} stale agent(s)[/]")

    return deployed_count


@app.command()
def deploy(
    path: str = typer.Argument(
        ".",
        help="Path to the Labrynth project to deploy",
    ),
) -> None:
    """
    Deploy agents from a Labrynth project to the database.

    This command discovers all agents in the project and stores them
    in the global Labrynth database (~/.labrynth/labrynth.db).
    """
    project_path = Path(path).resolve()

    # Validate project
    if not project_path.exists():
        console.print(f"[red]Error: Path does not exist: {project_path}[/]")
        raise typer.Exit(1)

    config_file = project_path / "labrynth.yaml"
    if not config_file.exists():
        console.print(f"[red]Error: Not a Labrynth project (no labrynth.yaml found)[/]")
        console.print(f"[dim]Run 'labrynth init' to create a new project.[/]")
        raise typer.Exit(1)

    # Run async deployment
    deployed = asyncio.run(deploy_agents_to_db(project_path))

    if deployed > 0:
        console.print("\n[dim]Start the server with 'labrynth server start' to access deployed agents.[/]")
