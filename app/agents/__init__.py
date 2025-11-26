"""Agent implementations for the Connector Generator.

This module provides agents for connector generation:
- BaseAgent: Abstract base class with Anthropic API client
- ResearchAgent: API documentation research
- GeneratorAgent: Code generation
- TesterAgent: Test execution
- ReviewerAgent: Code review
- PublisherAgent: Git operations
"""

from .base import BaseAgent
from .research import ResearchAgent
from .generator import GeneratorAgent
from .tester import TesterAgent, TesterMode
from .reviewer import ReviewerAgent
from .publisher import PublisherAgent

__all__ = [
    # Base agent
    "BaseAgent",
    # Specialized agents
    "ResearchAgent",
    "GeneratorAgent",
    "TesterAgent",
    "TesterMode",
    "ReviewerAgent",
    "PublisherAgent",
]
