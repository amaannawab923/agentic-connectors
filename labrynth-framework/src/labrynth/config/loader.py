"""Configuration loader for Labrynth projects."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class AgentsConfig:
    """Configuration for agent discovery."""

    paths: List[str] = field(default_factory=lambda: ["agents/"])
    auto_discover: bool = True
    watch: bool = False


@dataclass
class ServerConfig:
    """Configuration for the server."""

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False


@dataclass
class LabrynthConfig:
    """Root configuration for a Labrynth project."""

    name: str = "labrynth-project"
    version: str = "0.1.0"
    agents: AgentsConfig = field(default_factory=AgentsConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def load_config(project_path: Path) -> LabrynthConfig:
    """
    Load configuration from labrynth.yaml.

    Args:
        project_path: Path to the project root.

    Returns:
        Parsed configuration object.
    """
    config_file = project_path / "labrynth.yaml"

    if not config_file.exists():
        return LabrynthConfig()

    with open(config_file) as f:
        data = yaml.safe_load(f) or {}

    # Parse nested configs
    agents_data = data.get("agents", {})
    server_data = data.get("server", {})

    return LabrynthConfig(
        name=data.get("name", "labrynth-project"),
        version=data.get("version", "0.1.0"),
        agents=AgentsConfig(
            paths=agents_data.get("paths", ["agents/"]),
            auto_discover=agents_data.get("auto_discover", True),
            watch=agents_data.get("watch", False),
        ),
        server=ServerConfig(
            host=server_data.get("host", "127.0.0.1"),
            port=server_data.get("port", 8000),
            debug=server_data.get("debug", False),
        ),
    )
