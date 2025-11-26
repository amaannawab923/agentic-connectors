"""Celery tasks for running the LangGraph pipeline v2.

These tasks run the pipeline in background workers, allowing:
- Long-running execution (500-1000+ seconds)
- Fault tolerance (task requeued if worker dies)
- Progress tracking via task state
- Resume capability via checkpointing
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded

from ..celery_app import celery_app
from ..pipeline import create_pipeline_app, get_checkpointer
from ..state import create_initial_state, PipelineState, PipelineStatus
from ..config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="orchestrator.run_pipeline",
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    track_started=True,
)
def run_pipeline_task(
    self,
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: Optional[str] = None,
    original_request: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the complete connector generation pipeline v2.

    This task executes the LangGraph pipeline with checkpointing enabled,
    allowing for resume on failure.

    Args:
        connector_name: Name of the connector to generate.
        connector_type: Type of connector ("source" or "destination").
        api_doc_url: Optional URL to API documentation.
        original_request: Optional original user request text.

    Returns:
        Final pipeline state as dictionary.
    """
    task_id = self.request.id
    thread_id = f"pipeline-{connector_name}-{task_id[:8]}"

    logger.info(f"[TASK {task_id}] Starting pipeline v2 for {connector_name}")
    logger.info(f"[TASK {task_id}] Thread ID: {thread_id}")

    try:
        # Update task state to PROGRESS
        self.update_state(
            state="PROGRESS",
            meta={
                "phase": "starting",
                "connector_name": connector_name,
                "thread_id": thread_id,
                "started_at": datetime.utcnow().isoformat(),
            }
        )

        # Run the async pipeline
        result = _run_async(
            _execute_pipeline(
                task=self,
                connector_name=connector_name,
                connector_type=connector_type,
                api_doc_url=api_doc_url,
                original_request=original_request,
                thread_id=thread_id,
            )
        )

        logger.info(f"[TASK {task_id}] Pipeline completed for {connector_name}")
        return result

    except SoftTimeLimitExceeded:
        logger.error(f"[TASK {task_id}] Soft time limit exceeded!")
        return {
            "status": PipelineStatus.FAILED.value,
            "error": "Task exceeded soft time limit",
            "connector_name": connector_name,
            "thread_id": thread_id,
        }

    except Exception as e:
        logger.exception(f"[TASK {task_id}] Pipeline failed: {e}")
        raise  # Let Celery handle retry


async def _execute_pipeline(
    task,
    connector_name: str,
    connector_type: str,
    api_doc_url: Optional[str],
    original_request: Optional[str],
    thread_id: str,
) -> Dict[str, Any]:
    """Execute the LangGraph pipeline v2 asynchronously.

    Args:
        task: Celery task instance (for state updates).
        connector_name: Name of the connector.
        connector_type: Type of connector.
        api_doc_url: Optional API documentation URL.
        original_request: Optional original request text.
        thread_id: Thread ID for checkpointing.

    Returns:
        Final pipeline state.
    """
    # Create checkpointer for state persistence
    checkpointer = get_checkpointer()

    # Create pipeline app with checkpointing
    app = create_pipeline_app(checkpointer=checkpointer)

    # Create initial state with v2 parameters
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

    # Configuration for this run
    config = {"configurable": {"thread_id": thread_id}}

    # Update task state
    task.update_state(
        state="PROGRESS",
        meta={
            "phase": "running",
            "connector_name": connector_name,
            "thread_id": thread_id,
            "current_node": "research",
        }
    )

    # Execute the pipeline with streaming to track progress
    final_state = None

    async for event in app.astream(initial_state, config, stream_mode="values"):
        final_state = event

        # Update task state with v2 progress info
        current_phase = event.get("current_phase", "unknown")
        status = event.get("status", PipelineStatus.RUNNING.value)

        # v2 retry counters
        test_retries = event.get("test_retries", 0)
        gen_fix_retries = event.get("gen_fix_retries", 0)
        review_retries = event.get("review_retries", 0)
        research_retries = event.get("research_retries", 0)
        coverage_ratio = event.get("coverage_ratio", 0.0)

        task.update_state(
            state="PROGRESS",
            meta={
                "phase": current_phase,
                "status": status,
                "connector_name": connector_name,
                "thread_id": thread_id,
                # v2 counters
                "test_retries": test_retries,
                "gen_fix_retries": gen_fix_retries,
                "review_retries": review_retries,
                "research_retries": research_retries,
                "coverage_ratio": coverage_ratio,
                # Decisions
                "test_review_decision": event.get("test_review_decision"),
                "review_decision": event.get("review_decision"),
                # Mode
                "degraded_mode": event.get("degraded_mode", False),
                # Last 5 logs
                "logs": event.get("logs", [])[-5:],
            }
        )

        logger.info(
            f"[PIPELINE] Phase: {current_phase} | "
            f"test_retries: {test_retries}, gen_fix: {gen_fix_retries}, "
            f"review: {review_retries}, research: {research_retries} | "
            f"coverage: {coverage_ratio*100:.0f}%"
        )

    return dict(final_state) if final_state else {}


@celery_app.task(
    bind=True,
    name="orchestrator.resume_pipeline",
    max_retries=1,
)
def resume_pipeline_task(self, thread_id: str) -> Dict[str, Any]:
    """Resume a previously interrupted pipeline.

    Args:
        thread_id: Thread ID of the pipeline to resume.

    Returns:
        Final pipeline state.
    """
    task_id = self.request.id
    logger.info(f"[TASK {task_id}] Resuming pipeline: {thread_id}")

    try:
        result = _run_async(_resume_pipeline(task=self, thread_id=thread_id))
        logger.info(f"[TASK {task_id}] Pipeline resumed and completed")
        return result

    except Exception as e:
        logger.exception(f"[TASK {task_id}] Resume failed: {e}")
        raise


async def _resume_pipeline(task, thread_id: str) -> Dict[str, Any]:
    """Resume pipeline execution from checkpoint.

    Args:
        task: Celery task instance.
        thread_id: Thread ID to resume.

    Returns:
        Final pipeline state.
    """
    checkpointer = get_checkpointer()
    app = create_pipeline_app(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    # Get current state
    state_snapshot = await app.aget_state(config)

    if not state_snapshot.values:
        raise ValueError(f"No saved state found for thread: {thread_id}")

    logger.info(f"[RESUME] Found state at: {state_snapshot.next}")

    # Continue execution
    final_state = None
    async for event in app.astream(None, config, stream_mode="values"):
        final_state = event
        current_phase = event.get("current_phase", "unknown")
        task.update_state(
            state="PROGRESS",
            meta={
                "phase": current_phase,
                "thread_id": thread_id,
                "status": event.get("status", PipelineStatus.RUNNING.value),
            }
        )

    return dict(final_state) if final_state else {}


@celery_app.task(name="orchestrator.get_pipeline_state")
def get_pipeline_state_task(thread_id: str) -> Dict[str, Any]:
    """Get current state of a pipeline.

    Args:
        thread_id: Thread ID of the pipeline.

    Returns:
        Current pipeline state or empty dict if not found.
    """
    return _run_async(_get_state(thread_id))


async def _get_state(thread_id: str) -> Dict[str, Any]:
    """Get pipeline state from checkpoint."""
    checkpointer = get_checkpointer()
    app = create_pipeline_app(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = await app.aget_state(config)

    if state_snapshot.values:
        return {
            "found": True,
            "state": dict(state_snapshot.values),
            "next_nodes": list(state_snapshot.next) if state_snapshot.next else [],
        }

    return {"found": False, "state": {}, "next_nodes": []}
