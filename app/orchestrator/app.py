"""FastAPI application for the orchestrator v2.

Native LangGraph async implementation without Celery.
Supports persistent checkpointing via SQLite or PostgreSQL.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings
from .runner import cleanup_completed_runs
from .pipeline import get_checkpointer_async, close_checkpointer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Orchestrator API v2 (Native Async)...")
    logger.info(f"Checkpointer type: {settings.checkpointer_type}")
    if settings.checkpointer_type == "sqlite":
        logger.info(f"SQLite database: {settings.sqlite_db_path}")
    logger.info(f"Max test retries: {settings.max_test_retries}")
    logger.info(f"Max gen_fix retries: {settings.max_gen_fix_retries}")
    logger.info(f"Max review retries: {settings.max_review_retries}")
    logger.info(f"Max research retries: {settings.max_research_retries}")

    # Initialize checkpointer on startup
    try:
        await get_checkpointer_async()
        logger.info("Checkpointer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize checkpointer: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Orchestrator API v2...")
    await cleanup_completed_runs(max_age_seconds=0)  # Clean all completed runs
    await close_checkpointer()  # Close database connection


def create_app() -> FastAPI:
    """Create the FastAPI application."""

    app = FastAPI(
        title="Connector Orchestrator API v2",
        description="""
## Native LangGraph Pipeline Orchestrator

This API provides endpoints for running connector generation pipelines
with native async execution and persistent checkpointing.

### Architecture

```
FastAPI → Native Async (asyncio) → LangGraph Pipeline → SQLite/PostgreSQL
```

### Pipeline Flow (v2)

```
Research → Generator → Tester → TestReviewer ─┬─ VALID+PASS → Reviewer ─┬─ APPROVE → Publisher
                ↑         ↑                   │                         │
                │         │                   ├─ INVALID → Tester       ├─ REJECT:CODE → Generator
                │         │                   │                         │
                │         └───────────────────┴─ VALID+FAIL → Generator └─ REJECT:CONTEXT → Research
                │                                                                  │
                └──────────────────────────────────────────────────────────────────┘
```

### Features

- **Native async execution**: No Celery needed, runs in asyncio event loop
- **Persistent checkpointing**: SQLite (default) or PostgreSQL for state persistence
- **Progress streaming**: Real-time updates via SSE or polling
- **Resume capability**: Continue from last checkpoint even after server restart
- **Explicit retry counters**: test_retries, gen_fix_retries, review_retries, research_retries

### Checkpointing Options

| Type | Persistence | Use Case |
|------|-------------|----------|
| memory | No | Testing only |
| sqlite | Yes | Single-node deployment (default) |
| postgres | Yes | Multi-node / production |

Set via `ORCHESTRATOR_CHECKPOINTER_TYPE` environment variable.

### Coverage-Based Routing

- **100%**: APPROVE → Publisher (full success)
- **≥80%**: APPROVE (DEGRADED MODE) → Publisher (partial success)
- **50-79%**: REJECT:CODE → Generator (fix code)
- **<50%**: REJECT:CONTEXT → Research (need more API context)
        """,
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include orchestrator routes
    app.include_router(router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Connector Orchestrator API",
            "version": "2.0.0",
            "architecture": "Native LangGraph Async (no Celery)",
            "docs": "/docs",
            "health": "/orchestrator/health",
            "start_pipeline": "/orchestrator/pipeline/start",
            "stream_pipeline": "/orchestrator/pipeline/stream",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.orchestrator.app:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        reload_dirs=["app/orchestrator"],
    )
