"""Pipeline nodes (agents) v2.

This module contains the node functions for the LangGraph pipeline.
Currently using mock agents - replace with real Claude Agent SDK calls.

Pipeline uses 7 nodes:
    - research_node: Research API documentation (handles re-research)
    - generator_node: Generate/fix/improve code
    - tester_node: Run tests and fix invalid tests
    - test_reviewer_node: Validate test quality, route based on results
    - reviewer_node: Review code quality, route based on coverage
    - publisher_node: Publish to repository (handles DEGRADED MODE)
    - failed_node: Handle pipeline failures (defined in pipeline.py)
"""

from .mock_agents import (
    research_node,
    generator_node,
    tester_node,
    test_reviewer_node,
    reviewer_node,
    publisher_node,
)

__all__ = [
    "research_node",
    "generator_node",
    "tester_node",
    "test_reviewer_node",
    "reviewer_node",
    "publisher_node",
]
