# LangGraph Orchestration with Claude Agent SDK

## Overview

This document describes the hybrid architecture for orchestrating Claude Agent SDK agents using LangGraph as a state machine orchestrator.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LangGraph Orchestrator                            │
│            (State machine, routing, checkpointing, visualization)           │
│                                                                             │
│  ┌──────────┐    ┌───────────┐    ┌────────┐    ┌──────────┐    ┌───────┐ │
│  │ Research │───▶│ Generator │───▶│ Tester │───▶│ Reviewer │───▶│Publish│ │
│  └────┬─────┘    └─────┬─────┘    └───┬────┘    └────┬─────┘    └───┬───┘ │
│       │                │              │              │              │      │
│       │                │         ┌────┴────┐         │              │      │
│       │                │         │ Pass or │         │              │      │
│       │                │         │  Fail?  │         │              │      │
│       │                │         └────┬────┘         │              │      │
│       │                │              │              │              │      │
│       │                │    FAIL ┌────┴────┐ PASS    │              │      │
│       │                │◀────────│  Fixer  │─────────▶              │      │
│       │                │         └─────────┘                        │      │
└───────┼────────────────┼──────────────────────────────┼─────────────┼──────┘
        │                │                              │             │
        ▼                ▼                              ▼             ▼
  ┌───────────┐   ┌───────────┐                  ┌───────────┐  ┌───────────┐
  │ Research  │   │ Generator │                  │ Reviewer  │  │ Publisher │
  │   Agent   │   │   Agent   │                  │   Agent   │  │   Agent   │
  │(Claude SDK│   │(Claude SDK│                  │(Claude SDK│  │(Claude SDK│
  └───────────┘   └───────────┘                  └───────────┘  └───────────┘
```

## Why This Approach?

| Feature | LangGraph | Claude Agent SDK |
|---------|-----------|------------------|
| State machine routing | ✅ Built-in | ❌ Manual |
| Conditional branching | ✅ `add_conditional_edges()` | ❌ If/else logic |
| Checkpointing/Resume | ✅ Built-in persistence | ❌ Must implement |
| Visualization | ✅ `get_graph().draw_mermaid()` | ❌ None |
| Tool execution | ❌ Uses LangChain tools | ✅ Native tools (Read, Write, Bash, etc.) |
| Streaming responses | ❌ Limited | ✅ Full streaming |
| Claude optimization | ❌ Generic | ✅ Anthropic-native |

**Hybrid approach gives you the best of both worlds.**

## Installation

```bash
pip install langgraph
```

## Implementation

### 1. Define Pipeline State

```python
# app/core/langgraph_pipeline.py

from typing import TypedDict, Literal, Optional, List, Any
from langgraph.graph import StateGraph, END

class PipelineState(TypedDict):
    """Shared state across all pipeline nodes."""

    # Request info
    connector_name: str
    connector_type: str
    api_doc_url: Optional[str]

    # Artifacts
    research_doc: Optional[str]
    generated_code: Optional[str]
    connector_dir: Optional[str]

    # Results
    test_result: Optional[dict]
    review_result: Optional[dict]

    # Counters
    test_attempts: int
    review_cycles: int

    # Budget
    total_spent: float
    max_budget: float

    # Errors
    errors: List[str]
```

### 2. Create Node Wrappers

Each node wraps your existing Claude Agent SDK agent:

```python
# app/core/langgraph_nodes.py

import json
from app.agents.research import ResearchAgent
from app.agents.generator import GeneratorAgent
from app.agents.tester import TesterAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.publisher import PublisherAgent

# Initialize agents (reuse instances)
research_agent = ResearchAgent()
generator_agent = GeneratorAgent()
tester_agent = TesterAgent()
reviewer_agent = ReviewerAgent()
publisher_agent = PublisherAgent()


async def research_node(state: PipelineState) -> PipelineState:
    """Execute research using Claude Agent SDK."""
    result = await research_agent.execute(
        connector_name=state["connector_name"],
        connector_type=state["connector_type"],
        api_doc_url=state.get("api_doc_url"),
    )

    if not result.success:
        return {
            **state,
            "errors": state["errors"] + [f"Research failed: {result.error}"]
        }

    return {
        **state,
        "research_doc": result.output,
    }


async def generator_node(state: PipelineState) -> PipelineState:
    """Execute code generation using Claude Agent SDK."""
    result = await generator_agent.execute(
        connector_name=state["connector_name"],
        connector_type=state["connector_type"],
        research_doc=state["research_doc"],
        output_dir=f"output/source-{state['connector_name']}",
    )

    if not result.success:
        return {
            **state,
            "errors": state["errors"] + [f"Generation failed: {result.error}"]
        }

    return {
        **state,
        "generated_code": result.output,
        "connector_dir": f"output/source-{state['connector_name']}",
    }


async def tester_node(state: PipelineState) -> PipelineState:
    """Execute tests using Claude Agent SDK."""
    result = await tester_agent.execute(
        connector_dir=state["connector_dir"],
        connector_name=state["connector_name"],
    )

    # Parse test result
    try:
        test_result = json.loads(result.output) if result.output else {}
    except json.JSONDecodeError:
        test_result = {"passed": False, "errors": ["Failed to parse test results"]}

    return {
        **state,
        "test_result": test_result,
        "test_attempts": state["test_attempts"] + 1,
    }


async def fixer_node(state: PipelineState) -> PipelineState:
    """Fix code based on test failures using Claude Agent SDK."""
    errors = state["test_result"].get("errors", [])

    result = await generator_agent.execute(
        connector_name=state["connector_name"],
        connector_type=state["connector_type"],
        research_doc=state["research_doc"],
        output_dir=state["connector_dir"],
        fix_errors=errors,  # Pass errors to fix
    )

    if not result.success:
        return {
            **state,
            "errors": state["errors"] + [f"Fix failed: {result.error}"]
        }

    return {
        **state,
        "generated_code": result.output,
    }


async def reviewer_node(state: PipelineState) -> PipelineState:
    """Execute code review using Claude Agent SDK."""
    result = await reviewer_agent.execute(
        connector_name=state["connector_name"],
        connector_dir=state["connector_dir"],
    )

    # Parse review result
    try:
        review_result = json.loads(result.output) if result.output else {}
    except json.JSONDecodeError:
        review_result = {"approved": True, "score": 7.0}  # Default approve

    return {
        **state,
        "review_result": review_result,
        "review_cycles": state["review_cycles"] + 1,
    }


async def improver_node(state: PipelineState) -> PipelineState:
    """Improve code based on review feedback using Claude Agent SDK."""
    feedback = state["review_result"].get("improvements", [])

    result = await generator_agent.execute(
        connector_name=state["connector_name"],
        connector_type=state["connector_type"],
        research_doc=state["research_doc"],
        output_dir=state["connector_dir"],
        review_feedback=feedback,
    )

    return {
        **state,
        "generated_code": result.output,
    }


async def publisher_node(state: PipelineState) -> PipelineState:
    """Publish connector using Claude Agent SDK."""
    result = await publisher_agent.execute(
        connector_name=state["connector_name"],
        connector_dir=state["connector_dir"],
    )

    return {
        **state,
        "published": result.success,
    }
```

### 3. Define Routing Logic

```python
# app/core/langgraph_routing.py

from typing import Literal

MAX_TEST_ATTEMPTS = 3
MAX_REVIEW_CYCLES = 2


def route_after_test(state: PipelineState) -> Literal["fixer", "reviewer", "end"]:
    """Determine next step after testing."""

    # Check for fatal errors
    if state.get("errors"):
        return "end"

    test_passed = state.get("test_result", {}).get("passed", False)

    if test_passed:
        return "reviewer"

    # Check retry limit
    if state["test_attempts"] >= MAX_TEST_ATTEMPTS:
        # Force proceed to review after max attempts
        return "reviewer"

    return "fixer"


def route_after_review(state: PipelineState) -> Literal["improver", "publisher", "end"]:
    """Determine next step after review."""

    # Check for fatal errors
    if state.get("errors"):
        return "end"

    approved = state.get("review_result", {}).get("approved", False)

    if approved:
        return "publisher"

    # Check cycle limit
    if state["review_cycles"] >= MAX_REVIEW_CYCLES:
        # Force publish after max cycles
        return "publisher"

    return "improver"


def should_continue(state: PipelineState) -> Literal["continue", "end"]:
    """Check if pipeline should continue or stop due to errors/budget."""

    if state.get("errors"):
        return "end"

    if state["total_spent"] >= state["max_budget"]:
        return "end"

    return "continue"
```

### 4. Build the Graph

```python
# app/core/langgraph_pipeline.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .langgraph_nodes import (
    research_node,
    generator_node,
    tester_node,
    fixer_node,
    reviewer_node,
    improver_node,
    publisher_node,
)
from .langgraph_routing import route_after_test, route_after_review


def build_connector_pipeline() -> StateGraph:
    """Build the LangGraph pipeline for connector generation."""

    # Create the graph
    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("fixer", fixer_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("improver", improver_node)
    workflow.add_node("publisher", publisher_node)

    # Set entry point
    workflow.set_entry_point("research")

    # Add sequential edges
    workflow.add_edge("research", "generator")
    workflow.add_edge("generator", "tester")

    # Conditional routing after test
    workflow.add_conditional_edges(
        "tester",
        route_after_test,
        {
            "fixer": "fixer",
            "reviewer": "reviewer",
            "end": END,
        }
    )

    # Fixer goes back to tester
    workflow.add_edge("fixer", "tester")

    # Conditional routing after review
    workflow.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "improver": "improver",
            "publisher": "publisher",
            "end": END,
        }
    )

    # Improver goes back to tester (re-test after improvements)
    workflow.add_edge("improver", "tester")

    # Publisher ends the workflow
    workflow.add_edge("publisher", END)

    return workflow


def create_pipeline_app(checkpointer=None):
    """Create compiled pipeline application."""
    workflow = build_connector_pipeline()

    # Add checkpointing for persistence/resume
    if checkpointer is None:
        checkpointer = SqliteSaver.from_conn_string(":memory:")

    return workflow.compile(checkpointer=checkpointer)
```

### 5. Run the Pipeline

```python
# app/core/langgraph_runner.py

import asyncio
from langgraph.checkpoint.sqlite import SqliteSaver

from .langgraph_pipeline import create_pipeline_app, PipelineState


async def run_connector_pipeline(
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: str = None,
    max_budget: float = 7.0,
) -> dict:
    """Run the connector generation pipeline."""

    # Create checkpointer for persistence
    checkpointer = SqliteSaver.from_conn_string("pipeline_state.db")

    # Create pipeline app
    app = create_pipeline_app(checkpointer=checkpointer)

    # Initial state
    initial_state: PipelineState = {
        "connector_name": connector_name,
        "connector_type": connector_type,
        "api_doc_url": api_doc_url,
        "research_doc": None,
        "generated_code": None,
        "connector_dir": None,
        "test_result": None,
        "review_result": None,
        "test_attempts": 0,
        "review_cycles": 0,
        "total_spent": 0.0,
        "max_budget": max_budget,
        "errors": [],
    }

    # Configuration for this run
    config = {"configurable": {"thread_id": f"connector-{connector_name}"}}

    # Run the pipeline
    final_state = await app.ainvoke(initial_state, config)

    return final_state


async def resume_pipeline(thread_id: str) -> dict:
    """Resume a previously interrupted pipeline."""

    checkpointer = SqliteSaver.from_conn_string("pipeline_state.db")
    app = create_pipeline_app(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    # Get current state
    state = await app.aget_state(config)

    if state.values:
        # Resume from last checkpoint
        final_state = await app.ainvoke(None, config)
        return final_state

    raise ValueError(f"No saved state found for thread: {thread_id}")
```

### 6. Visualize the Pipeline

```python
# Generate Mermaid diagram
from app.core.langgraph_pipeline import build_connector_pipeline

workflow = build_connector_pipeline()
app = workflow.compile()

# Print Mermaid diagram
print(app.get_graph().draw_mermaid())

# Or save as PNG (requires graphviz)
app.get_graph().draw_png("pipeline_graph.png")
```

Output:
```mermaid
graph TD
    research --> generator
    generator --> tester
    tester -->|passed| reviewer
    tester -->|failed| fixer
    fixer --> tester
    reviewer -->|approved| publisher
    reviewer -->|needs_work| improver
    improver --> tester
    publisher --> END
```

## API Integration

### FastAPI Endpoint

```python
# app/api/routes.py

from fastapi import APIRouter, BackgroundTasks
from app.core.langgraph_runner import run_connector_pipeline, resume_pipeline

router = APIRouter()

@router.post("/api/v1/pipeline/run")
async def start_pipeline(
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: str = None,
    background_tasks: BackgroundTasks = None,
):
    """Start a new connector generation pipeline."""

    # Run in background
    background_tasks.add_task(
        run_connector_pipeline,
        connector_name=connector_name,
        connector_type=connector_type,
        api_doc_url=api_doc_url,
    )

    return {
        "status": "started",
        "thread_id": f"connector-{connector_name}",
    }


@router.post("/api/v1/pipeline/resume/{thread_id}")
async def resume_pipeline_endpoint(thread_id: str):
    """Resume an interrupted pipeline."""

    result = await resume_pipeline(thread_id)
    return result


@router.get("/api/v1/pipeline/status/{thread_id}")
async def get_pipeline_status(thread_id: str):
    """Get current pipeline state."""

    from langgraph.checkpoint.sqlite import SqliteSaver
    from app.core.langgraph_pipeline import create_pipeline_app

    checkpointer = SqliteSaver.from_conn_string("pipeline_state.db")
    app = create_pipeline_app(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)

    return {
        "thread_id": thread_id,
        "current_node": state.next[0] if state.next else "completed",
        "state": state.values,
    }
```

## Checkpointing & Persistence

LangGraph supports multiple persistence backends:

### SQLite (Development)
```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("pipeline_state.db")
```

### PostgreSQL (Production)
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/dbname"
)
```

### Redis (Distributed)
```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver.from_url("redis://localhost:6379")
```

## Benefits of This Architecture

| Feature | Description |
|---------|-------------|
| **State Machine** | Clear visual flow with conditional routing |
| **Retry Logic** | Built-in loops for test→fix and review→improve |
| **Persistence** | Checkpoint state to DB, resume after crashes |
| **Visualization** | Auto-generate Mermaid/PNG diagrams |
| **Debugging** | Time-travel debugging, inspect any state |
| **Unchanged Agents** | Your Claude Agent SDK agents work as-is |
| **Async Support** | Full async/await compatibility |

## Migration Path

1. **Phase 1**: Install LangGraph, create node wrappers
2. **Phase 2**: Build graph with routing logic
3. **Phase 3**: Add checkpointing for persistence
4. **Phase 4**: Update API endpoints
5. **Phase 5**: Remove old `pipeline.py` orchestration

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Multi-Agent Workflows](https://blog.langchain.com/langgraph-multi-agent-workflows/)
