"""Native LangGraph Pipeline Orchestrator v2.

This module provides a production-ready orchestration system for
long-running connector generation pipelines using native async execution.

Components:
- LangGraph: State machine with conditional routing
- Native Async: asyncio-based background execution
- SQLite/PostgreSQL: Checkpoint persistence

Usage:
    # Start a pipeline via API
    POST /orchestrator/pipeline/start
    {"connector_name": "google-sheets"}

    # Or directly via runner
    from app.orchestrator.runner import start_pipeline, get_pipeline_status
    thread_id = await start_pipeline("google-sheets", "source")
    status = await get_pipeline_status(thread_id)
"""

from .config import settings, OrchestratorSettings
from .state import (
    PipelineState,
    PipelinePhase,
    PipelineStatus,
    ReviewDecision,
    TestReviewDecision,
    create_initial_state,
)
from .pipeline import build_pipeline, create_pipeline_app, create_pipeline_app_async, get_pipeline_diagram
from .runner import (
    start_pipeline,
    get_pipeline_status,
    get_pipeline_history,
    resume_pipeline,
    cancel_pipeline,
    execute_pipeline,
    stream_pipeline_events,
)

__all__ = [
    # Config
    "settings",
    "OrchestratorSettings",
    # State
    "PipelineState",
    "PipelinePhase",
    "PipelineStatus",
    "ReviewDecision",
    "TestReviewDecision",
    "create_initial_state",
    # Pipeline
    "build_pipeline",
    "create_pipeline_app",
    "create_pipeline_app_async",
    "get_pipeline_diagram",
    # Runner (Native Async)
    "start_pipeline",
    "get_pipeline_status",
    "get_pipeline_history",
    "resume_pipeline",
    "cancel_pipeline",
    "execute_pipeline",
    "stream_pipeline_events",
]
