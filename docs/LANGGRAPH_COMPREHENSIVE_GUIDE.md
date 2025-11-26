# LangGraph Comprehensive Guide

> **A Complete Reference for Building Production-Grade AI Agents**
>
> Last Updated: November 2025

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [State Management](#3-state-management)
4. [Agent Patterns](#4-agent-patterns)
5. [Advanced Features](#5-advanced-features)
6. [Best Practices](#6-best-practices)
7. [Production Deployment](#7-production-deployment)
8. [Troubleshooting](#8-troubleshooting)
9. [Quick Reference](#9-quick-reference)

---

## 1. Introduction

### What is LangGraph?

**LangGraph** is a low-level orchestration framework for building, managing, and deploying long-running, stateful AI agents. Built on top of LangChain, it enables the creation of **cyclical graphs** for agent runtimes—solving the critical limitation of LangChain's linear (DAG-only) architecture.

### Core Value Proposition

| Capability | Description |
|------------|-------------|
| **Durable Execution** | Agents persist through failures and resume from interruption points |
| **Human-in-the-Loop** | Seamless integration of human oversight at any workflow point |
| **Comprehensive Memory** | Both short-term (session) and long-term (cross-session) memory |
| **Cyclic Workflows** | Loops, retries, and refinement patterns impossible in DAGs |

### LangGraph vs LangChain

| Aspect | LangChain | LangGraph |
|--------|-----------|-----------|
| **Graph Type** | Directed Acyclic Graphs (DAGs) | Cyclic Graphs with loops |
| **Execution Model** | Sequential pipeline | State machine with branching |
| **Flow Pattern** | Linear, step-by-step | Nonlinear, conditional paths |
| **Best For** | Simple chains, RAG, Q&A | Complex agents, multi-step workflows |

**Key Insight**: LangGraph is built **on top of** LangChain, not a replacement. Use LangChain for components (models, tools, retrievers) and LangGraph for orchestration.

### When to Use LangGraph

**Choose LangGraph for:**
- Complex, stateful, multi-agent systems
- Applications requiring loops and conditional branching
- Long-running workflows with human oversight
- Production deployments requiring fault tolerance

**Don't use LangGraph for:**
- Simple linear chains
- Basic RAG pipelines
- Quick prototypes without state requirements

---

## 2. Core Concepts

### 2.1 StateGraph

The **StateGraph** is the core class representing your workflow structure. It maintains a central state object that gets updated as the graph executes.

**Key Properties:**
- Initialized with a state schema (TypedDict or Pydantic model)
- Each node receives current state as input
- Nodes return updates that modify state attributes
- State is stored as key-value structure

### 2.2 Nodes

**Nodes** are the fundamental building blocks—discrete units of work or computation.

**Characteristics:**
- Typically Python functions or LCEL runnables
- Accept current state as input (dictionary matching State schema)
- Perform tasks: call LLMs, query databases, execute business logic
- Return dictionary with state attributes to update

**Special Nodes:**
- `START` - Virtual node marking graph entry point
- `END` - Virtual node representing graph termination

### 2.3 Edges

**Edges** are directed connections between nodes defining execution flow.

**Types:**

| Edge Type | Description | Method |
|-----------|-------------|--------|
| **Standard** | Deterministic, guaranteed transitions | `add_edge(source, dest)` |
| **Conditional** | Decision-based routing | `add_conditional_edges(source, router_fn, path_map)` |
| **Entry Point** | Special edges from START | `set_entry_point(node)` |

### 2.4 Execution Model

LangGraph's execution is inspired by **Google's Pregel** system:

1. **Super-Steps**: Discrete rounds of graph processing
2. **Message Passing**: Nodes activate when receiving state on incoming edges
3. **Parallel Execution**: Nodes in same super-step can run concurrently

**Execution Flow:**
```
Initial State → Node Activation → State Update → Edge Routing → Next Node(s) → ... → END
```

### 2.5 Compilation

Before execution, the graph is **compiled**:
- Validates structure for consistency
- Checks for orphaned nodes
- Returns a LangChain Runnable supporting `.invoke()`, `.stream()`, `.batch()`

---

## 3. State Management

### 3.1 State Schema Design

**TypedDict Approach** (Recommended for internal state):
```python
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[Message], add_messages]
    current_step: str
    iteration_count: int
```

**Pydantic Approach** (For validation at boundaries):
```python
from pydantic import BaseModel, Field

class InputSchema(BaseModel):
    query: str = Field(..., min_length=1)
    max_steps: int = Field(default=10, ge=1, le=50)
```

**Best Practice**: Use TypedDict internally, Pydantic at system boundaries.

### 3.2 Reducers

**Reducers** define how state updates from multiple sources merge into a single value.

| Reducer | Function | Use Case |
|---------|----------|----------|
| `operator.add` | Concatenates lists | Accumulating results |
| `add_messages` | Smart message handling | Conversation history |
| Custom function | User-defined logic | Complex merge requirements |

**Without reducer**: Value is overwritten
**With reducer**: Values are merged according to reducer logic

```python
from operator import add
from typing import Annotated

class State(TypedDict):
    # Will accumulate across parallel nodes
    results: Annotated[List[str], add]
    # Will be overwritten (no reducer)
    status: str
```

### 3.3 Checkpointing

**Checkpointing** saves complete state snapshots at each execution step.

**Available Checkpointers:**

| Checkpointer | Storage | Production Ready | Use Case |
|--------------|---------|------------------|----------|
| `MemorySaver` | In-memory | No | Testing/Development |
| `SqliteSaver` | SQLite file | Limited | Local development |
| `PostgresSaver` | PostgreSQL | Yes | Production |

**Usage:**
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(connection=db_connection)
await checkpointer.setup()

graph = builder.compile(checkpointer=checkpointer)

# Invoke with thread_id for state persistence
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke(input_data, config=config)
```

### 3.4 Thread-Based Isolation

**Threads** are unique execution contexts identified by `thread_id`:
- Each thread has its own checkpoint history
- State changes in one thread don't affect others
- Enables multi-user/multi-conversation scenarios

**Thread ID Patterns:**
```python
# Simple user conversation
thread_id = "user-123"

# Structured pattern
thread_id = f"tenant-{tenant_id}:user-{user_id}:session-{session_id}"
```

---

## 4. Agent Patterns

### 4.1 ReAct Agents (Reasoning + Acting)

The foundational pattern where LLMs alternate between reasoning and tool execution.

**Flow:**
```
User Input → LLM Reasoning → Tool Call Decision
                                    ↓
                            Tool Execution
                                    ↓
                            Observation → Loop back to LLM
                                    ↓
                            Final Answer → END
```

**Use Cases:**
- Question-answering with external data
- Task automation with tools
- Research and information gathering

**Pros/Cons:**
| Pros | Cons |
|------|------|
| Transparent reasoning | Multiple LLM calls = higher latency |
| Flexible tool integration | Token consumption accumulates |
| Production-proven | Requires careful prompting |

### 4.2 Reflection Agents

Agents that critique and refine their own outputs iteratively.

**Core Pattern:**
```
Generate → Critique → Improve → Loop until quality threshold
```

**Variants:**

1. **Basic Reflection**: Self-critique without external grounding
2. **Reflexion**: Critique grounded in external data/citations
3. **Tool-Based Validation**: External tools validate output (e.g., Pyright for code)

**Use Cases:**
- Code generation and validation
- High-stakes decision support
- Document quality assurance

**Trade-off**: "Reflection trades compute for quality"

### 4.3 Multi-Agent Patterns

Multiple specialized agents collaborating on complex problems.

**Pattern Variations:**

| Pattern | Description | Best For |
|---------|-------------|----------|
| **Shared Scratchpad** | All agents see all work | Debugging, transparency |
| **Independent Scratchpads** | Each agent has own history | Modular services |
| **Supervisor** | Central coordinator routes tasks | Clear routing requirements |
| **Hierarchical Teams** | Nested agent structure | Complex, multi-level problems |
| **Swarm** | Decentralized, emergent | Creative problem-solving |

### 4.4 Supervisor Pattern

Central coordinator manages multiple specialist workers.

**Architecture:**
```
User Input → Supervisor → Route to Worker A/B/C → Execute → Return to Supervisor → Aggregate → Output
```

**Benefits:**
- Modularity: Work on agents independently
- Control: All tool calls through supervisor
- Auditability: Central logging point
- Flexibility: Add/remove agents easily

### 4.5 Human-in-the-Loop

Pause execution for human review, approval, or input.

**Interrupt Mechanics:**
```python
from langgraph import interrupt

def approval_node(state):
    # Pause for human approval
    human_decision = interrupt("Approve this action?")
    if human_decision == "approved":
        return {"status": "proceeding"}
    return {"status": "rejected"}
```

**Design Patterns:**

1. **Approve/Reject**: Review before critical actions
2. **Edit State**: Correct errors before proceeding
3. **Review Tool Calls**: Validate before execution
4. **Multi-turn Conversation**: Request clarifying information

---

## 5. Advanced Features

### 5.1 Subgraphs and Nested Graphs

**Subgraphs** are compiled graphs functioning as nodes within parent graphs.

**Use Cases:**
- Multi-agent team organization
- Reusable workflow components
- Independent development by teams

**Implementation:**
```python
# Define subgraph
research_subgraph = build_research_graph().compile()

# Add as node in parent
parent_builder.add_node("research", research_subgraph)
```

**Limitation**: Cannot invoke multiple subgraphs in same node with checkpointing enabled.

### 5.2 Parallel Node Execution

Execute independent nodes concurrently for performance.

**Methods:**
1. **Multiple edges from same source**: Nodes without dependencies run in parallel
2. **Send API**: Dynamic branching with runtime-determined count
3. **Map-Reduce**: Break problem into parallel sub-components

**Concurrency Control:**
```python
config = {"max_concurrency": 50}
result = graph.invoke(inputs, config=config)
```

**Performance**: 50%+ latency reduction achievable.

### 5.3 Dynamic Graph Modification

Configure graph structure at runtime.

**Approaches:**
1. **Runtime Configuration**: Pass `config` to nodes for dynamic behavior
2. **Graph Rebuild Pattern**: Dynamically return new compiled graph
3. **Wrapper Graph**: Single node dynamically calls graph factory

### 5.4 Time Travel and State Replay

Replay execution from any checkpoint for debugging or alternative exploration.

**Capabilities:**
- Retrieve checkpoint history: `graph.get_state_history(config)`
- Resume from specific checkpoint: Provide `checkpoint_id` in config
- Modify state and fork: `update_state()` then resume

**Use Cases:**
- Debugging execution paths
- "What-if" analysis
- Error recovery without data loss

### 5.5 Streaming

Progressive result delivery for better UX.

**Streaming Modes:**

| Mode | Returns | Use Case |
|------|---------|----------|
| `values` | Complete state after each node | Full context needed |
| `updates` | Only state changes (deltas) | Bandwidth-sensitive |
| `messages` | LLM tokens + metadata | Chat interfaces |
| `custom` | Application-specific events | Complex workflows |

```python
async for event in graph.astream(input, config, stream_mode="messages"):
    print(event)  # Token-by-token output
```

### 5.6 Memory Management

**Short-Term Memory** (Session-Scoped):
- Thread-scoped checkpointers
- Conversation history, intermediate results
- Bounded by thread lifetime

**Long-Term Memory** (Cross-Session):
- LangGraph `store` class
- Persists across different threads
- Custom namespaces for organization
- Content-based filtering

```python
# Long-term memory store
from langgraph.store import InMemoryStore

store = InMemoryStore()
graph = builder.compile(store=store)
```

---

## 6. Best Practices

### 6.1 State Design

| Do | Don't |
|----|-------|
| Keep state minimal and typed | Dump everything into state |
| Use TypedDict with clear field names | Use plain dicts |
| Store only persistent/expensive data | Store formatted strings |
| Document state structure | Mix TypedDict and Pydantic |

### 6.2 Node Design

| Do | Don't |
|----|-------|
| Small, focused, single-responsibility | Monolithic nodes combining operations |
| Return partial state updates | Mutate state directly |
| Make operations idempotent | Create side effects in state |

### 6.3 Edge Design

| Do | Don't |
|----|-------|
| Simple sequential edges by default | Over-engineer control flow |
| Conditional edges only at decision points | Add unnecessary routing |
| Bound cycles with hard stops | Allow infinite retry loops |

### 6.4 Error Handling

**Multi-Level Strategy:**

1. **Node-Level**: Try-catch around external calls
2. **Graph-Level**: Conditional edges for fallback paths
3. **App-Level**: Request validation, rate limiting

**Retry Policy:**
```python
from langgraph.pregel import RetryPolicy

retry_policy = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_multiplier=2.0
)
```

### 6.5 Testing Strategy

| Level | Purpose | Tools |
|-------|---------|-------|
| **Snapshot** | Validate graph structure | `syrupy` |
| **Unit** | Test individual nodes | `pytest`, mocks |
| **Partial Execution** | Test paused/resumed workflows | `InMemorySaver` |
| **Integration** | End-to-end workflows | Full graph execution |

### 6.6 Performance Optimization

**Diagnosis First**: Use LangSmith waterfall view to identify bottlenecks.

**Optimization Strategies:**

1. **Reduce LLM Calls** (Highest impact)
2. **Parallelize Independent Work** (50%+ improvement possible)
3. **Use Faster Models** for non-critical steps
4. **Implement Caching** for expensive operations
5. **Stream Intermediate Results** for better perceived latency

---

## 7. Production Deployment

### 7.1 Deployment Options

| Option | Description | Best For |
|--------|-------------|----------|
| **Cloud SaaS** | Fully managed by LangChain | Teams without DevOps |
| **Hybrid** | SaaS control + self-hosted data | Enterprise compliance |
| **Self-Hosted** | Full infrastructure control | Regulated environments |

### 7.2 LangGraph Platform Features

- Horizontally-scaling task queues
- PostgreSQL checkpointer for concurrent users
- One-click rollback to previous versions
- Built-in LangGraph Studio for debugging
- GitHub integration for deployment

### 7.3 Observability with LangSmith

**Enable Tracing:**
```bash
export LANGSMITH_API_KEY=...
export LANGSMITH_PROJECT=my-project
```

**Key Capabilities:**
- Waterfall view for latency analysis
- Run tree showing execution path
- Cost tracking per LLM API
- Performance monitoring dashboard

### 7.4 Production Checklist

- [ ] PostgreSQL checkpointer (not MemorySaver)
- [ ] Meaningful, stable thread_id structure
- [ ] State cleanup/retention policy
- [ ] Multi-level error handling
- [ ] Retry policies on external calls
- [ ] LangSmith tracing enabled
- [ ] Cost monitoring alerts
- [ ] Human-in-loop at critical operations

---

## 8. Troubleshooting

### Common Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| **Supervisor Always Routes to One Agent** | Can't handle multi-faceted queries | Hierarchical routing or parallel processing |
| **Oversized Nodes** | Poor checkpointing, hard to debug | Smaller, focused nodes |
| **State Bloat** | Slow checkpointing | Store only essential data |
| **Unbounded Cycles** | Infinite loops | max_steps counter, explicit exits |
| **Missing Error Context** | Hard to debug failures | Multi-level error handling with logging |

### Debugging Techniques

1. **Enable Verbose Logging**: Set log level to DEBUG
2. **Use LangGraph Studio**: Visual inspection of execution
3. **Time Travel**: Replay from checkpoints
4. **Snapshot Testing**: Catch structural changes
5. **LangSmith Traces**: Full execution visibility

---

## 9. Quick Reference

### Graph Building Cheatsheet

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

# 1. Define State
class State(TypedDict):
    messages: Annotated[list, add_messages]
    current_step: str

# 2. Define Nodes
def my_node(state: State) -> dict:
    return {"current_step": "processed"}

def router(state: State) -> str:
    if state["current_step"] == "done":
        return "end"
    return "continue"

# 3. Build Graph
builder = StateGraph(State)
builder.add_node("process", my_node)
builder.add_node("finalize", finalize_node)

# 4. Add Edges
builder.set_entry_point("process")
builder.add_conditional_edges("process", router, {
    "continue": "process",
    "end": "finalize"
})
builder.add_edge("finalize", END)

# 5. Compile
graph = builder.compile(checkpointer=checkpointer)

# 6. Execute
result = graph.invoke(
    {"messages": [], "current_step": "start"},
    config={"configurable": {"thread_id": "123"}}
)
```

### Key Imports

```python
# Core
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Checkpointers
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

# Human-in-loop
from langgraph import interrupt
from langgraph.types import Command

# Prebuilt
from langgraph.prebuilt import create_react_agent
```

### Execution Methods

```python
# Synchronous
result = graph.invoke(input, config)

# Asynchronous
result = await graph.ainvoke(input, config)

# Streaming
for event in graph.stream(input, config):
    print(event)

# Async streaming
async for event in graph.astream(input, config):
    print(event)

# Batch
results = graph.batch([input1, input2], config)
```

---

## References

### Official Documentation
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Platform](https://www.langchain.com/langgraph-platform)
- [LangSmith Observability](https://www.langchain.com/langsmith)

### Key Blog Posts
- [Building LangGraph: Designing an Agent Runtime](https://blog.langchain.com/building-langgraph/)
- [Reflection Agents](https://blog.langchain.com/reflection-agents/)
- [Multi-Agent Workflows](https://blog.langchain.com/langgraph-multi-agent-workflows/)
- [Top 5 LangGraph Agents in Production 2024](https://blog.langchain.com/top-5-langgraph-agents-in-production-2024/)

### Tutorials
- [LangGraph Tutorial - DataCamp](https://www.datacamp.com/tutorial/langgraph-tutorial)
- [ReAct Agent from Scratch](https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/)
- [Human-in-the-Loop with Interrupt](https://blog.langchain.com/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt/)

---

## Production Users

Companies using LangGraph in production:
- **LinkedIn**: AI Recruiter with hierarchical agents
- **Uber**: Large-scale code migration
- **Replit**: Multi-agent coordination
- **Elastic**: Threat detection automation
- **Klarna**: Customer service automation

---

*This guide is maintained as part of the Connector Generator project. For updates and contributions, see the project repository.*
