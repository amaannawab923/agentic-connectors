# Orchestrator v2 Implementation

## Overview

Native LangGraph async pipeline orchestrator for connector generation. Removed Celery dependency in favor of direct async execution with `asyncio.create_task()`.

## Architecture

```
FastAPI → asyncio.create_task() → graph.astream() → MemorySaver
```

## Pipeline Flow

```
Research → Generator → Tester → TestReviewer ─┬─ VALID+PASS → Reviewer ─┬─ APPROVE → Publisher
                ↑         ↑                   │                         │
                │         │                   ├─ INVALID → Tester       ├─ REJECT:CODE → Generator
                │         │                   │                         │
                │         └───────────────────┴─ VALID+FAIL → Generator └─ REJECT:CONTEXT → Research
                │                                                                  │
                └──────────────────────────────────────────────────────────────────┘
```

## File Structure

```
app/orchestrator/
├── __init__.py          # Package exports
├── app.py               # FastAPI application with lifespan
├── config.py            # Settings (retry limits, timeouts)
├── pipeline.py          # LangGraph StateGraph definition
├── runner.py            # Native async execution (start, status, cancel)
├── state.py             # PipelineState TypedDict with reducers
├── api/
│   └── routes.py        # REST API endpoints
└── nodes/
    └── mock_agents.py   # Mock agent implementations for testing
```

## Key Components

### 1. State Management (`state.py`)

```python
class PipelineState(TypedDict):
    # Immutable
    connector_name: str
    connector_type: str
    original_request: str

    # Retry Counters
    test_retries: int           # TestReviewer -> Tester
    gen_fix_retries: int        # TestReviewer -> Generator
    review_retries: int         # Reviewer -> Generator
    research_retries: int       # Reviewer -> Research

    # Results
    coverage_ratio: float       # 0.0 - 1.0
    review_decision: str        # approve, reject_code, reject_context
    test_review_decision: str   # valid_pass, valid_fail, invalid

    # Lists with reducers
    logs: Annotated[List[str], reduce_logs]
    errors: Annotated[List[str], reduce_list_append]
```

### 2. Reducers

Custom reducers for list fields prevent state overwrites:

```python
def reduce_logs(existing: List[str], new: List[str]) -> List[str]:
    """Append and trim to MAX_LOGS_IN_STATE (100)."""
    combined = (existing or []) + (new or [])
    return combined[-MAX_LOGS_IN_STATE:]

def reduce_list_append(existing: List[str], new: List[str]) -> List[str]:
    """Always append new items."""
    return (existing or []) + (new or [])

def reduce_list_replace(existing: List[str], new: List[str]) -> List[str]:
    """Replace if new is non-empty."""
    return new if new else (existing or [])
```

### 3. Routing Logic (`pipeline.py`)

**TestReviewer Routing:**
- `INVALID` → Tester (fix tests) if `test_retries < max`
- `VALID_FAIL` → Generator (fix code) if `gen_fix_retries < max`
- `VALID_PASS` → Reviewer

**Reviewer Routing:**
- `APPROVE` → Publisher (100% or >=80% degraded)
- `REJECT_CODE` → Generator if `review_retries < max`
- `REJECT_CONTEXT` → Research if `research_retries <= max`

### 4. Native Async Runner (`runner.py`)

```python
async def start_pipeline(connector_name: str, connector_type: str = "source") -> str:
    """Start pipeline as background task."""
    thread_id = f"pipeline-{connector_name}-{uuid4().hex[:8]}"
    task = asyncio.create_task(execute_pipeline(thread_id, initial_state))
    _active_runs[thread_id] = {"task": task, "state": initial_state}
    return thread_id

async def execute_pipeline(thread_id: str, initial_state: dict):
    """Execute pipeline using graph.astream()."""
    app = create_pipeline_app()
    config = {"configurable": {"thread_id": thread_id}}

    async for event in app.astream(initial_state, config, stream_mode="values"):
        _active_runs[thread_id]["state"] = event  # Update state on each step
```

## Configuration (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `max_test_retries` | 3 | TestReviewer → Tester retries |
| `max_gen_fix_retries` | 3 | TestReviewer → Generator retries |
| `max_review_retries` | 2 | Reviewer → Generator retries |
| `max_research_retries` | 1 | Reviewer → Research retries |
| `max_concurrent_pipelines` | 10 | Max parallel pipelines |
| `pipeline_timeout` | 1200 | Timeout in seconds (20 min) |

Environment prefix: `ORCHESTRATOR_`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orchestrator/pipeline/start` | Start new pipeline |
| GET | `/orchestrator/pipeline/status/{thread_id}` | Get pipeline status |
| GET | `/orchestrator/pipeline/history/{thread_id}` | Get state history |
| POST | `/orchestrator/pipeline/resume/{thread_id}` | Resume failed pipeline |
| POST | `/orchestrator/pipeline/cancel/{thread_id}` | Cancel running pipeline |
| GET | `/orchestrator/runs/active` | List active pipelines |
| GET | `/orchestrator/health` | Health check |

## Running the Server

```bash
# Development (with test mode)
cd /path/to/connector-generator
source venv/bin/activate
ORCHESTRATOR_TEST_MODE=true python3 -m uvicorn app.orchestrator.app:app --host 0.0.0.0 --port 8002

# Production
python3 -m uvicorn app.orchestrator.app:app --host 0.0.0.0 --port 8002
```

## Testing

```bash
# Start a pipeline
curl -X POST http://localhost:8002/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"connector_name": "google-sheets"}'

# Check status
curl http://localhost:8002/orchestrator/pipeline/status/THREAD_ID

# List active runs
curl http://localhost:8002/orchestrator/runs/active
```

## LangGraph Best Practices Applied

1. **State Reducers** - Use `Annotated[List[str], reducer]` for list fields
2. **Thread Isolation** - Unique `thread_id` per pipeline run
3. **Native Async** - Direct `astream()` instead of sync wrappers
4. **Log Trimming** - Cap logs at 100 entries to prevent unbounded growth
5. **Checkpointing** - MemorySaver for state persistence during execution
6. **Conditional Routing** - `add_conditional_edges()` for decision points

## Mock Agents

In test mode (`ORCHESTRATOR_TEST_MODE=true`), mock agents simulate:
- Quick delays (1-2 seconds instead of real API calls)
- Deterministic routing through all paths
- 100% coverage for most connectors
- Simulated failures for testing retry logic
