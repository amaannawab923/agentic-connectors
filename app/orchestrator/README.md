# LangGraph + Celery Orchestrator

A production-ready pipeline orchestrator using LangGraph for state machine logic and Celery for background task execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Server (:8002)                            │
│  POST /orchestrator/pipeline/start → Returns task_id immediately            │
│  GET  /orchestrator/pipeline/status/{task_id} → Poll for progress           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Redis (:6379)                                     │
│  • Celery message broker                                                    │
│  • Task result backend                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Celery Worker                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    LangGraph Pipeline                                  │ │
│  │                                                                        │ │
│  │  Research → Generate → Test ─┬─ (pass) → Review ─┬─ (ok) → Publish    │ │
│  │                              │                   │                     │ │
│  │                              │                   └─ (no) → Improve     │ │
│  │                              │                              ↓          │ │
│  │                              └─ (fail) → Fix ──────────────→ Test     │ │
│  │                                                                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│  • Checkpoints saved to SQLite                                              │
│  • task_time_limit: 1200s (20 min)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Redis (macOS)

```bash
# Install Redis
brew install redis

# Start Redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### 2. Install Dependencies

```bash
cd /Users/amaannawab/research/connector-platform/connector-generator

# Create/activate virtual environment (if not already)
python3 -m venv venv
source venv/bin/activate

# Install orchestrator dependencies
pip install -r app/orchestrator/requirements.txt
```

### 3. Start Celery Worker

Open a new terminal:

```bash
cd /Users/amaannawab/research/connector-platform/connector-generator
source venv/bin/activate

# Start Celery worker
celery -A app.orchestrator.celery_app worker \
    --loglevel=INFO \
    --concurrency=2 \
    --queues=pipeline
```

You should see:
```
 -------------- celery@your-machine v5.x.x
--- ***** -----
-- ******* ---- [config]
- *** --- * --- .> app:         orchestrator
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 2 (prefork)
-- ******* ----
--- ***** -----
 -------------- [queues]
                .> pipeline       exchange=pipeline(direct) key=pipeline

[tasks]
  . orchestrator.get_pipeline_state
  . orchestrator.resume_pipeline
  . orchestrator.run_pipeline
```

### 4. Start FastAPI Server

Open another terminal:

```bash
cd /Users/amaannawab/research/connector-platform/connector-generator
source venv/bin/activate

# Start FastAPI server
python -m uvicorn app.orchestrator.app:app --host 0.0.0.0 --port 8002 --reload
```

### 5. Test the Pipeline

#### Start a Pipeline

```bash
curl -X POST http://localhost:8002/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"connector_name": "test-connector", "connector_type": "source"}'
```

Response:
```json
{
  "task_id": "abc123...",
  "thread_id": "pipeline-test-connector-abc123",
  "status": "started",
  "message": "Pipeline started for test-connector",
  "poll_url": "/orchestrator/pipeline/status/abc123..."
}
```

#### Poll for Status

```bash
curl http://localhost:8002/orchestrator/pipeline/status/{task_id}
```

Response (while running):
```json
{
  "task_id": "abc123...",
  "status": "PROGRESS",
  "phase": "testing",
  "connector_name": "test-connector",
  "thread_id": "pipeline-test-connector-abc123",
  "test_attempts": 1,
  "review_cycles": 0,
  "logs": [
    "[10:30:15] [RESEARCH] Starting research...",
    "[10:30:25] [GENERATOR] Generating code...",
    "[10:30:40] [TESTER] Running tests (attempt 1)..."
  ]
}
```

Response (completed):
```json
{
  "task_id": "abc123...",
  "status": "SUCCESS",
  "phase": "completed",
  "result": {
    "connector_name": "test-connector",
    "published": true,
    "pr_url": "https://github.com/org/connectors/pull/123",
    "test_attempts": 2,
    "review_cycles": 1
  }
}
```

#### Other Endpoints

```bash
# Get pipeline diagram
curl http://localhost:8002/orchestrator/pipeline/diagram

# Check health
curl http://localhost:8002/orchestrator/health

# List workers
curl http://localhost:8002/orchestrator/workers

# Cancel a task
curl -X DELETE http://localhost:8002/orchestrator/pipeline/cancel/{task_id}

# Resume interrupted pipeline
curl -X POST http://localhost:8002/orchestrator/pipeline/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "pipeline-test-connector-abc123"}'
```

## Configuration

Environment variables (or `.env` file):

```bash
# Redis
ORCHESTRATOR_REDIS_URL=redis://localhost:6379/0
ORCHESTRATOR_CELERY_BROKER_URL=redis://localhost:6379/0
ORCHESTRATOR_CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Task Limits
ORCHESTRATOR_TASK_TIME_LIMIT=1200      # 20 minutes
ORCHESTRATOR_TASK_SOFT_TIME_LIMIT=1100 # 18 minutes

# Pipeline Config
ORCHESTRATOR_MAX_TEST_RETRIES=3
ORCHESTRATOR_MAX_REVIEW_CYCLES=2

# Mock Task Durations (seconds) - for testing
ORCHESTRATOR_MOCK_RESEARCH_DURATION=10
ORCHESTRATOR_MOCK_GENERATOR_DURATION=15
ORCHESTRATOR_MOCK_TESTER_DURATION=8
ORCHESTRATOR_MOCK_FIXER_DURATION=12
ORCHESTRATOR_MOCK_REVIEWER_DURATION=6
ORCHESTRATOR_MOCK_IMPROVER_DURATION=10
ORCHESTRATOR_MOCK_PUBLISHER_DURATION=5
```

## File Structure

```
app/orchestrator/
├── __init__.py
├── README.md              # This file
├── requirements.txt       # Dependencies
├── config.py              # Settings
├── state.py               # Pipeline state definition
├── pipeline.py            # LangGraph pipeline builder
├── celery_app.py          # Celery configuration
├── app.py                 # FastAPI application
├── api/
│   ├── __init__.py
│   └── routes.py          # REST endpoints
├── nodes/
│   ├── __init__.py
│   └── mock_agents.py     # Mock agent nodes (replace with real agents)
└── tasks/
    ├── __init__.py
    └── pipeline_tasks.py  # Celery task wrappers
```

## Integrating Real Agents

Replace the mock nodes in `nodes/mock_agents.py` with your real Claude Agent SDK calls:

```python
# Before (mock):
async def research_node(state: PipelineState) -> Dict[str, Any]:
    await asyncio.sleep(10)  # Mock delay
    return {"research_doc": "mock research..."}

# After (real):
async def research_node(state: PipelineState) -> Dict[str, Any]:
    from app.agents.research import ResearchAgent

    agent = ResearchAgent()
    result = await agent.execute(
        connector_name=state["connector_name"],
        connector_type=state["connector_type"],
    )

    return {
        "research_doc": result.output,
        "current_phase": "researching",
    }
```

## Monitoring

### Celery Flower (Optional)

```bash
pip install flower
celery -A app.orchestrator.celery_app flower --port=5555
```

Open http://localhost:5555 for a web UI to monitor tasks.

### Redis CLI

```bash
# Monitor Redis activity
redis-cli monitor

# Check queue length
redis-cli llen pipeline
```

## Troubleshooting

### "No workers available"

1. Check Celery worker is running
2. Check Redis is running: `redis-cli ping`
3. Check worker logs for errors

### "Task timeout"

Increase limits in config:
```bash
ORCHESTRATOR_TASK_TIME_LIMIT=2400  # 40 minutes
```

### "Connection refused"

1. Start Redis: `brew services start redis`
2. Check Redis URL in config

### Resume Failed Pipeline

If a pipeline fails mid-execution, use the resume endpoint:
```bash
curl -X POST http://localhost:8002/orchestrator/pipeline/resume \
  -d '{"thread_id": "pipeline-connector-name-taskid"}'
```

## Next Steps

1. **Replace mock agents** with real Claude Agent SDK calls
2. **Add PostgreSQL checkpointer** for production persistence
3. **Add Flower** for monitoring
4. **Scale workers** horizontally for parallel pipelines
