"""Pipeline state definition for LangGraph v2.

Implements the v2 architecture with:
- Explicit retry counters for each loop
- Coverage ratio thresholds
- DEGRADED MODE for partial success
- REJECT:CODE vs REJECT:CONTEXT paths
- Proper reducers for list fields (LangGraph best practice)
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from enum import Enum
from operator import add


class PipelinePhase(str, Enum):
    """Current phase of the pipeline."""
    PENDING = "pending"
    RESEARCHING = "researching"
    GENERATING = "generating"
    TESTING = "testing"
    TEST_REVIEWING = "test_reviewing"
    REVIEWING = "reviewing"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    """Final status of the pipeline."""
    RUNNING = "running"
    SUCCESS = "success"       # 100% tests pass
    PARTIAL = "partial"       # >=80% tests pass (DEGRADED MODE)
    FAILED = "failed"         # Max retries exceeded or <80% pass


class ReviewDecision(str, Enum):
    """Reviewer decision types."""
    APPROVE = "approve"
    REJECT_CODE = "reject_code"        # Code bugs -> Generator
    REJECT_CONTEXT = "reject_context"  # Missing API context -> Research


class TestReviewDecision(str, Enum):
    """TestReviewer decision types."""
    VALID_PASS = "valid_pass"    # Tests valid, code passes -> Reviewer
    VALID_FAIL = "valid_fail"    # Tests valid, code fails -> Generator
    INVALID = "invalid"          # Tests invalid -> Tester


# ─────────────────────────────────────────────────────────────────────────────
# Retry Limits (configurable defaults)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_MAX_TEST_RETRIES = 3       # TestReviewer -> Tester (invalid tests)
DEFAULT_MAX_GEN_FIX_RETRIES = 3    # TestReviewer -> Generator (code fails)
DEFAULT_MAX_REVIEW_RETRIES = 2     # Reviewer -> Generator (REJECT:CODE)
DEFAULT_MAX_RESEARCH_RETRIES = 1   # Reviewer -> Research (REJECT:CONTEXT)

# Coverage thresholds
COVERAGE_FULL_PASS = 1.0           # 100% -> APPROVE
COVERAGE_PARTIAL_MIN = 0.80        # >=80% -> DEGRADED MODE
COVERAGE_REJECT_CODE_MIN = 0.50    # 50-79% -> REJECT:CODE
# <50% -> REJECT:CONTEXT

# Log trimming (keep state size manageable)
MAX_LOGS_IN_STATE = 100


# ─────────────────────────────────────────────────────────────────────────────
# Custom Reducers
# ─────────────────────────────────────────────────────────────────────────────

def reduce_logs(existing: List[str], new: List[str]) -> List[str]:
    """Reducer for logs - appends and trims to max size.

    This prevents unbounded log growth in state.
    """
    combined = (existing or []) + (new or [])
    return combined[-MAX_LOGS_IN_STATE:]  # Keep last N logs


def reduce_list_append(existing: List[str], new: List[str]) -> List[str]:
    """Reducer for generic lists - always appends."""
    return (existing or []) + (new or [])


def reduce_list_replace(existing: List[str], new: List[str]) -> List[str]:
    """Reducer for feedback lists - replaces if new is non-empty, else keeps existing."""
    if new:
        return new
    return existing or []


class PipelineState(TypedDict):
    """Shared state across all pipeline nodes.

    This state is passed between nodes and persisted via checkpointing.
    Follows v2 architecture with explicit retry counters and coverage tracking.

    LangGraph Best Practices:
    - List fields use Annotated with reducers for proper merging
    - State is minimal - only essential data
    - Typed with TypedDict for clarity
    """

    # ─────────────────────────────────────────────────────────────
    # Immutable Request Information (set once)
    # ─────────────────────────────────────────────────────────────
    connector_name: str
    connector_type: str  # "source" or "destination"
    original_request: str  # Original user request (preserved on re-research)
    api_doc_url: Optional[str]
    created_at: str

    # ─────────────────────────────────────────────────────────────
    # Pipeline Control
    # ─────────────────────────────────────────────────────────────
    current_phase: str
    status: str  # PipelineStatus value

    # ─────────────────────────────────────────────────────────────
    # Retry Counters (v2 - explicit per-loop counters)
    # ─────────────────────────────────────────────────────────────
    test_retries: int           # TestReviewer -> Tester (invalid tests)
    gen_fix_retries: int        # TestReviewer -> Generator (code fails)
    review_retries: int         # Reviewer -> Generator (REJECT:CODE)
    research_retries: int       # Reviewer -> Research (REJECT:CONTEXT)

    # Retry limits (configurable)
    max_test_retries: int
    max_gen_fix_retries: int
    max_review_retries: int
    max_research_retries: int

    # ─────────────────────────────────────────────────────────────
    # Research Output
    # ─────────────────────────────────────────────────────────────
    research_output: Optional[Dict[str, Any]]  # {api_docs, auth_spec, endpoints, schemas}

    # Context gaps - uses reducer to accumulate across REJECT:CONTEXT cycles
    context_gaps: Annotated[List[str], reduce_list_append]

    # ─────────────────────────────────────────────────────────────
    # Generated Artifacts (cleared on REJECT:CONTEXT -> Research)
    # ─────────────────────────────────────────────────────────────
    generated_code: Optional[Dict[str, Any]]  # {files: Map<path, content>, checksum}
    test_code: Optional[Dict[str, Any]]       # {files: Map<path, content>, mock_server}
    connector_dir: Optional[str]

    # ─────────────────────────────────────────────────────────────
    # Test Results
    # ─────────────────────────────────────────────────────────────
    test_results: Optional[Dict[str, Any]]  # {passed, failed, total, coverage_ratio, failures}
    coverage_ratio: float  # passed / total (0.0 - 1.0)

    # ─────────────────────────────────────────────────────────────
    # Test Review Results (replaced each cycle)
    # ─────────────────────────────────────────────────────────────
    test_review_decision: Optional[str]  # TestReviewDecision value
    test_review_feedback: Annotated[List[str], reduce_list_replace]

    # ─────────────────────────────────────────────────────────────
    # Code Review Results (replaced each cycle)
    # ─────────────────────────────────────────────────────────────
    review_decision: Optional[str]  # ReviewDecision value
    review_feedback: Annotated[List[str], reduce_list_replace]

    # ─────────────────────────────────────────────────────────────
    # Publish Results
    # ─────────────────────────────────────────────────────────────
    published: bool
    pr_url: Optional[str]
    degraded_mode: bool  # True if partial success
    degraded_streams: Annotated[List[str], reduce_list_replace]

    # ─────────────────────────────────────────────────────────────
    # Execution Metadata
    # ─────────────────────────────────────────────────────────────
    # Errors accumulate, logs are trimmed
    errors: Annotated[List[str], reduce_list_append]
    logs: Annotated[List[str], reduce_logs]
    completed_at: Optional[str]
    total_duration: float


def create_initial_state(
    connector_name: str,
    connector_type: str = "source",
    api_doc_url: Optional[str] = None,
    original_request: Optional[str] = None,
    max_test_retries: int = DEFAULT_MAX_TEST_RETRIES,
    max_gen_fix_retries: int = DEFAULT_MAX_GEN_FIX_RETRIES,
    max_review_retries: int = DEFAULT_MAX_REVIEW_RETRIES,
    max_research_retries: int = DEFAULT_MAX_RESEARCH_RETRIES,
) -> PipelineState:
    """Create initial pipeline state.

    Args:
        connector_name: Name of the connector to generate.
        connector_type: Type of connector ("source" or "destination").
        api_doc_url: Optional URL to API documentation.
        original_request: Original user request text.
        max_test_retries: Max TestReviewer -> Tester retries (default 3).
        max_gen_fix_retries: Max TestReviewer -> Generator retries (default 3).
        max_review_retries: Max Reviewer -> Generator retries (default 2).
        max_research_retries: Max Reviewer -> Research retries (default 1).

    Returns:
        Initial PipelineState dictionary.
    """
    from datetime import datetime

    return PipelineState(
        # Immutable request info
        connector_name=connector_name,
        connector_type=connector_type,
        original_request=original_request or f"Generate {connector_type} connector for {connector_name}",
        api_doc_url=api_doc_url,
        created_at=datetime.utcnow().isoformat(),

        # Pipeline control
        current_phase=PipelinePhase.PENDING.value,
        status=PipelineStatus.RUNNING.value,

        # Retry counters (all start at 0)
        test_retries=0,
        gen_fix_retries=0,
        review_retries=0,
        research_retries=0,

        # Retry limits
        max_test_retries=max_test_retries,
        max_gen_fix_retries=max_gen_fix_retries,
        max_review_retries=max_review_retries,
        max_research_retries=max_research_retries,

        # Research output
        research_output=None,
        context_gaps=[],

        # Generated artifacts
        generated_code=None,
        test_code=None,
        connector_dir=None,

        # Test results
        test_results=None,
        coverage_ratio=0.0,

        # Test review results
        test_review_decision=None,
        test_review_feedback=[],

        # Code review results
        review_decision=None,
        review_feedback=[],

        # Publish results
        published=False,
        pr_url=None,
        degraded_mode=False,
        degraded_streams=[],

        # Metadata
        errors=[],
        logs=[],
        completed_at=None,
        total_duration=0.0,
    )


def reset_for_re_research(state: PipelineState, context_gap: str) -> dict:
    """Return state updates when REJECT:CONTEXT triggers re-research.

    Clears generated artifacts but preserves research context.
    Note: context_gaps uses a reducer, so we just provide the new gap.

    IMPORTANT: Does NOT reset review_decision because routing happens
    AFTER this update is applied, and the router needs to see the
    REJECT_CONTEXT decision to know where to route.

    Args:
        state: Current pipeline state.
        context_gap: What the Reviewer identified as missing.

    Returns:
        Dictionary of state updates to apply.
    """
    return {
        # Clear stale artifacts
        "generated_code": None,
        "test_code": None,
        "test_results": None,
        "coverage_ratio": 0.0,

        # Reset test review decision (but NOT review_decision - needed for routing)
        "test_review_decision": None,
        "test_review_feedback": [],
        # Note: review_decision is preserved for routing, cleared in research node
        "review_feedback": [],

        # Append context gap (reducer handles accumulation)
        "context_gaps": [context_gap],

        # Increment research retry counter
        "research_retries": state.get("research_retries", 0) + 1,

        # Update phase
        "current_phase": PipelinePhase.RESEARCHING.value,
    }
