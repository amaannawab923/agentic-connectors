"""Enumeration types for the Connector Generator."""

from enum import Enum


class PipelineState(str, Enum):
    """States of the connector generation pipeline."""

    PENDING = "pending"
    RESEARCHING = "researching"
    GENERATING = "generating"
    TESTING = "testing"
    FIXING = "fixing"
    REVIEWING = "reviewing"
    IMPROVING = "improving"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXCEEDED = "budget_exceeded"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Types of agents in the pipeline."""

    RESEARCH = "research"
    GENERATOR = "generator"
    MOCK_GENERATOR = "mock_generator"
    TESTER = "tester"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"


class ConnectorType(str, Enum):
    """Supported connector types."""

    SOURCE = "source"
    DESTINATION = "destination"


class TestStatus(str, Enum):
    """Test execution status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ReviewDecision(str, Enum):
    """Review decision outcomes."""

    APPROVED = "approved"
    NEEDS_WORK = "needs_work"
    REJECTED = "rejected"
