"""State management for pipeline execution."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import uuid

from ..models.enums import PipelineState, AgentType
from ..models.schemas import (
    PipelineStatus,
    BudgetStatus,
    CostLogEntry,
    TestResult,
    ReviewResult,
    GeneratedFile,
)
from .budget import BudgetController

logger = logging.getLogger(__name__)


@dataclass
class PipelineStateManager:
    """Manages the state of a connector generation pipeline.

    This class tracks all state throughout the pipeline execution,
    including budget, retries, generated artifacts, and results.
    """

    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connector_name: str = ""
    connector_type: str = "source"

    # Pipeline state
    state: PipelineState = PipelineState.PENDING
    previous_state: Optional[PipelineState] = None

    # Retry tracking
    test_retry_count: int = 0
    review_cycle_count: int = 0
    max_test_retries: int = 3
    max_review_cycles: int = 2

    # Budget
    budget: BudgetController = field(default_factory=BudgetController)

    # Timestamps
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Artifacts
    research_doc: Optional[str] = None
    generated_files: List[GeneratedFile] = field(default_factory=list)
    test_results: Optional[TestResult] = None
    review_results: Optional[ReviewResult] = None
    error_logs: List[str] = field(default_factory=list)

    # Output
    output_directory: Optional[str] = None
    pr_url: Optional[str] = None

    # Current agent
    current_agent: Optional[AgentType] = None

    # Error tracking
    error_message: Optional[str] = None

    def initialize(
        self,
        connector_name: str,
        connector_type: str = "source",
        max_budget: float = 7.00,
        max_test_retries: int = 3,
        max_review_cycles: int = 2,
    ) -> None:
        """Initialize the state manager for a new job.

        Args:
            connector_name: Name of the connector to generate.
            connector_type: Type of connector (source/destination).
            max_budget: Maximum budget for this job.
            max_test_retries: Maximum test retry attempts.
            max_review_cycles: Maximum review cycles.
        """
        self.connector_name = connector_name
        self.connector_type = connector_type
        self.max_test_retries = max_test_retries
        self.max_review_cycles = max_review_cycles
        self.budget = BudgetController(max_budget=max_budget)
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.state = PipelineState.PENDING

        logger.info(
            f"Pipeline initialized: job_id={self.job_id}, "
            f"connector={connector_name}, budget=${max_budget}"
        )

    def transition_to(self, new_state: PipelineState) -> None:
        """Transition to a new pipeline state.

        Args:
            new_state: The state to transition to.
        """
        self.previous_state = self.state
        self.state = new_state
        self.updated_at = datetime.utcnow()

        if new_state in [
            PipelineState.COMPLETED,
            PipelineState.FAILED,
            PipelineState.BUDGET_EXCEEDED,
            PipelineState.CANCELLED,
        ]:
            self.completed_at = datetime.utcnow()

        logger.info(
            f"Pipeline state transition: {self.previous_state.value} -> {new_state.value}"
        )

    def set_current_agent(self, agent: Optional[AgentType]) -> None:
        """Set the currently active agent.

        Args:
            agent: The agent currently executing, or None if idle.
        """
        self.current_agent = agent
        self.updated_at = datetime.utcnow()

    def increment_test_retries(self) -> bool:
        """Increment test retry count.

        Returns:
            True if more retries are allowed, False otherwise.
        """
        self.test_retry_count += 1
        self.updated_at = datetime.utcnow()
        return self.test_retry_count < self.max_test_retries

    def increment_review_cycles(self) -> bool:
        """Increment review cycle count.

        Returns:
            True if more review cycles are allowed, False otherwise.
        """
        self.review_cycle_count += 1
        self.updated_at = datetime.utcnow()
        return self.review_cycle_count < self.max_review_cycles

    def can_retry_tests(self) -> bool:
        """Check if more test retries are allowed.

        Returns:
            True if more retries available.
        """
        return self.test_retry_count < self.max_test_retries

    def can_review_again(self) -> bool:
        """Check if more review cycles are allowed.

        Returns:
            True if more review cycles available.
        """
        return self.review_cycle_count < self.max_review_cycles

    def set_research_doc(self, content: str) -> None:
        """Store the generated research document.

        Args:
            content: Research document content.
        """
        self.research_doc = content
        self.updated_at = datetime.utcnow()
        logger.info(f"Research doc stored: {len(content)} characters")

    def set_generated_files(self, files: List[GeneratedFile]) -> None:
        """Store generated code files.

        Args:
            files: List of generated files.
        """
        self.generated_files = files
        self.updated_at = datetime.utcnow()
        logger.info(f"Generated files stored: {len(files)} files")

    def update_generated_files(self, files: List[GeneratedFile]) -> None:
        """Update/replace generated code files.

        Args:
            files: Updated list of generated files.
        """
        self.generated_files = files
        self.updated_at = datetime.utcnow()

    def set_test_results(self, results: TestResult) -> None:
        """Store test results.

        Args:
            results: Test execution results.
        """
        self.test_results = results
        self.updated_at = datetime.utcnow()

        if not results.passed:
            self.error_logs.extend(results.errors)

    def set_review_results(self, results: ReviewResult) -> None:
        """Store review results.

        Args:
            results: Code review results.
        """
        self.review_results = results
        self.updated_at = datetime.utcnow()

    def set_error(self, error_message: str) -> None:
        """Record an error.

        Args:
            error_message: Error description.
        """
        self.error_message = error_message
        self.error_logs.append(f"[{datetime.utcnow().isoformat()}] {error_message}")
        self.updated_at = datetime.utcnow()
        logger.error(f"Pipeline error: {error_message}")

    def set_output_directory(self, directory: str) -> None:
        """Set the output directory path.

        Args:
            directory: Path to output directory.
        """
        self.output_directory = directory
        self.updated_at = datetime.utcnow()

    def set_pr_url(self, url: str) -> None:
        """Set the GitHub PR URL.

        Args:
            url: PR URL.
        """
        self.pr_url = url
        self.updated_at = datetime.utcnow()

    def is_terminal_state(self) -> bool:
        """Check if pipeline is in a terminal state.

        Returns:
            True if pipeline has reached a final state.
        """
        return self.state in [
            PipelineState.COMPLETED,
            PipelineState.FAILED,
            PipelineState.BUDGET_EXCEEDED,
            PipelineState.CANCELLED,
        ]

    def get_status(self) -> PipelineStatus:
        """Get current pipeline status.

        Returns:
            PipelineStatus object with current state.
        """
        return PipelineStatus(
            job_id=self.job_id,
            connector_name=self.connector_name,
            state=self.state,
            test_retry_count=self.test_retry_count,
            review_cycle_count=self.review_cycle_count,
            budget=self.budget.get_status(),
            cost_log=self.budget.get_cost_log(),
            current_agent=self.current_agent,
            started_at=self.started_at or datetime.utcnow(),
            updated_at=self.updated_at or datetime.utcnow(),
            completed_at=self.completed_at,
            error_message=self.error_message,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization.

        Returns:
            Dictionary representation of state.
        """
        return {
            "job_id": self.job_id,
            "connector_name": self.connector_name,
            "connector_type": self.connector_type,
            "state": self.state.value,
            "test_retry_count": self.test_retry_count,
            "review_cycle_count": self.review_cycle_count,
            "budget": self.budget.get_status().model_dump(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "pr_url": self.pr_url,
            "output_directory": self.output_directory,
        }

    def save_to_file(self, filepath: str) -> None:
        """Save state to a JSON file.

        Args:
            filepath: Path to save the state file.
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.debug(f"State saved to {filepath}")

    @classmethod
    def load_from_file(cls, filepath: str) -> "PipelineStateManager":
        """Load state from a JSON file.

        Args:
            filepath: Path to the state file.

        Returns:
            PipelineStateManager instance.
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        manager = cls()
        manager.job_id = data["job_id"]
        manager.connector_name = data["connector_name"]
        manager.connector_type = data["connector_type"]
        manager.state = PipelineState(data["state"])
        manager.test_retry_count = data["test_retry_count"]
        manager.review_cycle_count = data["review_cycle_count"]

        if data.get("started_at"):
            manager.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("updated_at"):
            manager.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at"):
            manager.completed_at = datetime.fromisoformat(data["completed_at"])

        manager.error_message = data.get("error_message")
        manager.pr_url = data.get("pr_url")
        manager.output_directory = data.get("output_directory")

        return manager
