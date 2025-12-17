"""Labrynth server commands."""

import os
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich.console import Console

from labrynth import __version__
from labrynth.cli.root import app
from labrynth.config.loader import load_config

console = Console()

server_app = typer.Typer(
    name="server",
    help="Manage the Labrynth server",
)
app.add_typer(server_app)


def print_banner() -> None:
    """Print the Labrynth banner."""
    banner = """
  _          _                     _   _
 | |    __ _| |__  _ __ _   _ _ __ | |_| |__
 | |   / _` | '_ \\| '__| | | | '_ \\| __| '_ \\
 | |__| (_| | |_) | |  | |_| | | | | |_| | | |
 |_____\\__,_|_.__/|_|   \\__, |_| |_|\\__|_| |_|
                        |___/
"""
    console.print(banner, style="cyan")
    console.print(f" Labrynth Server v{__version__}", style="bold")
    console.print()


@server_app.command()
def start(
    host: Optional[str] = typer.Option(
        None,
        "--host",
        "-h",
        help="Host to bind to (overrides config)",
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="Port to bind to (overrides config)",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload on file changes",
    ),
) -> None:
    """Start the Labrynth server."""
    project_path = Path.cwd()

    # Load configuration
    config = load_config(project_path)

    # Override with CLI arguments
    server_host = host or config.server.host
    server_port = port or config.server.port

    # Print banner
    print_banner()

    # Server URLs
    base_url = f"http://{server_host}:{server_port}"
    console.print(f"[bold]Server running at[/bold] {base_url}")
    console.print(f"[dim]API docs at {base_url}/docs[/dim]")
    console.print(f"[dim]Health check at {base_url}/api/health[/dim]")
    console.print()
    console.print("[dim]Press CTRL+C to stop[/dim]")
    console.print()

    # Start server
    uvicorn.run(
        "labrynth.server.app:create_app",
        factory=True,
        host=server_host,
        port=server_port,
        reload=reload,
        log_level="info",
    )
