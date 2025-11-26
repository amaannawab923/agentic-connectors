"""Pydantic schemas for the Connector Generator."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from .enums import PipelineState, AgentType, TestStatus, ReviewDecision


class CredentialsConfig(BaseModel):
    """Credentials configuration for testing the connector."""

    auth_type: str = Field(..., description="Authentication type (oauth2, service_account, api_key)")
    credentials_data: Dict[str, Any] = Field(..., description="Credential data for testing")


class ConnectorRequest(BaseModel):
    """Request to generate a new connector."""

    connector_name: str = Field(..., description="Name of the connector (e.g., 'google-sheets')")
    connector_type: str = Field(default="source", description="Type: source or destination")
    api_documentation_url: Optional[str] = Field(
        default=None,
        description="URL to API documentation"
    )
    reference_repos: List[str] = Field(
        default_factory=list,
        description="GitHub repos to reference for implementation patterns"
    )
    credentials: Optional[CredentialsConfig] = Field(
        default=None,
        description="Test credentials for validation"
    )
    custom_requirements: Optional[str] = Field(
        default=None,
        description="Additional requirements or notes"
    )
    max_budget: float = Field(
        default=7.00,
        ge=1.0,
        le=20.0,
        description="Maximum budget for this connector generation"
    )


class BudgetStatus(BaseModel):
    """Current budget status."""

    spent: float = Field(default=0.0, description="Amount spent so far")
    remaining: float = Field(..., description="Remaining budget")
    max_budget: float = Field(..., description="Maximum allowed budget")
    percent_used: float = Field(..., description="Percentage of budget used")
    warning: bool = Field(default=False, description="Whether budget warning threshold reached")
    exceeded: bool = Field(default=False, description="Whether budget limit exceeded")


class CostLogEntry(BaseModel):
    """Single entry in the cost log."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    operation: str = Field(..., description="Operation name")
    agent: AgentType = Field(..., description="Agent that performed the operation")
    cost: float = Field(..., description="Cost of this operation")
    total_spent: float = Field(..., description="Running total after this operation")
    details: Optional[str] = Field(default=None, description="Additional details")


class TestResult(BaseModel):
    """Result of running tests."""

    status: TestStatus = Field(..., description="Overall test status")
    passed: bool = Field(..., description="Whether all tests passed")
    unit_tests_passed: int = Field(default=0)
    unit_tests_failed: int = Field(default=0)
    connection_test_passed: bool = Field(default=False)
    data_fetch_test_passed: bool = Field(default=False)
    sample_records_count: int = Field(default=0)
    errors: List[str] = Field(default_factory=list, description="Error messages")
    logs: str = Field(default="", description="Full test output logs")
    duration_seconds: float = Field(default=0.0)


class ReviewComment(BaseModel):
    """Single review comment."""

    file: str = Field(..., description="File path")
    line: Optional[int] = Field(default=None, description="Line number")
    severity: str = Field(default="info", description="Severity: info, warning, error")
    message: str = Field(..., description="Comment message")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")


class ReviewResult(BaseModel):
    """Result of code review."""

    decision: ReviewDecision = Field(..., description="Review decision")
    approved: bool = Field(..., description="Whether code is approved")
    score: float = Field(default=0.0, ge=0.0, le=10.0, description="Quality score")
    comments: List[ReviewComment] = Field(default_factory=list)
    summary: str = Field(default="", description="Review summary")
    improvements_required: List[str] = Field(
        default_factory=list,
        description="List of required improvements"
    )


class AgentResult(BaseModel):
    """Generic result from any agent."""

    agent: AgentType = Field(..., description="Agent that produced this result")
    success: bool = Field(..., description="Whether operation succeeded")
    output: Optional[str] = Field(default=None, description="Agent output/content")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    duration_seconds: float = Field(default=0.0)
    tokens_used: int = Field(default=0, description="Tokens consumed")
    cost: float = Field(default=0.0, description="Cost of this operation")


class GeneratedFile(BaseModel):
    """A generated code file."""

    path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File content")
    description: Optional[str] = Field(default=None, description="File description")


class PipelineStatus(BaseModel):
    """Current status of the pipeline."""

    job_id: str = Field(..., description="Unique job identifier")
    connector_name: str = Field(..., description="Connector being generated")
    state: PipelineState = Field(..., description="Current pipeline state")
    test_retry_count: int = Field(default=0)
    review_cycle_count: int = Field(default=0)
    budget: BudgetStatus = Field(...)
    cost_log: List[CostLogEntry] = Field(default_factory=list)
    current_agent: Optional[AgentType] = Field(default=None)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class ConnectorResponse(BaseModel):
    """Response for a connector generation request."""

    job_id: str = Field(..., description="Unique job identifier")
    status: PipelineStatus = Field(..., description="Current pipeline status")
    research_doc: Optional[str] = Field(default=None, description="Generated research document")
    generated_files: List[GeneratedFile] = Field(
        default_factory=list,
        description="Generated code files"
    )
    test_results: Optional[TestResult] = Field(default=None)
    review_results: Optional[ReviewResult] = Field(default=None)
    pr_url: Optional[str] = Field(default=None, description="GitHub PR URL if published")
    output_directory: Optional[str] = Field(
        default=None,
        description="Local directory with generated files"
    )


class JobListItem(BaseModel):
    """Summary item for job listing."""

    job_id: str
    connector_name: str
    state: PipelineState
    budget_spent: float
    created_at: datetime
    updated_at: datetime
