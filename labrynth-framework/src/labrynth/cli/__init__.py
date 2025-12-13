"""Labrynth CLI"""

from labrynth.cli.root import app

# Import submodules to register commands
import labrynth.cli.init  # noqa: F401
import labrynth.cli.server  # noqa: F401
import labrynth.cli.deploy  # noqa: F401

__all__ = ["app"]
