"""FastAPI application factory for Labrynth server."""

import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from labrynth import __version__
from labrynth.config.loader import LabrynthConfig, load_config
from labrynth.database import AgentRepository, get_session, init_database

# Environment variable for dev mode
LABRYNTH_DEV_PROJECT_ENV = "LABRYNTH_DEV_PROJECT"

# Global config reference
_config: Optional[LabrynthConfig] = None
_project_path: Optional[Path] = None


def get_config() -> LabrynthConfig:
    """Get the current configuration."""
    if _config is None:
        return LabrynthConfig()
    return _config


def get_dev_project_path() -> Optional[Path]:
    """Get dev project path from environment variable."""
    dev_path = os.environ.get(LABRYNTH_DEV_PROJECT_ENV)
    if dev_path:
        path = Path(dev_path)
        if path.exists() and (path / "labrynth.yaml").exists():
            return path
    return None


async def auto_deploy_dev_project(project_path: Path) -> int:
    """Auto-deploy agents from dev project to database."""
    from labrynth.core.registry import clear_registry, get_agents
    from labrynth.discovery.importer import discover_agents

    # Load project config
    config = load_config(project_path)

    # Generate project ID
    path_str = str(project_path.resolve())
    project_id = hashlib.md5(path_str.encode()).hexdigest()[:8]

    print(f"[Dev Mode] Auto-deploying from: {project_path}")
    print(f"[Dev Mode] Project ID: {project_id}")

    # Clear any existing agents in memory registry
    clear_registry()

    # Discover agents
    agent_count, imported_files = discover_agents(config.agents.paths, project_path)

    if agent_count == 0:
        print("[Dev Mode] No agents found to deploy")
        return 0

    print(f"[Dev Mode] Found {agent_count} agent(s)")

    # Get agents from registry and deploy to database
    agents = get_agents()
    deployed_count = 0

    async with get_session() as session:
        repo = AgentRepository(session)

        for name, agent_info in agents.items():
            # Compute entrypoint
            if imported_files:
                module_path = imported_files[0].replace("/", ".").replace(".py", "")
                entrypoint = f"{module_path}:{name.replace('-', '_')}"
            else:
                entrypoint = f"unknown:{name}"

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
            print(f"[Dev Mode]   - {agent_info.name}")

    print(f"[Dev Mode] Deployed {deployed_count} agent(s)")
    return deployed_count


def create_app(
    project_path: Optional[Path] = None,
    config: Optional[LabrynthConfig] = None,
) -> FastAPI:
    """
    Create the FastAPI application.

    Args:
        project_path: Path to the project root. Defaults to cwd.
        config: Optional pre-loaded configuration.

    Returns:
        Configured FastAPI application.
    """
    global _config, _project_path

    _project_path = project_path or Path.cwd()
    _config = config or load_config(_project_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Handle startup and shutdown events."""
        # STARTUP: Initialize database
        await init_database()
        print("Database initialized")

        # Check for dev mode auto-deploy
        dev_project = get_dev_project_path()
        if dev_project:
            await auto_deploy_dev_project(dev_project)

        yield
        # SHUTDOWN

    app = FastAPI(
        title="Labrynth Server",
        description="Agentic Pipeline Framework API",
        version=__version__,
        lifespan=lifespan,
    )

    # Add CORS middleware for future UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    from labrynth.server.api import health, agents

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(agents.router, prefix="/api", tags=["agents"])

    # UI settings endpoint
    @app.get("/api/ui-settings")
    def ui_settings():
        """Provide configuration to the UI."""
        return {
            "api_url": "/api",
            "version": __version__,
        }

    # Serve UI static files (if built)
    ui_path = Path(__file__).parent / "ui"
    if ui_path.exists() and (ui_path / "index.html").exists():
        from labrynth.server.static import SPAStaticFiles

        app.mount("/", SPAStaticFiles(directory=ui_path, html=True), name="ui")

    return app
