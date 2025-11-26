"""Native async pipeline runner for LangGraph.

This module provides async execution of the pipeline without Celery.
LangGraph handles:
- Durable execution via checkpointing
- Resume on failure via thread_id
- Progress tracking via streaming events

Usage:
    # Start a pipeline
    thread_id = await start_pipeline("my-connector")

    # Get status
    status = await get_pipeline_status(thread_id)

    # Resume interrupted pipeline
    await resume_pipeline(thread_id)
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field

from .pipeline import create_pipeline_app_async, get_checkpointer_async, build_pipeline
from .state import create_initial_state, PipelineState, PipelineStatus
from .config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Run Tracking (in-memory for active runs)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineRun:
    """Track active pipeline execution."""
    thread_id: str
    connector_name: str
    status: str = "starting"
    current_phase: str = "pending"
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None


# Active runs (thread_id -> PipelineRun)
_active_runs: Dict[str, PipelineRun] = {}


def get_active_runs() -> Dict[str, PipelineRun]:
    """Get all active pipeline runs."""
    return _active_runs.copy()


def get_active_run(thread_id: str) -> Optional[PipelineRun]:
    """Get a specific active run."""
    return _active_runs.get(thread_id)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Execution
# ─────────────────────────────────────────────────────────────────────────────

async def execute_pipeline(
    thread_id: str,
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: Optional[str] = None,
    original_request: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the pipeline asynchronously.

    This is the core execution function. LangGraph handles:
    - Checkpointing at each node (automatic state persistence)
    - Resume from failure (pass None to continue from checkpoint)

    Args:
        thread_id: Unique identifier for this pipeline run.
        connector_name: Name of the connector to generate.
        connector_type: Type ("source" or "destination").
        api_doc_url: Optional API documentation URL.
        original_request: Optional original user request.

    Returns:
        Final pipeline state.
    """
    logger.info(f"[PIPELINE {thread_id}] Starting execution for {connector_name}")

    # Track this run
    run = PipelineRun(
        thread_id=thread_id,
        connector_name=connector_name,
        status="running",
    )
    _active_runs[thread_id] = run

    try:
        # Create pipeline with checkpointer
        app = await create_pipeline_app_async()

        # Create initial state
        initial_state = create_initial_state(
            connector_name=connector_name,
            connector_type=connector_type,
            api_doc_url=api_doc_url,
            original_request=original_request,
            max_test_retries=settings.max_test_retries,
            max_gen_fix_retries=settings.max_gen_fix_retries,
            max_review_retries=settings.max_review_retries,
            max_research_retries=settings.max_research_retries,
        )

        # Configuration for this run (thread_id enables checkpointing)
        config = {"configurable": {"thread_id": thread_id}}

        # Execute pipeline with streaming to track progress
        final_state = None

        async for event in app.astream(initial_state, config, stream_mode="values"):
            final_state = event

            # Update run tracking
            run.current_phase = event.get("current_phase", "unknown")
            run.status = event.get("status", PipelineStatus.RUNNING.value)

            # Log progress
            logger.info(
                f"[PIPELINE {thread_id}] Phase: {run.current_phase} | "
                f"test_retries: {event.get('test_retries', 0)}, "
                f"gen_fix: {event.get('gen_fix_retries', 0)}, "
                f"review: {event.get('review_retries', 0)}, "
                f"research: {event.get('research_retries', 0)} | "
                f"coverage: {event.get('coverage_ratio', 0.0)*100:.0f}%"
            )

        # Mark completed
        run.status = final_state.get("status", "unknown") if final_state else "failed"
        run.completed_at = datetime.utcnow().isoformat()

        logger.info(f"[PIPELINE {thread_id}] Completed with status: {run.status}")
        return dict(final_state) if final_state else {"status": "failed"}

    except Exception as e:
        logger.exception(f"[PIPELINE {thread_id}] Failed with error: {e}")
        run.status = "failed"
        run.error = str(e)
        run.completed_at = datetime.utcnow().isoformat()
        raise

    finally:
        # Keep in active runs for status queries (cleanup after timeout)
        pass


async def resume_pipeline(thread_id: str) -> Dict[str, Any]:
    """Resume an interrupted pipeline from its last checkpoint.

    LangGraph automatically:
    - Loads state from the last checkpoint
    - Skips already-executed nodes
    - Continues from where it left off

    Args:
        thread_id: Thread ID of the pipeline to resume.

    Returns:
        Final pipeline state.
    """
    logger.info(f"[PIPELINE {thread_id}] Resuming execution...")

    # Get or create run tracking
    run = _active_runs.get(thread_id)
    if not run:
        run = PipelineRun(thread_id=thread_id, connector_name="unknown", status="resuming")
        _active_runs[thread_id] = run
    else:
        run.status = "resuming"

    try:
        # Create pipeline with checkpointer
        app = await create_pipeline_app_async()
        config = {"configurable": {"thread_id": thread_id}}

        # Check if there's state to resume from
        state_snapshot = await app.aget_state(config)
        if not state_snapshot.values:
            raise ValueError(f"No saved state found for thread: {thread_id}")

        logger.info(f"[PIPELINE {thread_id}] Resuming from: {state_snapshot.next}")

        # Update connector name from saved state
        run.connector_name = state_snapshot.values.get("connector_name", "unknown")

        # Resume execution (pass None to continue from checkpoint)
        final_state = None
        async for event in app.astream(None, config, stream_mode="values"):
            final_state = event
            run.current_phase = event.get("current_phase", "unknown")
            run.status = event.get("status", PipelineStatus.RUNNING.value)

            logger.info(f"[PIPELINE {thread_id}] Resumed - Phase: {run.current_phase}")

        run.status = final_state.get("status", "unknown") if final_state else "failed"
        run.completed_at = datetime.utcnow().isoformat()

        logger.info(f"[PIPELINE {thread_id}] Resume completed with status: {run.status}")
        return dict(final_state) if final_state else {"status": "failed"}

    except Exception as e:
        logger.exception(f"[PIPELINE {thread_id}] Resume failed: {e}")
        run.status = "failed"
        run.error = str(e)
        raise


async def get_pipeline_status(thread_id: str) -> Dict[str, Any]:
    """Get the current status of a pipeline.

    Checks both active runs and checkpointed state.

    Args:
        thread_id: Thread ID of the pipeline.

    Returns:
        Status dictionary with current state.
    """
    # Check active runs first
    run = _active_runs.get(thread_id)

    # Get state from checkpointer
    try:
        app = await create_pipeline_app_async()
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = await app.aget_state(config)

        if state_snapshot.values:
            state = state_snapshot.values
            return {
                "found": True,
                "thread_id": thread_id,
                "connector_name": state.get("connector_name"),
                "status": state.get("status"),
                "current_phase": state.get("current_phase"),
                "coverage_ratio": state.get("coverage_ratio", 0.0),
                "test_retries": state.get("test_retries", 0),
                "gen_fix_retries": state.get("gen_fix_retries", 0),
                "review_retries": state.get("review_retries", 0),
                "research_retries": state.get("research_retries", 0),
                "degraded_mode": state.get("degraded_mode", False),
                "pr_url": state.get("pr_url"),
                "next_nodes": list(state_snapshot.next) if state_snapshot.next else [],
                "is_active": run is not None and run.completed_at is None,
                "logs": state.get("logs", [])[-10:],  # Last 10 logs
            }
    except Exception as e:
        logger.warning(f"Could not get checkpoint state for {thread_id}: {e}")

    # Fall back to active run tracking
    if run:
        return {
            "found": True,
            "thread_id": thread_id,
            "connector_name": run.connector_name,
            "status": run.status,
            "current_phase": run.current_phase,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "error": run.error,
            "is_active": run.completed_at is None,
            "next_nodes": [],
            "logs": [],
        }

    return {
        "found": False,
        "thread_id": thread_id,
        "message": "Pipeline not found",
    }


async def get_pipeline_history(thread_id: str) -> Dict[str, Any]:
    """Get the full checkpoint history for a pipeline.

    Useful for debugging and time-travel.

    Args:
        thread_id: Thread ID of the pipeline.

    Returns:
        History with all checkpoints.
    """
    try:
        app = await create_pipeline_app_async()
        config = {"configurable": {"thread_id": thread_id}}

        checkpoints = []
        async for state_snapshot in app.aget_state_history(config):
            checkpoints.append({
                "checkpoint_id": state_snapshot.config.get("configurable", {}).get("checkpoint_id"),
                "phase": state_snapshot.values.get("current_phase"),
                "status": state_snapshot.values.get("status"),
                "next_nodes": list(state_snapshot.next) if state_snapshot.next else [],
            })

        return {
            "found": True,
            "thread_id": thread_id,
            "checkpoints": checkpoints,
            "total_checkpoints": len(checkpoints),
        }

    except Exception as e:
        logger.warning(f"Could not get history for {thread_id}: {e}")
        return {
            "found": False,
            "thread_id": thread_id,
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def generate_thread_id(connector_name: str) -> str:
    """Generate a unique thread ID for a pipeline run.

    Args:
        connector_name: Name of the connector.

    Returns:
        Unique thread ID.
    """
    short_uuid = uuid.uuid4().hex[:8]
    return f"pipeline-{connector_name}-{short_uuid}"


async def start_pipeline(
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: Optional[str] = None,
    original_request: Optional[str] = None,
) -> str:
    """Start a new pipeline execution in the background.

    This is the main entry point for starting pipelines.

    Args:
        connector_name: Name of the connector to generate.
        connector_type: Type ("source" or "destination").
        api_doc_url: Optional API documentation URL.
        original_request: Optional original user request.

    Returns:
        Thread ID for tracking the pipeline.
    """
    thread_id = generate_thread_id(connector_name)

    # Create background task
    task = asyncio.create_task(
        execute_pipeline(
            thread_id=thread_id,
            connector_name=connector_name,
            connector_type=connector_type,
            api_doc_url=api_doc_url,
            original_request=original_request,
        )
    )

    # Store task reference
    if thread_id in _active_runs:
        _active_runs[thread_id].task = task

    logger.info(f"Started pipeline with thread_id: {thread_id}")
    return thread_id


async def cancel_pipeline(thread_id: str) -> bool:
    """Cancel a running pipeline.

    Args:
        thread_id: Thread ID of the pipeline to cancel.

    Returns:
        True if cancelled, False if not found or already completed.
    """
    run = _active_runs.get(thread_id)
    if not run or not run.task:
        return False

    if run.task.done():
        return False

    run.task.cancel()
    run.status = "cancelled"
    run.completed_at = datetime.utcnow().isoformat()

    logger.info(f"Cancelled pipeline: {thread_id}")
    return True


async def cleanup_completed_runs(max_age_seconds: int = 3600):
    """Clean up completed runs older than max_age.

    Args:
        max_age_seconds: Maximum age in seconds before cleanup.
    """
    now = datetime.utcnow()
    to_remove = []

    for thread_id, run in _active_runs.items():
        if run.completed_at:
            completed = datetime.fromisoformat(run.completed_at)
            age = (now - completed).total_seconds()
            if age > max_age_seconds:
                to_remove.append(thread_id)

    for thread_id in to_remove:
        del _active_runs[thread_id]

    if to_remove:
        logger.info(f"Cleaned up {len(to_remove)} completed pipeline runs")


# ─────────────────────────────────────────────────────────────────────────────
# Streaming Events (for real-time updates)
# ─────────────────────────────────────────────────────────────────────────────

async def stream_pipeline_events(
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute pipeline and stream events as they occur.

    Useful for real-time UI updates.

    Args:
        connector_name: Name of the connector.
        connector_type: Type of connector.
        api_doc_url: Optional API documentation URL.

    Yields:
        Event dictionaries with pipeline progress.
    """
    thread_id = generate_thread_id(connector_name)

    yield {
        "type": "started",
        "thread_id": thread_id,
        "connector_name": connector_name,
    }

    try:
        app = await create_pipeline_app_async()
        initial_state = create_initial_state(
            connector_name=connector_name,
            connector_type=connector_type,
            api_doc_url=api_doc_url,
        )
        config = {"configurable": {"thread_id": thread_id}}

        async for event in app.astream(initial_state, config, stream_mode="values"):
            yield {
                "type": "progress",
                "thread_id": thread_id,
                "phase": event.get("current_phase"),
                "status": event.get("status"),
                "coverage_ratio": event.get("coverage_ratio", 0.0),
                "test_retries": event.get("test_retries", 0),
                "gen_fix_retries": event.get("gen_fix_retries", 0),
                "review_retries": event.get("review_retries", 0),
                "research_retries": event.get("research_retries", 0),
            }

        yield {
            "type": "completed",
            "thread_id": thread_id,
            "status": event.get("status") if event else "unknown",
            "pr_url": event.get("pr_url") if event else None,
        }

    except Exception as e:
        yield {
            "type": "error",
            "thread_id": thread_id,
            "error": str(e),
        }
