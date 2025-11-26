"""Mock agent nodes v2 for testing the orchestrator.

These nodes simulate real agents with configurable delays.
Replace these with real agent calls in production.

IMPORTANT: Log Handling with Reducers
─────────────────────────────────────
State uses Annotated[List[str], reduce_logs] for log fields.
Reducers automatically merge old + new values, so nodes should
ONLY return NEW log entries, not the full accumulated list.

Example:
    # WRONG - would double-count logs
    logs = state.get("logs", []) + [new_entry]
    return {"logs": logs}

    # CORRECT - reducer handles merging
    new_logs = [new_entry]
    return {"logs": new_logs}

Test Mode (ORCHESTRATOR_TEST_MODE=true):
    Demonstrates ALL v2 pipeline routing paths:

    Phase 1: Initial Research → First Review
    ─────────────────────────────────────────
    1. Research → Generator → Tester (0 tests) → TestReviewer (INVALID) → Tester
    2. Tester → TestReviewer (VALID+FAIL) → Generator
    3. Generator → Tester → TestReviewer (VALID+FAIL) → Generator
    4. Generator → Tester → TestReviewer (VALID+PASS) → Reviewer
    5. Reviewer (REJECT:CONTEXT) → Research  ← NEW PATH!

    Phase 2: Re-Research → Final Approval
    ─────────────────────────────────────────
    6. Research (re-research with context_gaps) → Generator → Tester → TestReviewer
    7. TestReviewer (VALID+PASS) → Reviewer
    8. Reviewer (REJECT:CODE) → Generator
    9. Generator → Tester → TestReviewer → Reviewer (APPROVE) → Publisher

    All Counters Tested:
    - test_retries: increments when INVALID (max 3)
    - gen_fix_retries: increments when VALID+FAIL (max 3)
    - review_retries: increments when REJECT:CODE (max 2)
    - research_retries: increments when REJECT:CONTEXT (max 1)  ← NEW!
"""

import asyncio
import os
import random
import logging
from datetime import datetime
from typing import Dict, Any, List

from ..state import (
    PipelineState,
    PipelinePhase,
    PipelineStatus,
    TestReviewDecision,
    ReviewDecision,
    COVERAGE_FULL_PASS,
    COVERAGE_PARTIAL_MIN,
    COVERAGE_REJECT_CODE_MIN,
    reset_for_re_research,
)
from ..config import settings

logger = logging.getLogger(__name__)

# Test mode flag - when True, uses deterministic behavior
TEST_MODE = os.getenv("ORCHESTRATOR_TEST_MODE", "").lower() in ("true", "1", "yes")
TEST_DELAY = 1  # 1 second delay in test mode


def _log(message: str) -> str:
    """Create a timestamped log entry.

    NOTE: This returns a SINGLE log entry string.
    Nodes should collect new entries in a list and return only NEW logs.
    The reducer will handle merging with existing logs.
    """
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    logger.info(log_entry)
    return log_entry


# ─────────────────────────────────────────────────────────────────────────────
# Research Node
# ─────────────────────────────────────────────────────────────────────────────

async def research_node(state: PipelineState) -> Dict[str, Any]:
    """Mock research agent - simulates API documentation research.

    In production, this would call ResearchAgent.execute().

    Handles both initial research and re-research (when REJECT:CONTEXT).
    When re-researching, uses context_gaps to focus research.
    """
    connector_name = state["connector_name"]
    research_retries = state.get("research_retries", 0)
    context_gaps = state.get("context_gaps", [])
    duration = TEST_DELAY if TEST_MODE else settings.mock_research_duration

    is_re_research = research_retries > 0 or len(context_gaps) > 0

    # Collect NEW logs only (reducer will merge with existing)
    new_logs: List[str] = []

    if is_re_research:
        new_logs.append(_log(f"[RESEARCH] Re-researching {connector_name} (retry {research_retries})..."))
        new_logs.append(f"[RESEARCH] Context gaps to address: {context_gaps}")
    else:
        new_logs.append(_log(f"[RESEARCH] Starting research for {connector_name}..."))

    if TEST_MODE:
        new_logs.append(f"[RESEARCH] TEST MODE - quick delay: {duration}s")

    await asyncio.sleep(duration)

    # Mock research output
    research_output = {
        "api_docs": f"https://api.example.com/docs/{connector_name}",
        "auth_spec": {
            "type": "oauth2",
            "token_url": "https://api.example.com/oauth/token",
        },
        "endpoints": [
            {"path": "/resources", "method": "GET", "description": "List resources"},
            {"path": "/resources/{id}", "method": "GET", "description": "Get resource"},
        ],
        "schemas": [
            {"name": "Resource", "fields": ["id", "name", "created_at"]},
        ],
        "context_gaps_addressed": context_gaps,
        "researched_at": datetime.utcnow().isoformat(),
    }

    new_logs.append(_log(f"[RESEARCH] Completed! Found {len(research_output['endpoints'])} endpoints"))

    result = {
        "research_output": research_output,
        "current_phase": PipelinePhase.RESEARCHING.value,
        "logs": new_logs,  # Only NEW logs - reducer merges
    }

    # Clear review_decision when starting fresh research (was preserved for routing)
    if is_re_research:
        result["review_decision"] = None

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Generator Node
# ─────────────────────────────────────────────────────────────────────────────

async def generator_node(state: PipelineState) -> Dict[str, Any]:
    """Mock generator agent - handles code generation and fixes.

    Triggered by:
    - Initial generation (no prior code)
    - TestReviewer VALID+FAIL (gen_fix_retries incremented)
    - Reviewer REJECT:CODE (review_retries incremented)

    In production, this would call GeneratorAgent.execute().
    """
    connector_name = state["connector_name"]
    duration = TEST_DELAY if TEST_MODE else settings.mock_generator_duration

    gen_fix_retries = state.get("gen_fix_retries", 0)
    review_retries = state.get("review_retries", 0)
    test_review_feedback = state.get("test_review_feedback", [])
    review_feedback = state.get("review_feedback", [])

    # Determine action based on what triggered this node
    if test_review_feedback:
        action = "Fixing code"
        reason = f"test failures: {test_review_feedback[:2]}"
    elif review_feedback:
        action = "Improving code"
        reason = f"review feedback: {review_feedback[:2]}"
    else:
        action = "Generating code"
        reason = "initial generation"

    # Collect NEW logs only
    new_logs: List[str] = []
    new_logs.append(_log(f"[GENERATOR] {action} for {connector_name}..."))
    new_logs.append(f"[GENERATOR] Reason: {reason}")
    new_logs.append(f"[GENERATOR] gen_fix_retries={gen_fix_retries}, review_retries={review_retries}")

    if TEST_MODE:
        new_logs.append(f"[GENERATOR] TEST MODE - quick delay: {duration}s")

    await asyncio.sleep(duration)

    # Mock generated code
    timestamp = datetime.utcnow().isoformat()

    generated_code = {
        "files": {
            f"src/{connector_name}/connector.py": f"# Connector code generated at {timestamp}",
            f"src/{connector_name}/client.py": f"# API client generated at {timestamp}",
            f"src/{connector_name}/streams.py": f"# Streams generated at {timestamp}",
        },
        "checksum": f"mock-checksum-{timestamp}",
        "action": action,
        "reason": reason,
    }

    connector_dir = f"output/source-{connector_name}"
    new_logs.append(_log(f"[GENERATOR] Code generated successfully ({len(generated_code['files'])} files)"))

    return {
        "generated_code": generated_code,
        "connector_dir": connector_dir,
        "current_phase": PipelinePhase.GENERATING.value,
        # Clear feedback after processing (use empty list for reducer)
        "test_review_feedback": [],
        "review_feedback": [],
        "logs": new_logs,  # Only NEW logs
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tester Node
# ─────────────────────────────────────────────────────────────────────────────

async def tester_node(state: PipelineState) -> Dict[str, Any]:
    """Mock tester agent - runs tests and generates test code.

    Triggered by:
    - Initial test run (after Generator)
    - TestReviewer INVALID (test_retries incremented, fix tests)

    In production, this would call TesterAgent.execute().

    TEST_MODE behavior:
    - test_retries=0: Create tests that will be marked INVALID
    - test_retries=1: Create valid tests but code FAILS
    - test_retries=2: Tests pass, code passes
    """
    connector_name = state["connector_name"]
    duration = TEST_DELAY if TEST_MODE else settings.mock_tester_duration

    test_retries = state.get("test_retries", 0)
    gen_fix_retries = state.get("gen_fix_retries", 0)
    test_review_feedback = state.get("test_review_feedback", [])

    is_fixing_tests = len(test_review_feedback) > 0

    # Collect NEW logs only
    new_logs: List[str] = []

    if is_fixing_tests:
        new_logs.append(_log(f"[TESTER] Fixing tests (test_retries={test_retries})..."))
        new_logs.append(f"[TESTER] Feedback to address: {test_review_feedback[:2]}")
    else:
        new_logs.append(_log(f"[TESTER] Running tests (gen_fix_retries={gen_fix_retries})..."))

    if TEST_MODE:
        new_logs.append(f"[TESTER] TEST MODE - deterministic behavior")

    await asyncio.sleep(duration)

    # Determine test results based on TEST_MODE state
    if TEST_MODE:
        # Progression:
        # - First tester run (test_retries=0, gen_fix=0): 0 tests (will be INVALID)
        # - After fixing tests (test_retries=1, gen_fix=0): 25 tests, 5 fail (VALID+FAIL)
        # - After fixing code (test_retries=1, gen_fix=1): 25 tests, 3 fail (VALID+FAIL)
        # - After fixing code again (test_retries=1, gen_fix=2): 25 tests, all pass (VALID+PASS)

        total_gen_fix = gen_fix_retries

        if test_retries == 0:
            # First run: Create invalid tests (0 tests run)
            tests_run = 0
            tests_passed = 0
            tests_failed = 0
            new_logs.append(f"[TESTER] TEST MODE - Created tests with 0 test cases (will be INVALID)")
        elif total_gen_fix < 2:
            # Valid tests but code fails
            tests_run = 25
            tests_failed = 5 - total_gen_fix  # 5, then 4, then 3...
            tests_passed = tests_run - tests_failed
            new_logs.append(f"[TESTER] TEST MODE - {tests_passed}/{tests_run} passed (gen_fix={total_gen_fix})")
        else:
            # All tests pass
            tests_run = 25
            tests_passed = 25
            tests_failed = 0
            new_logs.append(f"[TESTER] TEST MODE - All tests PASSED!")
    else:
        # Random behavior
        tests_run = random.randint(15, 30)
        pass_rate = min(0.5 + (test_retries * 0.15) + (gen_fix_retries * 0.15), 1.0)
        tests_passed = int(tests_run * pass_rate)
        tests_failed = tests_run - tests_passed

    # Calculate coverage ratio
    coverage_ratio = tests_passed / tests_run if tests_run > 0 else 0.0

    test_code = {
        "files": {
            f"tests/test_{connector_name}.py": f"# Test code - {tests_run} test cases",
            "tests/conftest.py": "# Pytest fixtures",
        },
        "mock_server": "mock://api.example.com",
    }

    test_results = {
        "passed": tests_passed,
        "failed": tests_failed,
        "total": tests_run,
        "coverage_ratio": coverage_ratio,
        "failures": [f"test_case_{i}" for i in range(tests_failed)],
    }

    new_logs.append(_log(f"[TESTER] Results: {tests_passed}/{tests_run} passed ({coverage_ratio*100:.0f}%)"))

    return {
        "test_code": test_code,
        "test_results": test_results,
        "coverage_ratio": coverage_ratio,
        "current_phase": PipelinePhase.TESTING.value,
        "logs": new_logs,  # Only NEW logs
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Reviewer Node
# ─────────────────────────────────────────────────────────────────────────────

async def test_reviewer_node(state: PipelineState) -> Dict[str, Any]:
    """Mock test reviewer - validates test quality and determines routing.

    Decisions:
    - INVALID: Tests are insufficient (0 tests, trivial tests) → Tester
    - VALID+FAIL: Tests are good but code fails → Generator
    - VALID+PASS: Tests pass → Reviewer

    TEST_MODE behavior:
    - test_retries=0: INVALID (tests have 0 cases)
    - test_retries>=1, gen_fix<2: VALID+FAIL
    - test_retries>=1, gen_fix>=2: VALID+PASS
    """
    duration = TEST_DELAY if TEST_MODE else settings.mock_reviewer_duration

    test_retries = state.get("test_retries", 0)
    gen_fix_retries = state.get("gen_fix_retries", 0)
    test_results = state.get("test_results", {})
    coverage_ratio = state.get("coverage_ratio", 0.0)

    # Collect NEW logs only
    new_logs: List[str] = []
    new_logs.append(_log(f"[TEST_REVIEWER] Reviewing test quality..."))
    new_logs.append(f"[TEST_REVIEWER] test_retries={test_retries}, gen_fix_retries={gen_fix_retries}")

    await asyncio.sleep(duration)

    tests_total = test_results.get("total", 0)
    tests_passed = test_results.get("passed", 0)

    # Determine decision
    if TEST_MODE:
        if test_retries == 0:
            # First time: tests are invalid
            decision = TestReviewDecision.INVALID.value
            feedback = ["No test cases found", "Add at least 5 meaningful tests"]
            new_logs.append(f"[TEST_REVIEWER] TEST MODE - INVALID (0 tests)")
        elif gen_fix_retries < 2:
            # Tests valid but code fails
            decision = TestReviewDecision.VALID_FAIL.value
            feedback = [f"{tests_total - tests_passed} tests failing", "Code needs fixes"]
            new_logs.append(f"[TEST_REVIEWER] TEST MODE - VALID+FAIL (gen_fix={gen_fix_retries})")
        else:
            # All good
            decision = TestReviewDecision.VALID_PASS.value
            feedback = []
            new_logs.append(f"[TEST_REVIEWER] TEST MODE - VALID+PASS")
    else:
        # Real logic
        if tests_total < 5:
            decision = TestReviewDecision.INVALID.value
            feedback = [f"Only {tests_total} tests (minimum 5)", "Add more test coverage"]
        elif coverage_ratio >= COVERAGE_FULL_PASS:
            decision = TestReviewDecision.VALID_PASS.value
            feedback = []
        else:
            decision = TestReviewDecision.VALID_FAIL.value
            feedback = [f"Coverage {coverage_ratio*100:.0f}% < 100%", "Fix failing tests"]

    # Build updates
    updates: Dict[str, Any] = {
        "test_review_decision": decision,
        "test_review_feedback": feedback,  # Replaces via reduce_list_replace
        "current_phase": PipelinePhase.TEST_REVIEWING.value,
    }

    if decision == TestReviewDecision.INVALID.value:
        updates["test_retries"] = test_retries + 1
        new_logs.append(_log(f"[TEST_REVIEWER] → Routing to TESTER (test_retries now {test_retries + 1})"))
    elif decision == TestReviewDecision.VALID_FAIL.value:
        updates["gen_fix_retries"] = gen_fix_retries + 1
        new_logs.append(_log(f"[TEST_REVIEWER] → Routing to GENERATOR (gen_fix_retries now {gen_fix_retries + 1})"))
    else:
        new_logs.append(_log(f"[TEST_REVIEWER] → Routing to REVIEWER"))

    updates["logs"] = new_logs  # Only NEW logs
    return updates


# ─────────────────────────────────────────────────────────────────────────────
# Reviewer Node
# ─────────────────────────────────────────────────────────────────────────────

async def reviewer_node(state: PipelineState) -> Dict[str, Any]:
    """Mock reviewer - reviews code quality and determines routing.

    Coverage-based decisions:
    - 100%: APPROVE → Publisher
    - >=80%: APPROVE (DEGRADED MODE) → Publisher
    - 50-79%: REJECT:CODE → Generator
    - <50%: REJECT:CONTEXT → Research

    TEST_MODE behavior (demonstrates ALL paths):
    - research_retries=0, review_retries=0: REJECT:CONTEXT (fundamental issue)
    - research_retries>=1, review_retries=0: REJECT:CODE (code quality issue)
    - research_retries>=1, review_retries>=1: APPROVE
    """
    connector_name = state["connector_name"]
    duration = TEST_DELAY if TEST_MODE else settings.mock_reviewer_duration

    review_retries = state.get("review_retries", 0)
    research_retries = state.get("research_retries", 0)
    coverage_ratio = state.get("coverage_ratio", 0.0)

    # Collect NEW logs only
    new_logs: List[str] = []
    new_logs.append(_log(f"[REVIEWER] Reviewing code quality..."))
    new_logs.append(f"[REVIEWER] review_retries={review_retries}, research_retries={research_retries}, coverage={coverage_ratio*100:.0f}%")

    await asyncio.sleep(duration)

    # Determine decision
    if TEST_MODE:
        if research_retries == 0:
            # First time reaching reviewer: REJECT:CONTEXT (simulate fundamental API issue)
            decision = ReviewDecision.REJECT_CONTEXT.value
            feedback = ["Missing pagination endpoint", "Auth flow unclear", "Need more API context"]
            degraded_mode = False
            degraded_streams: List[str] = []
            new_logs.append(f"[REVIEWER] TEST MODE - REJECT:CONTEXT (need more research)")
        elif review_retries == 0:
            # After re-research, first review: REJECT:CODE
            decision = ReviewDecision.REJECT_CODE.value
            feedback = ["Add better error handling", "Improve logging", "Add retry logic"]
            degraded_mode = False
            degraded_streams = []
            new_logs.append(f"[REVIEWER] TEST MODE - REJECT:CODE (code quality issue)")
        else:
            # After re-research + code improvement: APPROVE
            decision = ReviewDecision.APPROVE.value
            feedback = []
            degraded_mode = coverage_ratio < COVERAGE_FULL_PASS
            degraded_streams = ["stream_3", "stream_4"] if degraded_mode else []
            new_logs.append(f"[REVIEWER] TEST MODE - APPROVE")
    else:
        # Real logic based on coverage
        if coverage_ratio >= COVERAGE_FULL_PASS:
            decision = ReviewDecision.APPROVE.value
            feedback = []
            degraded_mode = False
            degraded_streams = []
        elif coverage_ratio >= COVERAGE_PARTIAL_MIN:
            decision = ReviewDecision.APPROVE.value
            feedback = []
            degraded_mode = True
            degraded_streams = [f"stream_{i}" for i in range(int((1 - coverage_ratio) * 10))]
        elif coverage_ratio >= COVERAGE_REJECT_CODE_MIN:
            decision = ReviewDecision.REJECT_CODE.value
            feedback = ["Improve test coverage", "Fix failing streams"]
            degraded_mode = False
            degraded_streams = []
        else:
            decision = ReviewDecision.REJECT_CONTEXT.value
            feedback = ["Fundamental API issues", "Need more research on endpoints"]
            degraded_mode = False
            degraded_streams = []

    # Build updates
    updates: Dict[str, Any] = {
        "review_decision": decision,
        "review_feedback": feedback,  # Replaces via reduce_list_replace
        "degraded_mode": degraded_mode,
        "degraded_streams": degraded_streams,  # Replaces via reduce_list_replace
        "current_phase": PipelinePhase.REVIEWING.value,
    }

    if decision == ReviewDecision.REJECT_CODE.value:
        updates["review_retries"] = review_retries + 1
        new_logs.append(_log(f"[REVIEWER] → Routing to GENERATOR (review_retries now {review_retries + 1})"))
    elif decision == ReviewDecision.REJECT_CONTEXT.value:
        # Apply reset for re-research
        context_gap = "Need more API context based on test failures"
        reset_updates = reset_for_re_research(state, context_gap)
        updates.update(reset_updates)
        new_logs.append(_log(f"[REVIEWER] → Routing to RESEARCH (research_retries now {reset_updates['research_retries']})"))
    else:
        if degraded_mode:
            new_logs.append(_log(f"[REVIEWER] → DEGRADED MODE - Routing to PUBLISHER"))
            new_logs.append(f"[REVIEWER] Disabled streams: {degraded_streams}")
        else:
            new_logs.append(_log(f"[REVIEWER] → Routing to PUBLISHER"))

    updates["logs"] = new_logs  # Only NEW logs
    return updates


# ─────────────────────────────────────────────────────────────────────────────
# Publisher Node
# ─────────────────────────────────────────────────────────────────────────────

async def publisher_node(state: PipelineState) -> Dict[str, Any]:
    """Mock publisher - publishes connector to git.

    Handles both full success and DEGRADED MODE publishing.

    In production, this would call PublisherAgent.execute().
    """
    connector_name = state["connector_name"]
    duration = TEST_DELAY if TEST_MODE else settings.mock_publisher_duration

    degraded_mode = state.get("degraded_mode", False)
    degraded_streams = state.get("degraded_streams", [])
    coverage_ratio = state.get("coverage_ratio", 0.0)

    # Collect NEW logs only
    new_logs: List[str] = []

    if degraded_mode:
        new_logs.append(_log(f"[PUBLISHER] Publishing {connector_name} in DEGRADED MODE..."))
        new_logs.append(f"[PUBLISHER] Disabled streams: {degraded_streams}")
        new_logs.append(f"[PUBLISHER] Coverage: {coverage_ratio*100:.0f}%")
    else:
        new_logs.append(_log(f"[PUBLISHER] Publishing {connector_name}..."))

    if TEST_MODE:
        new_logs.append(f"[PUBLISHER] TEST MODE - quick delay: {duration}s")

    await asyncio.sleep(duration)

    # Mock PR URL
    pr_number = random.randint(100, 999)
    pr_url = f"https://github.com/org/connectors/pull/{pr_number}"

    # Determine final status
    if degraded_mode:
        status = PipelineStatus.PARTIAL.value
        new_logs.append(_log(f"[PUBLISHER] Created PR (PARTIAL): {pr_url}"))
        new_logs.append(f"[PUBLISHER] Tagged as beta release")
    else:
        status = PipelineStatus.SUCCESS.value
        new_logs.append(_log(f"[PUBLISHER] Created PR (SUCCESS): {pr_url}"))

    return {
        "published": True,
        "pr_url": pr_url,
        "status": status,
        "current_phase": PipelinePhase.COMPLETED.value,
        "completed_at": datetime.utcnow().isoformat(),
        "logs": new_logs,  # Only NEW logs
    }
