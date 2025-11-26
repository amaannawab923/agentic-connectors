"""LangGraph pipeline definition v2 with conditional routing.

Native async implementation without Celery.
Supports persistent checkpointing via SQLite or PostgreSQL.

Pipeline Flow:
    Research -> Generator -> Tester -> TestReviewer --+-- VALID+PASS -> Reviewer --+-- APPROVE -> Publisher
                  ^           ^                       |                            |
                  |           |                       +-- INVALID -> Tester        +-- REJECT:CODE -> Generator
                  |           |                       |                            |
                  |           +-------------------+---+-- VALID+FAIL -> Generator  +-- REJECT:CONTEXT -> Research
                  |                                                                          |
                  +--------------------------------------------------------------------------+

Routing Decisions:
    1. TestReviewer:
       - INVALID -> Tester (fix tests) [max 3 retries]
       - VALID+FAIL -> Generator (fix code) [max 3 retries]
       - VALID+PASS -> Reviewer

    2. Reviewer (based on coverage_ratio):
       - 100% -> APPROVE -> Publisher
       - >=80% -> APPROVE (DEGRADED MODE) -> Publisher
       - 50-79% -> REJECT:CODE -> Generator [max 2 retries]
       - <50% -> REJECT:CONTEXT -> Research [max 1 retry]

Exit States:
    - END (success): Full pass, all streams working
    - END (partial): >=80% pass, DEGRADED MODE with warnings
    - FAILED: Max retries exceeded

Checkpointing:
    - memory: In-memory only (no persistence, for testing)
    - sqlite: SQLite database file (default, good for single-node)
    - postgres: PostgreSQL database (for production/multi-node)
"""

import logging
from typing import Literal, Optional, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import (
    PipelineState,
    PipelineStatus,
    ReviewDecision,
    TestReviewDecision,
    COVERAGE_FULL_PASS,
)
from .config import settings

# Real agents for research, generator, tester, and test_reviewer
from .nodes.real_agents import (
    research_node,
    generator_node,
    tester_node,
    test_reviewer_node,
)

# Mock agents for reviewer, publisher (to be integrated later)
from .nodes.mock_agents import (
    reviewer_node,
    publisher_node,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Checkpointer (Singleton with Async Support)
# ─────────────────────────────────────────────────────────────────────────────

_checkpointer: Optional[Any] = None
_checkpointer_context: Optional[Any] = None  # Holds the context manager
_checkpointer_initialized = False


async def get_checkpointer_async():
    """Get or create the checkpointer instance (async version).

    Supports:
        - memory: MemorySaver (in-memory, no persistence)
        - sqlite: AsyncSqliteSaver (file-based persistence)
        - postgres: AsyncPostgresSaver (database persistence)

    Returns:
        Checkpointer instance (singleton).
    """
    global _checkpointer, _checkpointer_context, _checkpointer_initialized

    if _checkpointer_initialized:
        return _checkpointer

    checkpointer_type = settings.checkpointer_type
    logger.info(f"Initializing checkpointer: {checkpointer_type}")

    if checkpointer_type == "memory":
        _checkpointer = MemorySaver()
        logger.info("Using MemorySaver (in-memory, no persistence)")

    elif checkpointer_type == "sqlite":
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        db_path = settings.sqlite_db_path
        logger.info(f"Using AsyncSqliteSaver with database: {db_path}")

        # from_conn_string returns an async context manager
        # We need to enter the context and keep the reference
        _checkpointer_context = AsyncSqliteSaver.from_conn_string(db_path)
        _checkpointer = await _checkpointer_context.__aenter__()
        await _checkpointer.setup()
        logger.info("SQLite checkpointer initialized and tables created")

    elif checkpointer_type == "postgres":
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        postgres_url = settings.postgres_url
        if not postgres_url:
            raise ValueError("ORCHESTRATOR_POSTGRES_URL is required for postgres checkpointer")

        logger.info("Using AsyncPostgresSaver with PostgreSQL")

        # from_conn_string returns an async context manager
        _checkpointer_context = AsyncPostgresSaver.from_conn_string(postgres_url)
        _checkpointer = await _checkpointer_context.__aenter__()
        await _checkpointer.setup()
        logger.info("PostgreSQL checkpointer initialized and tables created")

    else:
        raise ValueError(f"Unknown checkpointer type: {checkpointer_type}")

    _checkpointer_initialized = True
    return _checkpointer


def get_checkpointer_sync() -> MemorySaver:
    """Get a synchronous checkpointer (MemorySaver only).

    This is for cases where async is not available.
    For persistent checkpointing, use get_checkpointer_async().

    Returns:
        MemorySaver instance.
    """
    global _checkpointer

    if _checkpointer is None:
        logger.info("Creating MemorySaver checkpointer (sync fallback)")
        _checkpointer = MemorySaver()

    return _checkpointer


async def close_checkpointer():
    """Close the checkpointer connection (for cleanup).

    Should be called during application shutdown.
    """
    global _checkpointer, _checkpointer_context, _checkpointer_initialized

    if _checkpointer_context is not None:
        checkpointer_type = settings.checkpointer_type
        try:
            # Exit the async context manager properly
            await _checkpointer_context.__aexit__(None, None, None)
            logger.info(f"Closed {checkpointer_type} checkpointer connection")
        except Exception as e:
            logger.warning(f"Error closing checkpointer: {e}")

    _checkpointer = None
    _checkpointer_context = None
    _checkpointer_initialized = False
    logger.info("Checkpointer cleaned up")


# ─────────────────────────────────────────────────────────────────────────────
# Routing Functions
# ─────────────────────────────────────────────────────────────────────────────

def route_after_test_review(state: PipelineState) -> Literal["tester", "generator", "reviewer", "failed"]:
    """Route after TestReviewer based on test validity and code pass/fail.

    Routes:
        - INVALID tests -> tester (to fix tests) if test_retries < max
        - VALID+FAIL -> generator (to fix code) if gen_fix_retries < max
        - VALID+PASS -> reviewer
        - Max retries exceeded -> failed
    """
    # Check for fatal errors
    if state.get("errors"):
        logger.warning(f"Pipeline has fatal errors: {state['errors']}")
        return "failed"

    decision = state.get("test_review_decision")
    test_retries = state.get("test_retries", 0)
    gen_fix_retries = state.get("gen_fix_retries", 0)
    max_test_retries = state.get("max_test_retries", 3)
    max_gen_fix_retries = state.get("max_gen_fix_retries", 3)

    # INVALID tests -> back to Tester
    if decision == TestReviewDecision.INVALID.value:
        if test_retries >= max_test_retries:
            logger.warning(f"Max test retries ({max_test_retries}) exceeded -> FAILED")
            return "failed"
        logger.info(f"Tests INVALID (retry {test_retries}/{max_test_retries}) -> routing to tester")
        return "tester"

    # VALID+FAIL -> back to Generator to fix code
    if decision == TestReviewDecision.VALID_FAIL.value:
        if gen_fix_retries >= max_gen_fix_retries:
            logger.warning(f"Max gen_fix retries ({max_gen_fix_retries}) exceeded -> FAILED")
            return "failed"
        logger.info(f"Tests VALID but FAILED (retry {gen_fix_retries}/{max_gen_fix_retries}) -> routing to generator")
        return "generator"

    # VALID+PASS -> proceed to Reviewer
    if decision == TestReviewDecision.VALID_PASS.value:
        logger.info("Tests VALID and PASSED -> routing to reviewer")
        return "reviewer"

    # Unknown decision - shouldn't happen
    logger.error(f"Unknown test_review_decision: {decision}")
    return "failed"


def route_after_review(state: PipelineState) -> Literal["generator", "research", "publisher", "failed"]:
    """Route after Reviewer based on review decision and coverage.

    Coverage-based routing:
        - 100% -> APPROVE -> publisher
        - >=80% -> APPROVE (DEGRADED MODE) -> publisher
        - 50-79% -> REJECT:CODE -> generator (if retries available)
        - <50% -> REJECT:CONTEXT -> research (if retries available)
    """
    # Check for fatal errors
    if state.get("errors"):
        logger.warning(f"Pipeline has fatal errors: {state['errors']}")
        return "failed"

    decision = state.get("review_decision")
    coverage = state.get("coverage_ratio", 0.0)
    review_retries = state.get("review_retries", 0)
    research_retries = state.get("research_retries", 0)
    max_review_retries = state.get("max_review_retries", 2)
    max_research_retries = state.get("max_research_retries", 1)

    # APPROVE -> publisher (handles both full and partial success)
    if decision == ReviewDecision.APPROVE.value:
        if coverage >= COVERAGE_FULL_PASS:
            logger.info(f"Review APPROVED (100% coverage) -> routing to publisher")
        else:
            logger.info(f"Review APPROVED (DEGRADED MODE, {coverage*100:.0f}% coverage) -> routing to publisher")
        return "publisher"

    # REJECT:CODE -> back to Generator
    if decision == ReviewDecision.REJECT_CODE.value:
        if review_retries >= max_review_retries:
            logger.warning(f"Max review retries ({max_review_retries}) exceeded -> FAILED")
            return "failed"
        logger.info(f"Review REJECT:CODE (retry {review_retries}/{max_review_retries}) -> routing to generator")
        return "generator"

    # REJECT:CONTEXT -> back to Research
    # Note: research_retries is incremented BEFORE this check (in reset_for_re_research)
    # So we check > instead of >= to allow the first retry
    if decision == ReviewDecision.REJECT_CONTEXT.value:
        if research_retries > max_research_retries:
            logger.warning(f"Max research retries ({max_research_retries}) exceeded -> FAILED")
            return "failed"
        logger.info(f"Review REJECT:CONTEXT (retry {research_retries}/{max_research_retries}) -> routing to research")
        return "research"

    # Unknown decision
    logger.error(f"Unknown review_decision: {decision}")
    return "failed"


# ─────────────────────────────────────────────────────────────────────────────
# Failed Node (saves artifacts before ending)
# ─────────────────────────────────────────────────────────────────────────────

def failed_node(state: PipelineState) -> dict:
    """Handle pipeline failure - save logs and artifacts.

    This node is reached when max retries are exceeded.
    """
    from datetime import datetime

    logger.error(f"Pipeline FAILED for connector: {state.get('connector_name')}")
    logger.error(f"Final state - test_retries: {state.get('test_retries')}, "
                 f"gen_fix_retries: {state.get('gen_fix_retries')}, "
                 f"review_retries: {state.get('review_retries')}, "
                 f"research_retries: {state.get('research_retries')}")

    return {
        "current_phase": "failed",
        "status": PipelineStatus.FAILED.value,
        "completed_at": datetime.utcnow().isoformat(),
        "logs": [
            f"Pipeline failed at phase: {state.get('current_phase')}",
            f"Coverage ratio: {state.get('coverage_ratio', 0.0)*100:.1f}%",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    """Build the LangGraph pipeline v2 for connector generation.

    Pipeline Flow:
        Research -> Generator -> Tester -> TestReviewer --+-- VALID+PASS -> Reviewer -> Publisher
                      ^           ^                       |
                      |           |                       +-- INVALID -> Tester
                      |           |                       |
                      |           +-------------------+---+-- VALID+FAIL -> Generator
                      |
                      +---------------------------------------- REJECT:CODE from Reviewer
              ^
              +-------------------------------------------- REJECT:CONTEXT from Reviewer

    Returns:
        Compiled StateGraph ready for execution.
    """
    logger.info("Building LangGraph pipeline v2...")

    # Create the state graph
    workflow = StateGraph(PipelineState)

    # ─────────────────────────────────────────────────────────────
    # Add Nodes
    # ─────────────────────────────────────────────────────────────
    workflow.add_node("research", research_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("test_reviewer", test_reviewer_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("failed", failed_node)

    # ─────────────────────────────────────────────────────────────
    # Set Entry Point
    # ─────────────────────────────────────────────────────────────
    workflow.set_entry_point("research")

    # ─────────────────────────────────────────────────────────────
    # Add Sequential Edges (happy path)
    # ─────────────────────────────────────────────────────────────
    workflow.add_edge("research", "generator")
    workflow.add_edge("generator", "tester")
    workflow.add_edge("tester", "test_reviewer")

    # ─────────────────────────────────────────────────────────────
    # Add Conditional Edges (TestReviewer decisions)
    # ─────────────────────────────────────────────────────────────
    workflow.add_conditional_edges(
        "test_reviewer",
        route_after_test_review,
        {
            "tester": "tester",           # INVALID -> fix tests
            "generator": "generator",     # VALID+FAIL -> fix code
            "reviewer": "reviewer",       # VALID+PASS -> proceed
            "failed": "failed",           # Max retries exceeded
        }
    )

    # ─────────────────────────────────────────────────────────────
    # Add Conditional Edges (Reviewer decisions)
    # ─────────────────────────────────────────────────────────────
    workflow.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "generator": "generator",     # REJECT:CODE -> fix code quality
            "research": "research",       # REJECT:CONTEXT -> re-research
            "publisher": "publisher",     # APPROVE -> publish
            "failed": "failed",           # Max retries exceeded
        }
    )

    # ─────────────────────────────────────────────────────────────
    # Terminal Edges
    # ─────────────────────────────────────────────────────────────
    workflow.add_edge("publisher", END)
    workflow.add_edge("failed", END)

    logger.info("Pipeline v2 built successfully")
    return workflow


async def create_pipeline_app_async(checkpointer=None):
    """Create compiled pipeline application with async checkpointing.

    This is the preferred method for production use with SQLite or PostgreSQL.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                     If None, uses the configured checkpointer type.

    Returns:
        Compiled pipeline application.
    """
    workflow = build_pipeline()

    if checkpointer is None:
        checkpointer = await get_checkpointer_async()

    logger.info(f"Creating pipeline with checkpointer: {type(checkpointer).__name__}")
    return workflow.compile(checkpointer=checkpointer)


def create_pipeline_app(checkpointer=None):
    """Create compiled pipeline application with checkpointing (sync version).

    Note: This uses MemorySaver only. For persistent checkpointing,
    use create_pipeline_app_async() instead.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                     If None, uses MemorySaver.

    Returns:
        Compiled pipeline application.
    """
    workflow = build_pipeline()

    if checkpointer is None:
        checkpointer = get_checkpointer_sync()

    logger.info(f"Creating pipeline with checkpointer: {type(checkpointer).__name__}")
    return workflow.compile(checkpointer=checkpointer)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Visualization
# ─────────────────────────────────────────────────────────────────────────────

def get_pipeline_diagram() -> str:
    """Get Mermaid diagram of the pipeline.

    Returns:
        Mermaid diagram string.
    """
    workflow = build_pipeline()
    app = workflow.compile()
    return app.get_graph().draw_mermaid()


def print_pipeline_diagram():
    """Print the pipeline diagram to console."""
    print("\n" + "=" * 60)
    print("CONNECTOR GENERATION PIPELINE v2")
    print("=" * 60)
    print(get_pipeline_diagram())
    print("=" * 60 + "\n")
