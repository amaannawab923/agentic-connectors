"""Labrynth init command."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from labrynth.cli.root import app
from labrynth.project.initialize import initialize_project, VALID_TEMPLATES

console = Console()


@app.command()
def init(
    path: Path = typer.Argument(
        ".",
        help="Directory to initialize as a Labrynth project",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Project name (defaults to directory name)",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help=f"Template for scaffolding ({', '.join(VALID_TEMPLATES)}). "
        "Omit for minimal init.",
    ),
) -> None:
    """
    Initialize a new Labrynth project.

    Without --template: Creates only config files (labrynth.yaml, .labrynthignore)

    With --template: Creates full project structure with example files
    """
    project_path = Path(path).resolve()
    project_name = name or project_path.name

    # Header
    console.print()
    console.print(
        f"Initializing Labrynth project: [bold cyan]{project_name}[/bold cyan]"
    )
    console.print(f"[dim]Path: {project_path}[/dim]")

    if template:
        console.print(f"[dim]Template: {template}[/dim]")
    else:
        console.print("[dim]Mode: minimal (config only)[/dim]")

    console.print()

    try:
        created_files = initialize_project(
            path=project_path,
            name=project_name,
            template=template,
        )

        if created_files:
            console.print("[green]Created:[/green]")
            for f in created_files:
                console.print(f"  {f}")
        else:
            console.print(
                "[yellow]No new files created (project already initialized)[/yellow]"
            )

        console.print()
        console.print("[bold green]Labrynth project initialized![/bold green]")
        console.print()
        console.print("[dim]Next steps:[/dim]")

        if template == "basic":
            console.print(f"  1. cd {project_path.name}")
            console.print("  2. Edit agents/example.py")
            console.print("  3. labrynth server start")
        elif template == "blank":
            console.print(f"  1. cd {project_path.name}")
            console.print("  2. Create your agents in agents/")
            console.print("  3. labrynth server start")
        else:
            console.print(f"  1. cd {project_path.name}")
            console.print("  2. Create agents with @agent decorator")
            console.print("  3. labrynth server start")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
