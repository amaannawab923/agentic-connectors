"""Agent registry for tracking registered agents."""

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from labrynth.core.agent import AgentInfo

# Global registry for all registered agents
_AGENT_REGISTRY: Dict[str, "AgentInfo"] = {}


def register_agent(agent: "AgentInfo") -> None:
    """
    Register an agent in the global registry.

    Args:
        agent: The AgentInfo object to register.
    """
    _AGENT_REGISTRY[agent.name] = agent


def get_agent(name: str) -> Optional["AgentInfo"]:
    """
    Get an agent by name.

    Args:
        name: The name of the agent to retrieve.

    Returns:
        The AgentInfo object if found, None otherwise.
    """
    return _AGENT_REGISTRY.get(name)


def get_agents() -> Dict[str, "AgentInfo"]:
    """
    Get all registered agents.

    Returns:
        A copy of the agent registry dictionary.
    """
    return _AGENT_REGISTRY.copy()


def clear_registry() -> None:
    """Clear all registered agents from the registry."""
    _AGENT_REGISTRY.clear()
