"""FastAPI routes for the orchestrator v2.

Native async implementation without Celery.

These endpoints provide a REST API for:
- Starting new pipeline runs
- Checking pipeline status
- Resuming interrupted pipelines
- Streaming pipeline events
- Getting pipeline visualization
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from ..runner import (
    start_pipeline,
    get_pipeline_status,
    get_pipeline_history,
    resume_pipeline,
    cancel_pipeline,
    get_active_runs,
    stream_pipeline_events,
)
from ..pipeline import get_pipeline_diagram
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    """Request to start a new pipeline."""
    connector_name: str
    connector_type: str = "source"
    api_doc_url: Optional[str] = None
    original_request: Optional[str] = None


class PipelineResponse(BaseModel):
    """Response after starting a pipeline."""
    thread_id: str
    status: str
    message: str
    poll_url: str
    stream_url: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    """Response with pipeline status."""
    found: bool
    thread_id: str
    connector_name: Optional[str] = None
    status: Optional[str] = None
    current_phase: Optional[str] = None
    coverage_ratio: Optional[float] = None
    test_retries: Optional[int] = None
    gen_fix_retries: Optional[int] = None
    review_retries: Optional[int] = None
    research_retries: Optional[int] = None
    degraded_mode: Optional[bool] = None
    pr_url: Optional[str] = None
    next_nodes: Optional[list] = None
    is_active: Optional[bool] = None
    logs: Optional[list] = None
    message: Optional[str] = None


class ResumeRequest(BaseModel):
    """Request to resume a pipeline."""
    thread_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/pipeline/start", response_model=PipelineResponse)
async def start_pipeline_endpoint(request: PipelineRequest):
    """Start a new connector generation pipeline.

    This kicks off a native async task that runs the LangGraph pipeline.
    Use the returned thread_id to poll for status or stream events.

    Args:
        request: Pipeline configuration.

    Returns:
        Thread ID and polling/streaming URLs.
    """
    logger.info(f"Starting pipeline for: {request.connector_name}")

    try:
        # Start pipeline (runs in background via asyncio.create_task)
        thread_id = await start_pipeline(
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            api_doc_url=request.api_doc_url,
            original_request=request.original_request,
        )

        return PipelineResponse(
            thread_id=thread_id,
            status="started",
            message=f"Pipeline started for {request.connector_name}",
            poll_url=f"/orchestrator/pipeline/status/{thread_id}",
            stream_url=f"/orchestrator/pipeline/stream/{request.connector_name}",
        )

    except Exception as e:
        logger.exception(f"Failed to start pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {e}")


@router.get("/pipeline/status/{thread_id}")
async def get_status_endpoint(thread_id: str):
    """Get the current status of a pipeline.

    Reads from checkpointed state for accurate status.

    Args:
        thread_id: Thread ID of the pipeline.

    Returns:
        Current pipeline status and progress.
    """
    status = await get_pipeline_status(thread_id)

    if not status.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline not found: {thread_id}"
        )

    return status


@router.get("/pipeline/history/{thread_id}")
async def get_history_endpoint(thread_id: str):
    """Get the checkpoint history of a pipeline.

    Useful for debugging and time-travel.

    Args:
        thread_id: Thread ID of the pipeline.

    Returns:
        List of all checkpoints.
    """
    history = await get_pipeline_history(thread_id)

    if not history.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline history not found: {thread_id}"
        )

    return history


@router.post("/pipeline/resume", response_model=PipelineResponse)
async def resume_pipeline_endpoint(request: ResumeRequest):
    """Resume an interrupted pipeline from checkpoint.

    LangGraph automatically loads state and continues from last checkpoint.

    Args:
        request: Resume request with thread_id.

    Returns:
        Thread ID and polling URL.
    """
    logger.info(f"Resuming pipeline: {request.thread_id}")

    # Check if state exists first
    status = await get_pipeline_status(request.thread_id)

    if not status.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"No saved state found for thread: {request.thread_id}"
        )

    try:
        # Resume pipeline
        await resume_pipeline(request.thread_id)

        return PipelineResponse(
            thread_id=request.thread_id,
            status="resuming",
            message=f"Resuming pipeline from checkpoint",
            poll_url=f"/orchestrator/pipeline/status/{request.thread_id}",
        )

    except Exception as e:
        logger.exception(f"Failed to resume pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume: {e}")


@router.delete("/pipeline/cancel/{thread_id}")
async def cancel_pipeline_endpoint(thread_id: str):
    """Cancel a running pipeline.

    Args:
        thread_id: Thread ID of the pipeline to cancel.

    Returns:
        Cancellation status.
    """
    cancelled = await cancel_pipeline(thread_id)

    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline not found or already completed: {thread_id}"
        )

    return {
        "thread_id": thread_id,
        "status": "cancelled",
        "message": "Pipeline cancelled successfully",
    }


@router.get("/pipeline/stream/{connector_name}")
async def stream_pipeline(
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: Optional[str] = None,
):
    """Start a pipeline and stream events via Server-Sent Events.

    This endpoint starts a new pipeline and streams progress events
    in real-time. Useful for UI updates.

    Args:
        connector_name: Name of the connector.
        connector_type: Type (source/destination).
        api_doc_url: Optional API documentation URL.

    Returns:
        SSE stream of pipeline events.
    """
    async def event_generator():
        async for event in stream_pipeline_events(
            connector_name=connector_name,
            connector_type=connector_type,
            api_doc_url=api_doc_url,
        ):
            # Format as SSE
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/pipeline/diagram")
async def get_diagram():
    """Get the pipeline diagram in Mermaid format.

    Returns:
        Mermaid diagram string.
    """
    diagram = get_pipeline_diagram()
    return {
        "format": "mermaid",
        "diagram": diagram,
    }


@router.get("/pipelines/active")
async def list_active_pipelines():
    """List all active pipeline runs.

    Returns:
        List of active pipeline runs.
    """
    runs = get_active_runs()

    return {
        "count": len(runs),
        "pipelines": [
            {
                "thread_id": run.thread_id,
                "connector_name": run.connector_name,
                "status": run.status,
                "current_phase": run.current_phase,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "error": run.error,
            }
            for run in runs.values()
        ],
    }


@router.get("/health")
async def health_check():
    """Check orchestrator health.

    Verifies:
    - API is running
    - Checkpointer is configured
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "architecture": "native_async",
        "checkpointer": {
            "type": settings.checkpointer_type,
            "path": settings.sqlite_db_path if settings.checkpointer_type == "sqlite" else None,
        },
        "limits": {
            "max_test_retries": settings.max_test_retries,
            "max_gen_fix_retries": settings.max_gen_fix_retries,
            "max_review_retries": settings.max_review_retries,
            "max_research_retries": settings.max_research_retries,
            "max_concurrent_pipelines": settings.max_concurrent_pipelines,
        },
        "active_pipelines": len(get_active_runs()),
    }
