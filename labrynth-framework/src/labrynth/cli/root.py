"""Root CLI application for Labrynth"""

import typer
from rich.console import Console

app = typer.Typer(
    name="labrynth",
    help="Labrynth - Agentic Pipeline Framework. Build and visualize agentic pipelines.",
    no_args_is_help=True,
    add_completion=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from labrynth import __version__
        console.print(f"Labrynth v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """
    Labrynth - Agentic Pipeline Framework.

    Build and visualize agentic pipelines with ease.
    """
    pass
