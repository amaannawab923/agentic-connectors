"""Agent discovery via dynamic imports."""

import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple

from labrynth.core.registry import get_agents


def discover_agents(
    paths: List[str],
    project_root: Path,
) -> Tuple[int, List[str]]:
    """
    Discover agents by importing Python files from configured paths.

    Args:
        paths: List of relative paths to scan for agents.
        project_root: Root directory of the project.

    Returns:
        Tuple of (agent_count, list_of_imported_files).
    """
    imported_files = []
    initial_count = len(get_agents())

    # Add project root to sys.path for imports
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    for path_str in paths:
        agent_path = project_root / path_str

        if not agent_path.exists():
            continue

        for py_file in sorted(agent_path.glob("**/*.py")):
            # Skip private files
            if py_file.name.startswith("_"):
                continue

            try:
                # Create a unique module name
                relative_path = py_file.relative_to(project_root)
                module_name = str(relative_path.with_suffix("")).replace("/", ".")

                # Create module spec
                spec = importlib.util.spec_from_file_location(
                    module_name, py_file
                )

                if spec is None or spec.loader is None:
                    continue

                # Load and execute module
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                imported_files.append(str(relative_path))

            except Exception as e:
                # Log error but continue with other files
                print(f"Error importing {py_file}: {e}")

    final_count = len(get_agents())
    agents_discovered = final_count - initial_count

    return agents_discovered, imported_files
