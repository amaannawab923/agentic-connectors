#!/usr/bin/env python3
"""Test script for the real research agent node.

Run with: python test_research_agent.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_research_node():
    """Test the research node with a real connector."""
    from app.orchestrator.nodes.real_agents import research_node
    from app.orchestrator.state import create_initial_state

    # Create initial state for testing
    connector_name = "stripe"  # A well-known API for testing
    state = create_initial_state(
        connector_name=connector_name,
        connector_type="source",
    )

    print("=" * 60)
    print(f"Testing Research Agent for: {connector_name}")
    print("=" * 60)
    print()

    # Call the research node
    result = await research_node(state)

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    # Print the result structure
    if "errors" in result and result["errors"]:
        print(f"ERRORS: {result['errors']}")
    else:
        research_output = result.get("research_output", {})
        print(f"Phase: {result.get('current_phase')}")
        print(f"Document length: {len(research_output.get('full_document', ''))} chars")
        print(f"Duration: {research_output.get('duration_seconds', 0):.1f}s")
        print(f"Tokens used: {research_output.get('tokens_used', 0)}")
        print()
        print("Logs:")
        for log in result.get("logs", []):
            print(f"  {log}")

        # Print first 2000 chars of the research document
        doc = research_output.get("full_document", "")
        if doc:
            print()
            print("=" * 60)
            print("RESEARCH DOCUMENT (first 2000 chars)")
            print("=" * 60)
            print(doc[:2000])
            if len(doc) > 2000:
                print(f"\n... ({len(doc) - 2000} more chars)")

    return result


if __name__ == "__main__":
    result = asyncio.run(test_research_node())
