"""Labrynth - Agentic Pipeline Framework"""

__version__ = "0.1.0"

# Core exports - Agent decorator and registry
from labrynth.core.agent import agent, AgentInfo
from labrynth.core.registry import get_agents, get_agent, clear_registry

__all__ = [
    "__version__",
    # Agent decorator
    "agent",
    "AgentInfo",
    # Registry functions
    "get_agents",
    "get_agent",
    "clear_registry",
]
