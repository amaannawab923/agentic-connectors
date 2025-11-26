"""FastAPI routes for connector generation."""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..config import Settings
from ..models.enums import PipelineState
from ..models.schemas import (
    ConnectorRequest,
    ConnectorResponse,
    BudgetStatus,
    PipelineStatus,
)
from ..core.pipeline import ConnectorPipeline
from ..agents.research import ResearchAgent
from ..agents.generator import GeneratorAgent
from ..agents.tester import TesterAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["connector-generator"])

# In-memory job storage (use Redis in production)
jobs: Dict[str, Dict] = {}
pipelines: Dict[str, ConnectorPipeline] = {}


class GenerateRequest(BaseModel):
    """Request model for connector generation."""

    connector_name: str = Field(
        ...,
        description="Name of the connector (e.g., 'google-sheets', 'salesforce')",
        min_length=2,
        max_length=50,
    )
    connector_type: str = Field(
        default="source",
        description="Type of connector: 'source' or 'destination'",
    )
    api_doc_url: Optional[str] = Field(
        default=None,
        description="URL to API documentation",
    )
    reference_repos: Optional[List[str]] = Field(
        default=None,
        description="List of GitHub repos to reference (format: owner/repo)",
    )
    custom_requirements: Optional[str] = Field(
        default=None,
        description="Additional requirements or notes",
    )
    test_credentials: Optional[Dict] = Field(
        default=None,
        description="Credentials for testing the connector",
    )
    repo_path: Optional[str] = Field(
        default=None,
        description="Path to git repository for publishing",
    )
    create_pr: bool = Field(
        default=True,
        description="Whether to create a pull request",
    )


class JobStatus(BaseModel):
    """Response model for job status."""

    job_id: str
    connector_name: str
    state: str
    budget_spent: float
    budget_remaining: float
    test_attempts: int
    review_cycles: int
    errors: List[str] = []
    pr_url: Optional[str] = None
    files_generated: List[str] = []


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@router.post("/generate", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def generate_connector(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    """Start connector generation pipeline.

    This endpoint starts a background task to generate a connector.
    Use the job_id to poll for status.
    """
    job_id = f"job-{uuid4().hex[:8]}"

    # Create connector request
    connector_request = ConnectorRequest(
        connector_name=request.connector_name,
        connector_type=request.connector_type,
        api_doc_url=request.api_doc_url,
        reference_repos=request.reference_repos,
        custom_requirements=request.custom_requirements,
        test_credentials=request.test_credentials,
        repo_path=request.repo_path,
        create_pr=request.create_pr,
    )

    # Initialize job tracking
    jobs[job_id] = {
        "job_id": job_id,
        "connector_name": request.connector_name,
        "state": PipelineState.PENDING.value,
        "budget_spent": 0.0,
        "budget_remaining": 7.0,
        "test_attempts": 0,
        "review_cycles": 0,
        "errors": [],
        "pr_url": None,
        "files_generated": [],
        "response": None,
    }

    # Create pipeline
    settings = Settings()
    pipeline = ConnectorPipeline(settings=settings)
    pipelines[job_id] = pipeline

    # Start background task
    background_tasks.add_task(
        run_pipeline_task,
        job_id=job_id,
        pipeline=pipeline,
        request=connector_request,
    )

    logger.info(f"Started generation job {job_id} for {request.connector_name}")

    return JobStatus(
        job_id=job_id,
        connector_name=request.connector_name,
        state=PipelineState.PENDING.value,
        budget_spent=0.0,
        budget_remaining=7.0,
        test_attempts=0,
        review_cycles=0,
    )


async def run_pipeline_task(
    job_id: str,
    pipeline: ConnectorPipeline,
    request: ConnectorRequest,
):
    """Background task to run the pipeline."""
    try:
        # Update state to running
        jobs[job_id]["state"] = PipelineState.RESEARCHING.value

        # Run the pipeline
        response = await pipeline.run(request)

        # Update job with results
        jobs[job_id].update({
            "state": response.status.state.value,
            "budget_spent": response.budget.total_spent,
            "budget_remaining": response.budget.remaining,
            "test_attempts": response.status.test_attempts,
            "review_cycles": response.status.review_cycles,
            "errors": response.status.errors,
            "pr_url": response.pr_url,
            "files_generated": response.files_generated,
            "response": response,
        })

        logger.info(f"Pipeline completed for job {job_id}: {response.status.state.value}")

    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}")
        jobs[job_id].update({
            "state": PipelineState.FAILED.value,
            "errors": [str(e)],
        })


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a generation job."""
    if job_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    job = jobs[job_id]

    # Get latest status from pipeline if available
    if job_id in pipelines:
        pipeline_status = pipelines[job_id].get_status()
        job["state"] = pipeline_status["state"]
        job["budget_spent"] = pipeline_status["budget"]["total_spent"]
        job["budget_remaining"] = pipeline_status["budget"]["remaining"]
        job["test_attempts"] = pipeline_status["test_attempts"]
        job["review_cycles"] = pipeline_status["review_cycles"]

    return JobStatus(
        job_id=job["job_id"],
        connector_name=job["connector_name"],
        state=job["state"],
        budget_spent=job["budget_spent"],
        budget_remaining=job["budget_remaining"],
        test_attempts=job["test_attempts"],
        review_cycles=job["review_cycles"],
        errors=job.get("errors", []),
        pr_url=job.get("pr_url"),
        files_generated=job.get("files_generated", []),
    )


@router.get("/jobs/{job_id}/result", response_model=ConnectorResponse)
async def get_job_result(job_id: str):
    """Get the full result of a completed generation job."""
    if job_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    job = jobs[job_id]

    if job["state"] not in [PipelineState.COMPLETED.value, PipelineState.FAILED.value, PipelineState.BUDGET_EXCEEDED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is still running (state: {job['state']})",
        )

    if job.get("response") is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job completed but no response available",
        )

    return job["response"]


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job (cleanup only - cannot stop in-progress operations)."""
    if job_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Mark as cancelled (actual cancellation is best-effort)
    jobs[job_id]["state"] = "cancelled"
    jobs[job_id]["errors"].append("Job cancelled by user")

    # Remove from active pipelines
    if job_id in pipelines:
        del pipelines[job_id]

    return {"message": f"Job {job_id} marked for cancellation"}


@router.get("/jobs", response_model=List[JobStatus])
async def list_jobs(
    state: Optional[str] = None,
    limit: int = 50,
):
    """List all generation jobs."""
    result = []

    for job_id, job in jobs.items():
        if state and job["state"] != state:
            continue

        result.append(JobStatus(
            job_id=job["job_id"],
            connector_name=job["connector_name"],
            state=job["state"],
            budget_spent=job["budget_spent"],
            budget_remaining=job["budget_remaining"],
            test_attempts=job["test_attempts"],
            review_cycles=job["review_cycles"],
            errors=job.get("errors", []),
            pr_url=job.get("pr_url"),
            files_generated=job.get("files_generated", []),
        ))

        if len(result) >= limit:
            break

    return result


@router.get("/budget/config")
async def get_budget_config():
    """Get the current budget configuration."""
    settings = Settings()
    return {
        "max_budget": settings.max_budget,
        "warning_threshold": settings.warning_threshold,
        "force_publish_threshold": settings.force_publish_threshold,
        "cost_per_research": settings.cost_per_research,
        "cost_per_generation": settings.cost_per_generation,
        "cost_per_test": settings.cost_per_test,
        "cost_per_review": settings.cost_per_review,
        "max_test_retries": settings.max_test_retries,
        "max_review_cycles": settings.max_review_cycles,
    }


@router.post("/validate")
async def validate_request(request: GenerateRequest):
    """Validate a connector generation request without starting it."""
    # Basic validation
    errors = []

    if not request.connector_name:
        errors.append("connector_name is required")

    if request.connector_type not in ["source", "destination"]:
        errors.append("connector_type must be 'source' or 'destination'")

    if request.reference_repos:
        for repo in request.reference_repos:
            if "/" not in repo:
                errors.append(f"Invalid repo format: {repo} (expected: owner/repo)")

    if errors:
        return {
            "valid": False,
            "errors": errors,
        }

    return {
        "valid": True,
        "estimated_cost": {
            "research": 0.60,
            "generation": 0.80,
            "testing": 0.10,
            "review": 0.13,
            "total_estimated": 1.63,
            "max_possible": 7.00,
        },
        "message": "Request is valid and ready for submission",
    }


# =============================================================================
# Agent Testing Endpoints
# =============================================================================

class ResearchRequest(BaseModel):
    """Request model for research agent - simplified interface."""

    connector_name: str = Field(
        ...,
        description="Natural name of the connector (e.g., 'Google Sheets', 'Salesforce', 'Stripe')",
        min_length=2,
        max_length=100,
    )
    additional_context: Optional[str] = Field(
        default=None,
        description="Any additional context or requirements for the research",
    )
    save_to_file: bool = Field(
        default=True,
        description="Save the research document to a .md file",
    )


class ResearchResponse(BaseModel):
    """Response model for research agent."""

    success: bool
    connector_name: str
    research_document: Optional[str] = None
    file_path: Optional[str] = None  # Path to saved .md file
    error: Optional[str] = None
    duration_seconds: float
    tokens_used: int
    estimated_cost: float


# In-memory storage for research jobs
research_jobs: Dict[str, Dict] = {}


@router.post("/agents/research", response_model=ResearchResponse)
async def run_research_agent(request: ResearchRequest):
    """Run the Research Agent to gather connector implementation patterns.

    Simply provide the connector name in natural language - the agent will:
    - Search GitHub for implementations in Airbyte, Meltano, Singer, and other repos
    - Find and analyze official API documentation
    - Extract authentication patterns, rate limits, and best practices
    - Generate a comprehensive research document

    Example requests:
    ```json
    {"connector_name": "Google Sheets"}
    {"connector_name": "Salesforce", "additional_context": "Focus on bulk API"}
    {"connector_name": "Stripe"}
    ```
    """
    start_time = time.time()
    job_id = f"research-{uuid4().hex[:8]}"

    logger.info(f"Starting research agent for {request.connector_name} (job: {job_id})")

    try:
        # Initialize the research agent
        settings = Settings()
        agent = ResearchAgent(settings=settings)

        # Execute the research with simplified parameters
        result = await agent.execute(
            connector_name=request.connector_name,
            additional_context=request.additional_context,
        )

        duration = time.time() - start_time

        # Store result for later retrieval
        research_jobs[job_id] = {
            "request": request.model_dump(),
            "result": result,
            "timestamp": time.time(),
        }

        logger.info(
            f"Research completed for {request.connector_name} in {duration:.2f}s "
            f"(success: {result.success}, tokens: {result.tokens_used})"
        )

        # Save research document to file
        file_path = None
        if result.success and result.output:
            from pathlib import Path
            from datetime import datetime

            # Create research-docs directory if it doesn't exist
            research_dir = Path(__file__).parent.parent.parent / "research-docs"
            research_dir.mkdir(exist_ok=True)

            # Generate filename: connector-name-YYYYMMDD-HHMMSS.md
            connector_slug = request.connector_name.lower().replace(" ", "-")
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{connector_slug}-research-{timestamp}.md"
            file_path = research_dir / filename

            # Write the markdown file
            file_path.write_text(result.output, encoding="utf-8")
            logger.info(f"Research saved to: {file_path}")
            file_path = str(file_path)

        return ResearchResponse(
            success=result.success,
            connector_name=request.connector_name,
            research_document=result.output if result.success else None,
            file_path=file_path,
            error=result.error,
            duration_seconds=duration,
            tokens_used=result.tokens_used or 0,
            estimated_cost=agent.estimate_cost(),
        )

    except Exception as e:
        logger.exception(f"Research agent failed for {request.connector_name}")
        return ResearchResponse(
            success=False,
            connector_name=request.connector_name,
            file_path=None,
            error=str(e),
            duration_seconds=time.time() - start_time,
            tokens_used=0,
            estimated_cost=0.0,
        )


@router.post("/agents/research/async", status_code=status.HTTP_202_ACCEPTED)
async def run_research_agent_async(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):
    """Run the Research Agent asynchronously in the background.

    Returns immediately with a job_id that can be used to poll for results.

    Example:
    ```json
    {"connector_name": "Google Sheets"}
    ```
    """
    job_id = f"research-{uuid4().hex[:8]}"

    # Initialize job
    research_jobs[job_id] = {
        "job_id": job_id,
        "connector_name": request.connector_name,
        "state": "running",
        "request": request.model_dump(),
        "result": None,
        "error": None,
        "started_at": time.time(),
        "completed_at": None,
    }

    # Start background task
    background_tasks.add_task(
        _run_research_task,
        job_id=job_id,
        request=request,
    )

    logger.info(f"Started async research job {job_id} for {request.connector_name}")

    return {
        "job_id": job_id,
        "connector_name": request.connector_name,
        "state": "running",
        "message": f"Research started. Poll /api/v1/agents/research/{job_id} for results.",
    }


async def _run_research_task(job_id: str, request: ResearchRequest):
    """Background task to run research agent."""
    try:
        settings = Settings()
        agent = ResearchAgent(settings=settings)

        result = await agent.execute(
            connector_name=request.connector_name,
            additional_context=request.additional_context,
        )

        research_jobs[job_id].update({
            "state": "completed" if result.success else "failed",
            "result": result.output if result.success else None,
            "error": result.error,
            "tokens_used": result.tokens_used or 0,
            "estimated_cost": agent.estimate_cost(),
            "completed_at": time.time(),
        })

        logger.info(f"Async research completed for job {job_id}")

    except Exception as e:
        logger.exception(f"Async research failed for job {job_id}")
        research_jobs[job_id].update({
            "state": "failed",
            "error": str(e),
            "completed_at": time.time(),
        })


@router.get("/agents/research/{job_id}")
async def get_research_result(job_id: str):
    """Get the result of an async research job."""
    if job_id not in research_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research job {job_id} not found",
        )

    job = research_jobs[job_id]

    response = {
        "job_id": job_id,
        "connector_name": job.get("connector_name"),
        "state": job.get("state"),
    }

    if job.get("state") == "running":
        response["message"] = "Research is still in progress"
        response["elapsed_seconds"] = time.time() - job.get("started_at", time.time())
    else:
        response["success"] = job.get("state") == "completed"
        response["research_document"] = job.get("result")
        response["error"] = job.get("error")
        response["tokens_used"] = job.get("tokens_used", 0)
        response["estimated_cost"] = job.get("estimated_cost", 0.0)
        response["duration_seconds"] = (
            job.get("completed_at", time.time()) - job.get("started_at", time.time())
        )

    return response


@router.get("/agents/research")
async def list_research_jobs(
    state: Optional[str] = None,
    limit: int = 20,
):
    """List all research jobs."""
    results = []

    for job_id, job in research_jobs.items():
        if state and job.get("state") != state:
            continue

        results.append({
            "job_id": job_id,
            "connector_name": job.get("connector_name"),
            "state": job.get("state"),
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
        })

        if len(results) >= limit:
            break

    return results


# =============================================================================
# Generator Agent Endpoints
# =============================================================================

class GeneratorRequest(BaseModel):
    """Request model for generator agent."""

    connector_name: str = Field(
        ...,
        description="Natural name of the connector (e.g., 'Google Sheets', 'Salesforce', 'Stripe')",
        min_length=2,
        max_length=100,
    )
    connector_type: str = Field(
        default="source",
        description="Type of connector: 'source' or 'destination'",
    )
    research_doc_path: str = Field(
        ...,
        description="Path to the research document .md file (from research agent output)",
    )
    fix_errors: Optional[List[str]] = Field(
        default=None,
        description="List of errors to fix from failed tests",
    )
    review_feedback: Optional[List[str]] = Field(
        default=None,
        description="List of improvements from code review",
    )


class GeneratorResponse(BaseModel):
    """Response model for generator agent."""

    success: bool
    connector_name: str
    connector_type: str
    output_dir: Optional[str] = None
    files_generated: int = 0
    file_paths: List[str] = []
    error: Optional[str] = None
    duration_seconds: float
    estimated_cost: float


# In-memory storage for generator jobs
generator_jobs: Dict[str, Dict] = {}


@router.post("/agents/generator", response_model=GeneratorResponse)
async def run_generator_agent(request: GeneratorRequest):
    """Run the Generator Agent to create connector code.

    Takes a research document path and generates a complete connector implementation
    in the `output/connector-implementations/{connector-type}-{connector-name}/` directory.

    Example requests:
    ```json
    {
        "connector_name": "Google Sheets",
        "connector_type": "source",
        "research_doc_path": "/path/to/google-sheets-research-20251125-123456.md"
    }
    ```
    """
    start_time = time.time()
    job_id = f"generator-{uuid4().hex[:8]}"

    logger.info(f"Starting generator agent for {request.connector_name} (job: {job_id})")
    logger.info(f"Research doc: {request.research_doc_path}")

    try:
        # Initialize the generator agent
        settings = Settings()
        agent = GeneratorAgent(settings=settings)

        # Execute the generator
        result = await agent.execute(
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            research_doc_path=request.research_doc_path,
            fix_errors=request.fix_errors,
            review_feedback=request.review_feedback,
        )

        duration = time.time() - start_time

        # Store result for later retrieval
        generator_jobs[job_id] = {
            "request": request.model_dump(),
            "result": result,
            "timestamp": time.time(),
        }

        # Parse the output JSON to get file info
        output_dir = None
        files_generated = 0
        file_paths = []

        if result.success and result.output:
            import json
            try:
                output_data = json.loads(result.output)
                output_dir = output_data.get("output_dir")
                files_generated = output_data.get("files_generated", 0)
                file_paths = output_data.get("file_paths", [])
            except json.JSONDecodeError:
                logger.warning("Could not parse generator output as JSON")

        logger.info(
            f"Generator completed for {request.connector_name} in {duration:.2f}s "
            f"(success: {result.success}, files: {files_generated})"
        )

        return GeneratorResponse(
            success=result.success,
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            output_dir=output_dir,
            files_generated=files_generated,
            file_paths=file_paths,
            error=result.error,
            duration_seconds=duration,
            estimated_cost=agent.estimate_cost(),
        )

    except Exception as e:
        logger.exception(f"Generator agent failed for {request.connector_name}")
        return GeneratorResponse(
            success=False,
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            error=str(e),
            duration_seconds=time.time() - start_time,
            estimated_cost=0.0,
        )


# =============================================================================
# Tester Agent Endpoints
# =============================================================================

class TesterRequest(BaseModel):
    """Request model for tester agent."""

    connector_name: str = Field(
        ...,
        description="Natural name of the connector (e.g., 'Google Sheets', 'Salesforce', 'Stripe')",
        min_length=2,
        max_length=100,
    )
    connector_type: str = Field(
        default="source",
        description="Type of connector: 'source' or 'destination'",
    )
    connector_dir: str = Field(
        ...,
        description="Path to the connector implementation directory",
    )


class TesterResponse(BaseModel):
    """Response model for tester agent."""

    success: bool
    connector_name: str
    connector_type: str
    status: str  # passed, failed, error
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    mock_server_started: bool = False
    connection_test_passed: bool = False
    discover_test_passed: bool = False
    read_test_passed: bool = False
    records_read: int = 0
    errors: List[str] = []
    logs: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float
    estimated_cost: float


# In-memory storage for tester jobs
tester_jobs: Dict[str, Dict] = {}


@router.post("/agents/tester", response_model=TesterResponse)
async def run_tester_agent(request: TesterRequest):
    """Run the Tester Agent to validate connector code with mock servers.

    This agent:
    1. Reads the connector's README.md and IMPLEMENTATION_SUMMARY.md
    2. Creates a mock server that mimics the target API
    3. Tests the connector against the mock server
    4. Reports detailed test results

    Example requests:
    ```json
    {
        "connector_name": "Google Sheets",
        "connector_type": "source",
        "connector_dir": "/path/to/source-google-sheets"
    }
    ```
    """
    start_time = time.time()
    job_id = f"tester-{uuid4().hex[:8]}"

    logger.info(f"Starting tester agent for {request.connector_name} (job: {job_id})")
    logger.info(f"Connector dir: {request.connector_dir}")

    try:
        # Initialize the tester agent
        settings = Settings()
        agent = TesterAgent(settings=settings)

        # Execute the tester
        result = await agent.execute(
            connector_dir=request.connector_dir,
            connector_name=request.connector_name,
            connector_type=request.connector_type,
        )

        duration = time.time() - start_time

        # Store result for later retrieval
        tester_jobs[job_id] = {
            "request": request.model_dump(),
            "result": result,
            "timestamp": time.time(),
        }

        # Parse the output JSON to get test results
        test_status = "error"
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        mock_server_started = False
        connection_test_passed = False
        discover_test_passed = False
        read_test_passed = False
        records_read = 0
        errors = []
        logs = None

        if result.success and result.output:
            import json
            try:
                output_data = json.loads(result.output)
                test_status = output_data.get("status", "error")
                tests_run = output_data.get("unit_tests_passed", 0) + output_data.get("unit_tests_failed", 0)
                tests_passed = output_data.get("unit_tests_passed", 0)
                tests_failed = output_data.get("unit_tests_failed", 0)
                connection_test_passed = output_data.get("connection_test_passed", False)
                discover_test_passed = output_data.get("discover_test_passed", False)
                read_test_passed = output_data.get("data_fetch_test_passed", False)
                records_read = output_data.get("sample_records_count", 0)
                errors = output_data.get("errors", [])
                logs = output_data.get("logs")
            except json.JSONDecodeError:
                logger.warning("Could not parse tester output as JSON")
                test_status = "passed" if result.success else "failed"
        else:
            test_status = "failed"
            if result.error:
                errors = [result.error]

        logger.info(
            f"Tester completed for {request.connector_name} in {duration:.2f}s "
            f"(status: {test_status}, passed: {tests_passed}, failed: {tests_failed})"
        )

        return TesterResponse(
            success=result.success,
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            status=test_status,
            tests_run=tests_run,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            mock_server_started=mock_server_started,
            connection_test_passed=connection_test_passed,
            discover_test_passed=discover_test_passed,
            read_test_passed=read_test_passed,
            records_read=records_read,
            errors=errors,
            logs=logs,
            error=result.error,
            duration_seconds=duration,
            estimated_cost=agent.estimate_cost(),
        )

    except Exception as e:
        logger.exception(f"Tester agent failed for {request.connector_name}")
        return TesterResponse(
            success=False,
            connector_name=request.connector_name,
            connector_type=request.connector_type,
            status="error",
            errors=[str(e)],
            error=str(e),
            duration_seconds=time.time() - start_time,
            estimated_cost=0.0,
        )
