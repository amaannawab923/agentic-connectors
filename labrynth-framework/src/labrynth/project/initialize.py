"""Project initialization functions."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

VALID_TEMPLATES = ["basic", "blank"]


def get_git_info() -> Dict[str, Any]:
    """Get git repository info if available."""
    info: Dict[str, Any] = {"is_git": False, "repository": None, "branch": None}

    try:
        # Check for remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            info["is_git"] = True
            info["repository"] = result.stdout.strip()

        # Check for branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()
    except Exception:
        pass

    return info


def initialize_project(
    path: Path,
    name: Optional[str] = None,
    template: Optional[str] = None,
) -> List[str]:
    """
    Initialize a Labrynth project.

    Args:
        path: Directory to initialize
        name: Project name (defaults to directory name)
        template: Template name ("basic", "blank") or None for minimal init

    Returns:
        List of created file paths (relative to project)
    """
    # Validate template
    if template and template not in VALID_TEMPLATES:
        available = ", ".join(VALID_TEMPLATES)
        raise ValueError(f"Unknown template '{template}'. Available: {available}")

    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=True)

    project_name = name or path.name
    created_files: List[str] = []

    # ALWAYS create config files (minimal init)
    config_files = create_config_files(path, project_name)
    created_files.extend(config_files)

    # Only create scaffolding if template is specified
    if template:
        # Create .labrynth/ directory
        if create_data_directory(path):
            created_files.append(".labrynth/")

        # Create agents/ directory
        agent_files = create_agents_directory(path, template)
        created_files.extend(agent_files)

        # Create .gitignore
        if create_gitignore(path):
            created_files.append(".gitignore")

    return created_files


def create_config_files(path: Path, name: str) -> List[str]:
    """Create labrynth.yaml and .labrynthignore."""
    created: List[str] = []

    # Get git info for config
    git_info = get_git_info()

    # Create labrynth.yaml
    config_file = path / "labrynth.yaml"
    if not config_file.exists():
        config: Dict[str, Any] = {
            "name": name,
            "version": "0.1.0",
            "agents": {
                "paths": ["agents/"],
                "auto_discover": True,
                "watch": True,
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000,
                "debug": False,
            },
        }

        # Add git info if available
        if git_info["repository"]:
            config["repository"] = {
                "url": git_info["repository"],
                "branch": git_info["branch"] or "main",
            }

        with config_file.open("w") as f:
            f.write("# Labrynth Project Configuration\n")
            f.write("# https://github.com/your-org/labrynth\n\n")
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        created.append("labrynth.yaml")

    # Create .labrynthignore
    ignore_file = path / ".labrynthignore"
    if not ignore_file.exists():
        content = """# Labrynth artifacts
.labrynth/

# Python artifacts
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
*.egg

# Type checking
.mypy_cache/
.pytype/
.pyre/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Environments
.env
.venv/
venv/
env/
.python-version

# Editors
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# VCS
.git/
"""
        ignore_file.write_text(content)
        created.append(".labrynthignore")

    return created


def create_data_directory(path: Path) -> bool:
    """Create .labrynth/ hidden directory."""
    data_dir = path / ".labrynth"

    if data_dir.exists():
        return False

    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / ".gitkeep").touch()

    return True


def create_agents_directory(path: Path, template: str) -> List[str]:
    """Create agents/ directory based on template."""
    agents_dir = path / "agents"
    created: List[str] = []

    if not agents_dir.exists():
        agents_dir.mkdir(parents=True, exist_ok=True)
        created.append("agents/")

    # Always create __init__.py
    init_file = agents_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Labrynth agents for this project."""\n')
        created.append("agents/__init__.py")

    # Create example.py only for "basic" template
    if template == "basic":
        example_file = agents_dir / "example.py"
        if not example_file.exists():
            example_content = '''"""Example agents demonstrating Labrynth usage."""

from labrynth import agent


@agent(
    name="Hello World",
    description="A simple example agent that greets the world",
    tags=["example", "demo"]
)
def hello_world():
    """Say hello to the world."""
    print("Hello from Agent!")
    return {"message": "Hello, World!"}


@agent(
    name="Greeter",
    description="An agent that greets someone by name",
    tags=["example", "greeting"]
)
def greeter(name: str = "Friend"):
    """Greet someone by name.

    Args:
        name: The name of the person to greet
    """
    greeting = f"Hello, {name}!"
    print(greeting)
    return {"greeting": greeting}


@agent
def simple_agent():
    """A minimal agent using the bare decorator."""
    print("I am a simple agent!")
    return {"status": "executed"}
'''
            example_file.write_text(example_content)
            created.append("agents/example.py")

    return created


def create_gitignore(path: Path) -> bool:
    """Create .gitignore if it doesn't exist."""
    gitignore_file = path / ".gitignore"

    if gitignore_file.exists():
        return False

    content = """# Labrynth
.labrynth/

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# Environments
.env
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
"""
    gitignore_file.write_text(content)
    return True
