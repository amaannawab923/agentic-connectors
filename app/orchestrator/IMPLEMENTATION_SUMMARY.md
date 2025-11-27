# LangGraph Orchestrator Implementation Summary

## Overview

The orchestrator is a **native async LangGraph-based state machine** for orchestrating AI connector generation pipelines. It replaces traditional task queue approaches (like Celery) with LangGraph's built-in state machine capabilities while leveraging Claude Agent SDK agents for actual work execution.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                              │
│                           (app.py, routes.py)                            │
├──────────────────────────────────────────────────────────────────────────┤
│                          Native Async Runner                              │
│                    (runner.py - asyncio.create_task)                     │
├──────────────────────────────────────────────────────────────────────────┤
│                         LangGraph StateGraph                              │
│                     (pipeline.py - build_pipeline)                       │
├──────────────────────────────────────────────────────────────────────────┤
│                       Checkpointing Layer                                 │
│              (MemorySaver / AsyncSqliteSaver / AsyncPostgresSaver)       │
├──────────────────────────────────────────────────────────────────────────┤
│                          Node Implementations                             │
│                     (nodes/mock_agents.py, real_agents.py)               │
└──────────────────────────────────────────────────────────────────────────┘
```

## Pipeline Flow (v2.1 - with MockGenerator)

```
                                         ┌─── MockGenerator ───┐ (first run only)
                                         │   (fixtures only,   │
                                         │    NO tests)        │
                                         │                     ↓
Research → Generator ─┬─────────────────────────────────────→ Tester → TestReviewer ─┬─ VALID+PASS → Reviewer ─┬─ APPROVE → Publisher
                ↑     │ (conditional routing)                   ↑                    │                         │
                │     └─────────────────────────────────────────┘ (retry loops)      ├─ INVALID → Tester       ├─ REJECT:CODE → Generator
                │                                                                     │                         │
                │                                                                     └─ VALID+FAIL → Generator └─ REJECT:CONTEXT → Research
                │                                                                                                          │
                └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Routing Logic After Generator

| Condition | Route | Reason |
|-----------|-------|--------|
| **First run** (gen_fix_retries = 0, no fixtures) | → MockGenerator | Generate fixtures and conftest.py |
| **Retry loop** (gen_fix_retries > 0) | → Tester | Skip fixture generation, rerun tests |
| **Fixtures exist** | → Tester | Skip fixture generation |

### MockGenerator Behavior

- **When it runs**: Only on first generation when fixtures don't exist
- **What it does**:
  - Reads IMPLEMENTATION.md from Generator
  - Analyzes test files for fixture requirements
  - Researches mock library attributes (universe_domain, etc.)
  - Creates fixtures/ directory and conftest.py
  - **Does NOT run tests** (that's Tester's job)
- **When it's skipped**:
  - On retry loops (gen_fix_retries > 0)
  - When fixtures already exist

### Exit States

| Status | Condition | Description |
|--------|-----------|-------------|
| `SUCCESS` | 100% coverage | Full pass, all streams working |
| `PARTIAL` | ≥80% coverage | Degraded mode with warnings |
| `FAILED` | Max retries exceeded | Pipeline could not complete |

---

## Core Components

### 1. State Definition (`state.py`)

The `PipelineState` TypedDict defines the shared state across all nodes:

#### State Fields

| Category | Fields | Description |
|----------|--------|-------------|
| **Request Info** | `connector_name`, `connector_type`, `original_request`, `api_doc_url`, `created_at` | Immutable request data |
| **Pipeline Control** | `current_phase`, `status` | Current execution state |
| **Retry Counters** | `test_retries`, `gen_fix_retries`, `review_retries`, `research_retries` | Track loop iterations |
| **Retry Limits** | `max_test_retries` (3), `max_gen_fix_retries` (3), `max_review_retries` (2), `max_research_retries` (1) | Configurable limits |
| **Artifacts** | `research_output`, `generated_code`, `test_code`, `connector_dir` | Generated content |
| **Mock Generation** | `mock_generation_output`, `fixtures_created`, `mock_generation_skipped` | Fixture and conftest.py metadata |
| **Results** | `test_results`, `coverage_ratio`, `test_review_decision`, `review_decision` | Decision outcomes |
| **Publish** | `published`, `pr_url`, `degraded_mode`, `degraded_streams` | Publication state |
| **Metadata** | `errors`, `logs`, `completed_at`, `total_duration` | Execution metadata |

#### Custom Reducers

LangGraph uses reducers to merge state updates. Custom reducers handle list fields:

```python
def reduce_logs(existing: List[str], new: List[str]) -> List[str]:
    """Appends logs and trims to max 100 entries."""
    combined = (existing or []) + (new or [])
    return combined[-MAX_LOGS_IN_STATE:]

def reduce_list_append(existing: List[str], new: List[str]) -> List[str]:
    """Accumulates lists (errors, context_gaps)."""
    return (existing or []) + (new or [])

def reduce_list_replace(existing: List[str], new: List[str]) -> List[str]:
    """Replaces lists (feedback fields)."""
    return new if new else (existing or [])
```

#### Enums

```python
class PipelinePhase(str, Enum):
    PENDING = "pending"
    RESEARCHING = "researching"
    GENERATING = "generating"
    MOCK_GENERATING = "mock_generating"
    TESTING = "testing"
    TEST_REVIEWING = "test_reviewing"
    REVIEWING = "reviewing"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"

class PipelineStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"      # 100% tests pass
    PARTIAL = "partial"      # ≥80% tests pass (DEGRADED MODE)
    FAILED = "failed"        # Max retries exceeded

class TestReviewDecision(str, Enum):
    VALID_PASS = "valid_pass"    # Tests valid, code passes → Reviewer
    VALID_FAIL = "valid_fail"    # Tests valid, code fails → Generator
    INVALID = "invalid"          # Tests invalid → Tester

class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT_CODE = "reject_code"        # Code bugs → Generator
    REJECT_CONTEXT = "reject_context"  # Missing API context → Research
```

---

### 2. Pipeline Definition (`pipeline.py`)

Uses LangGraph's `StateGraph` to define the workflow:

```python
def build_pipeline() -> StateGraph:
    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("test_reviewer", test_reviewer_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("failed", failed_node)

    # Set entry point
    workflow.set_entry_point("research")

    # Sequential edges (happy path)
    workflow.add_edge("research", "generator")
    workflow.add_edge("generator", "tester")
    workflow.add_edge("tester", "test_reviewer")

    # Conditional routing after TestReviewer
    workflow.add_conditional_edges(
        "test_reviewer",
        route_after_test_review,
        {
            "tester": "tester",
            "generator": "generator",
            "reviewer": "reviewer",
            "failed": "failed",
        }
    )

    # Conditional routing after Reviewer
    workflow.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "generator": "generator",
            "research": "research",
            "publisher": "publisher",
            "failed": "failed",
        }
    )

    # Terminal edges
    workflow.add_edge("publisher", END)
    workflow.add_edge("failed", END)

    return workflow
```

---

### 3. Routing Logic (`pipeline.py`)

#### `route_after_test_review`

Routes based on test validity and code pass/fail:

| Decision | Route | Condition |
|----------|-------|-----------|
| `INVALID` | → tester | Tests are insufficient (< 5 tests), need fixes |
| `VALID_FAIL` | → generator | Tests pass validation but code fails |
| `VALID_PASS` | → reviewer | Tests and code both pass |
| Max retries exceeded | → failed | `test_retries >= 3` or `gen_fix_retries >= 3` |

#### `route_after_review`

Routes based on coverage ratio:

| Coverage | Decision | Route | Description |
|----------|----------|-------|-------------|
| 100% | `APPROVE` | → publisher | Full success |
| ≥80% | `APPROVE` (degraded) | → publisher | Partial success with warnings |
| 50-79% | `REJECT_CODE` | → generator | Code quality issues |
| <50% | `REJECT_CONTEXT` | → research | Fundamental API understanding issues |

---

### 4. Checkpointing (`pipeline.py`)

Singleton pattern with three backends for state persistence:

| Type | Class | Persistence | Use Case |
|------|-------|-------------|----------|
| `memory` | `MemorySaver` | No | Testing only |
| `sqlite` | `AsyncSqliteSaver` | Yes | Single-node deployment (default) |
| `postgres` | `AsyncPostgresSaver` | Yes | Multi-node / production |

```python
async def get_checkpointer_async():
    if checkpointer_type == "memory":
        return MemorySaver()
    elif checkpointer_type == "sqlite":
        saver = AsyncSqliteSaver.from_conn_string(db_path)
        await saver.setup()
        return saver
    elif checkpointer_type == "postgres":
        saver = AsyncPostgresSaver.from_conn_string(postgres_url)
        await saver.setup()
        return saver
```

---

### 5. Runner (`runner.py`)

Provides the async execution interface:

#### Core Functions

| Function | Purpose |
|----------|---------|
| `start_pipeline()` | Creates background task via `asyncio.create_task()` |
| `execute_pipeline()` | Core execution with streaming progress |
| `resume_pipeline()` | Continues from last checkpoint |
| `get_pipeline_status()` | Reads checkpointed state |
| `get_pipeline_history()` | Gets all checkpoints for time-travel |
| `stream_pipeline_events()` | AsyncGenerator for real-time SSE updates |
| `cancel_pipeline()` | Cancels running task |
| `cleanup_completed_runs()` | Removes old completed runs |

#### Active Run Tracking

```python
@dataclass
class PipelineRun:
    thread_id: str
    connector_name: str
    status: str = "starting"
    current_phase: str = "pending"
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None

# Active runs dictionary
_active_runs: Dict[str, PipelineRun] = {}
```

#### Streaming Execution

```python
async def execute_pipeline(thread_id, connector_name, ...):
    app = await create_pipeline_app()
    initial_state = create_initial_state(connector_name=connector_name, ...)
    config = {"configurable": {"thread_id": thread_id}}

    async for event in app.astream(initial_state, config, stream_mode="values"):
        # Update tracking
        run.current_phase = event.get("current_phase")
        run.status = event.get("status")
        # Log progress...

    return dict(final_state)
```

---

### 6. Node Implementations (`nodes/`)

#### Mock Agents (`mock_agents.py`)

For testing and development:

- Simulate real agents with configurable delays
- Deterministic `TEST_MODE` for integration testing
- Demonstrate all routing paths

```python
TEST_MODE = os.getenv("ORCHESTRATOR_TEST_MODE", "").lower() in ("true", "1", "yes")
TEST_DELAY = 1  # 1 second delay in test mode
```

#### Real Agents (`real_agents.py`)

Production implementations wrapping Claude Agent SDK:

```python
# Singleton agent instance
_research_agent = None

def _get_research_agent() -> ResearchAgent:
    global _research_agent
    if _research_agent is None:
        _research_agent = ResearchAgent()
    return _research_agent

async def research_node(state: PipelineState) -> Dict[str, Any]:
    agent = _get_research_agent()
    result = await agent.execute(
        connector_name=state["connector_name"],
        additional_context=additional_context,
    )
    # Transform result to state updates...
```

---

### 7. API Layer (`api/routes.py`)

FastAPI REST endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/orchestrator/pipeline/start` | POST | Start new pipeline |
| `/orchestrator/pipeline/status/{thread_id}` | GET | Get current status |
| `/orchestrator/pipeline/history/{thread_id}` | GET | Get checkpoint history |
| `/orchestrator/pipeline/resume` | POST | Resume from checkpoint |
| `/orchestrator/pipeline/cancel/{thread_id}` | DELETE | Cancel running pipeline |
| `/orchestrator/pipeline/stream/{connector_name}` | GET | SSE event stream |
| `/orchestrator/pipeline/diagram` | GET | Mermaid diagram |
| `/orchestrator/pipelines/active` | GET | List active runs |
| `/orchestrator/health` | GET | Health check |

#### Request/Response Models

```python
class PipelineRequest(BaseModel):
    connector_name: str
    connector_type: str = "source"
    api_doc_url: Optional[str] = None
    original_request: Optional[str] = None

class PipelineResponse(BaseModel):
    thread_id: str
    status: str
    message: str
    poll_url: str
    stream_url: Optional[str] = None
```

---

## Configuration (`config.py`)

```python
class OrchestratorSettings(BaseSettings):
    # Checkpointing
    checkpointer_type: Literal["memory", "sqlite", "postgres"] = "sqlite"
    sqlite_db_path: str = "orchestrator_checkpoints.db"
    postgres_url: Optional[str] = None

    # Retry limits
    max_test_retries: int = 3      # TestReviewer → Tester
    max_gen_fix_retries: int = 3   # TestReviewer → Generator
    max_review_retries: int = 2    # Reviewer → Generator
    max_research_retries: int = 1  # Reviewer → Research

    # Mock task durations (for testing)
    mock_research_duration: int = 10
    mock_generator_duration: int = 15
    mock_tester_duration: int = 8
    mock_reviewer_duration: int = 6
    mock_publisher_duration: int = 5

    # Execution
    max_concurrent_pipelines: int = 10
    pipeline_timeout: int = 1200  # 20 minutes

    class Config:
        env_prefix = "ORCHESTRATOR_"
        env_file = ".env"
```

### Environment Variables

```bash
# Checkpointing
ORCHESTRATOR_CHECKPOINTER_TYPE=sqlite  # memory, sqlite, postgres
ORCHESTRATOR_SQLITE_DB_PATH=orchestrator_checkpoints.db
ORCHESTRATOR_POSTGRES_URL=postgresql://user:pass@host:port/db

# Retry limits
ORCHESTRATOR_MAX_TEST_RETRIES=3
ORCHESTRATOR_MAX_GEN_FIX_RETRIES=3
ORCHESTRATOR_MAX_REVIEW_RETRIES=2
ORCHESTRATOR_MAX_RESEARCH_RETRIES=1

# Testing
ORCHESTRATOR_TEST_MODE=true  # Enable deterministic test behavior
```

---

## Key Design Decisions

### 1. LangGraph over Celery

| Aspect | LangGraph | Celery |
|--------|-----------|--------|
| State management | Built-in TypedDict state | Manual (Redis/DB) |
| Conditional routing | `add_conditional_edges()` | Manual if/else |
| Checkpointing | Native persistence | Must implement |
| Visualization | `get_graph().draw_mermaid()` | None |
| Complexity | State machine semantics | Distributed task queue |

### 2. Native Async Execution

Uses `asyncio.create_task()` instead of Celery workers:
- Simpler deployment (no broker required)
- Better for single-node or small-scale deployments
- LangGraph handles persistence via checkpointing

### 3. Coverage-Based Quality Gates

Automatic routing based on test coverage ratio:
- 100%: Full approval
- ≥80%: Degraded mode (partial approval with warnings)
- 50-79%: Code quality issues → fix code
- <50%: Fundamental issues → re-research

### 4. Degraded Mode

Allows partial success when perfect coverage isn't achievable:
- Pipeline can complete with ≥80% coverage
- Disabled streams are tracked in `degraded_streams`
- Status is `PARTIAL` instead of `SUCCESS`
- Useful for complex APIs where some endpoints are problematic

### 5. Context Gap Tracking

When `REJECT:CONTEXT` triggers re-research:
- `context_gaps` accumulates across cycles
- Research agent receives previous gaps as context
- Prevents repeating the same mistakes

### 6. Reducer-Based State Merging

Proper handling of list fields:
- Logs are appended and trimmed
- Errors accumulate
- Feedback fields are replaced each cycle

---

## Test Mode

Setting `ORCHESTRATOR_TEST_MODE=true` enables deterministic behavior that demonstrates all routing paths:

```
Phase 1: Initial Research → First Review
──────────────────────────────────────────
1. Research → Generator → Tester (0 tests) → TestReviewer (INVALID) → Tester
2. Tester → TestReviewer (VALID+FAIL) → Generator
3. Generator → Tester → TestReviewer (VALID+FAIL) → Generator
4. Generator → Tester → TestReviewer (VALID+PASS) → Reviewer
5. Reviewer (REJECT:CONTEXT) → Research  ← Tests re-research path

Phase 2: Re-Research → Final Approval
──────────────────────────────────────────
6. Research (with context_gaps) → Generator → Tester → TestReviewer
7. TestReviewer (VALID+PASS) → Reviewer
8. Reviewer (REJECT:CODE) → Generator  ← Tests code fix path
9. Generator → Tester → TestReviewer → Reviewer (APPROVE) → Publisher

All Counters Tested:
- test_retries: increments when INVALID (max 3)
- gen_fix_retries: increments when VALID+FAIL (max 3)
- review_retries: increments when REJECT:CODE (max 2)
- research_retries: increments when REJECT:CONTEXT (max 1)
```

---

## File Structure

```
app/orchestrator/
├── __init__.py           # Public exports
├── app.py                # FastAPI application with lifespan
├── config.py             # Pydantic settings
├── pipeline.py           # LangGraph StateGraph definition
├── runner.py             # Async execution and tracking
├── state.py              # PipelineState TypedDict & reducers
├── api/
│   ├── __init__.py
│   └── routes.py         # REST API endpoints
├── nodes/
│   ├── __init__.py
│   ├── mock_agents.py    # Test/mock implementations
│   └── real_agents.py    # Claude Agent SDK wrappers
└── tasks/                # (Legacy Celery tasks, unused)
```

---

## Usage Examples

### Starting a Pipeline

```bash
curl -X POST http://localhost:8002/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"connector_name": "google-sheets", "connector_type": "source"}'
```

Response:
```json
{
  "thread_id": "pipeline-google-sheets-a1b2c3d4",
  "status": "started",
  "message": "Pipeline started for google-sheets",
  "poll_url": "/orchestrator/pipeline/status/pipeline-google-sheets-a1b2c3d4",
  "stream_url": "/orchestrator/pipeline/stream/google-sheets"
}
```

### Checking Status

```bash
curl http://localhost:8002/orchestrator/pipeline/status/pipeline-google-sheets-a1b2c3d4
```

### Streaming Events (SSE)

```bash
curl http://localhost:8002/orchestrator/pipeline/stream/google-sheets
```

### Resuming After Failure

```bash
curl -X POST http://localhost:8002/orchestrator/pipeline/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "pipeline-google-sheets-a1b2c3d4"}'
```

---

## Running the Orchestrator

```bash
# Development
cd app/orchestrator
python -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload

# Or via the app module
python -m app.orchestrator.app
```

---

*Last Updated: November 26, 2025*
