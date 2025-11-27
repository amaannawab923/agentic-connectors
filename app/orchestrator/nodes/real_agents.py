"""Real agent nodes for the LangGraph orchestrator.

These nodes wrap the actual Claude Agent SDK agents for production use.
Each node calls the corresponding agent and transforms its output to match
the PipelineState requirements.

Usage:
    # In pipeline.py, import from here instead of mock_agents:
    from .nodes.real_agents import research_node, generator_node, ...
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..state import (
    PipelineState,
    PipelinePhase,
)

# Import the actual agents
from ...agents.research import ResearchAgent
from ...agents.generator import GeneratorAgent
from ...agents.mock_generator import MockGeneratorAgent
from ...agents.tester import TesterAgent, TesterMode
from ...agents.test_reviewer import TestReviewerAgent
from ...agents.publisher_new import PublisherAgentNew

logger = logging.getLogger(__name__)

# Base output directory for generated connectors
OUTPUT_BASE_DIR = Path(__file__).parent.parent.parent.parent / "output" / "connector-implementations"


def _log(message: str) -> str:
    """Create a timestamped log entry."""
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    logger.info(log_entry)
    return log_entry


# ─────────────────────────────────────────────────────────────────────────────
# Research Node (Real Agent)
# ─────────────────────────────────────────────────────────────────────────────

# Singleton agent instance (reuse for efficiency)
_research_agent = None


def _get_research_agent() -> ResearchAgent:
    """Get or create the research agent singleton."""
    global _research_agent
    if _research_agent is None:
        _research_agent = ResearchAgent()
    return _research_agent


async def research_node(state: PipelineState) -> Dict[str, Any]:
    """Real research agent - uses Claude Agent SDK for API documentation research.

    Calls ResearchAgent.execute() which:
    - Searches for API documentation
    - Finds existing connector implementations (Airbyte, Singer, etc.)
    - Generates a comprehensive research markdown document

    Handles both initial research and re-research (when REJECT:CONTEXT).
    When re-researching, passes context_gaps as additional context.

    Returns state updates with:
    - research_output: Dict containing the research document and metadata
    - current_phase: "researching"
    - logs: New log entries
    """
    connector_name = state["connector_name"]
    research_retries = state.get("research_retries", 0)
    context_gaps = state.get("context_gaps", [])

    is_re_research = research_retries > 0 or len(context_gaps) > 0

    # Collect NEW logs only (reducer will merge with existing)
    new_logs: List[str] = []

    if is_re_research:
        new_logs.append(_log(f"[RESEARCH] Re-researching {connector_name} (retry {research_retries})..."))
        new_logs.append(f"[RESEARCH] Context gaps to address: {context_gaps}")
    else:
        new_logs.append(_log(f"[RESEARCH] Starting research for {connector_name}..."))

    # Build additional context from context_gaps if re-researching
    additional_context = None
    if context_gaps:
        additional_context = f"""
## Previous Research Gaps

The previous research was insufficient. Please specifically address these gaps:

{chr(10).join(f'- {gap}' for gap in context_gaps)}

Focus your research on filling these specific knowledge gaps.
"""

    try:
        # Get the research agent
        agent = _get_research_agent()

        # Execute the research agent
        new_logs.append(_log(f"[RESEARCH] Calling Claude Agent SDK..."))
        result = await agent.execute(
            connector_name=connector_name,
            additional_context=additional_context,
        )

        if not result.success:
            new_logs.append(_log(f"[RESEARCH] FAILED: {result.error}"))
            return {
                "current_phase": PipelinePhase.RESEARCHING.value,
                "errors": [f"Research failed: {result.error}"],
                "logs": new_logs,
            }

        # Parse the research output
        research_doc = result.output or ""
        new_logs.append(_log(f"[RESEARCH] Completed! Generated {len(research_doc)} chars of research"))

        # Structure the research output for downstream agents
        research_output = {
            "full_document": research_doc,
            "connector_name": connector_name,
            "context_gaps_addressed": context_gaps,
            "researched_at": datetime.utcnow().isoformat(),
            "duration_seconds": result.duration_seconds,
            "tokens_used": result.tokens_used,
        }

        result_updates = {
            "research_output": research_output,
            "current_phase": PipelinePhase.RESEARCHING.value,
            "logs": new_logs,
        }

        # Clear review_decision when starting fresh research (was preserved for routing)
        if is_re_research:
            result_updates["review_decision"] = None

        return result_updates

    except Exception as e:
        logger.exception(f"Research agent exception: {e}")
        new_logs.append(_log(f"[RESEARCH] EXCEPTION: {str(e)}"))
        return {
            "current_phase": PipelinePhase.RESEARCHING.value,
            "errors": [f"Research exception: {str(e)}"],
            "logs": new_logs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Generator Node (Real Agent)
# ─────────────────────────────────────────────────────────────────────────────

# Singleton agent instance (reuse for efficiency)
_generator_agent: Optional[GeneratorAgent] = None


def _get_generator_agent() -> GeneratorAgent:
    """Get or create the generator agent singleton."""
    global _generator_agent
    if _generator_agent is None:
        _generator_agent = GeneratorAgent()
    return _generator_agent


def _read_generated_files(connector_dir: Path) -> Dict[str, str]:
    """Read all generated files from the connector directory.

    Args:
        connector_dir: Path to the connector output directory.

    Returns:
        Dictionary mapping relative file paths to their contents.
    """
    files: Dict[str, str] = {}

    if not connector_dir.exists():
        return files

    # Read all Python files
    for file_path in connector_dir.rglob("*.py"):
        try:
            relative_path = str(file_path.relative_to(connector_dir))
            files[relative_path] = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")

    # Read requirements.txt if present
    req_path = connector_dir / "requirements.txt"
    if req_path.exists():
        try:
            files["requirements.txt"] = req_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read requirements.txt: {e}")

    # Read IMPLEMENTATION.md if present (critical for tester agent)
    impl_path = connector_dir / "IMPLEMENTATION.md"
    if impl_path.exists():
        try:
            files["IMPLEMENTATION.md"] = impl_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read IMPLEMENTATION.md: {e}")

    return files


async def generator_node(state: PipelineState) -> Dict[str, Any]:
    """Real generator agent - uses Claude Agent SDK for code generation.

    Calls GeneratorAgent.execute() which:
    - Takes the research document as context
    - Generates complete connector code using the Write tool
    - Creates files in the output directory

    Triggered by:
    - Initial generation (after research completes)
    - TestReviewer VALID+FAIL (code fails tests, needs fixes)
    - Reviewer REJECT:CODE (code quality issues)

    Returns state updates with:
    - generated_code: Dict containing file paths and contents (for SQLite persistence)
    - connector_dir: Path to the output directory
    - current_phase: "generating"
    - logs: New log entries
    """
    connector_name = state["connector_name"]
    connector_type = state.get("connector_type", "source")
    research_output = state.get("research_output", {})

    # Get retry context
    gen_fix_retries = state.get("gen_fix_retries", 0)
    review_retries = state.get("review_retries", 0)
    test_review_feedback = state.get("test_review_feedback", [])
    review_feedback = state.get("review_feedback", [])

    # Collect NEW logs only (reducer will merge with existing)
    new_logs: List[str] = []

    # Determine action based on what triggered this node
    if test_review_feedback:
        action = "Fixing code"
        reason = f"test failures: {test_review_feedback[:3]}"
        new_logs.append(_log(f"[GENERATOR] Fixing code for {connector_name} (test failures)..."))
    elif review_feedback:
        action = "Improving code"
        reason = f"review feedback: {review_feedback[:3]}"
        new_logs.append(_log(f"[GENERATOR] Improving code for {connector_name} (review feedback)..."))
    else:
        action = "Generating code"
        reason = "initial generation"
        new_logs.append(_log(f"[GENERATOR] Generating code for {connector_name}..."))

    new_logs.append(f"[GENERATOR] Action: {action}, Reason: {reason}")
    new_logs.append(f"[GENERATOR] gen_fix_retries={gen_fix_retries}, review_retries={review_retries}")

    # Extract research document from state
    research_doc = research_output.get("full_document", "")
    if not research_doc:
        new_logs.append(_log(f"[GENERATOR] ERROR: No research document found in state"))
        return {
            "current_phase": PipelinePhase.GENERATING.value,
            "errors": ["Generator failed: No research document available"],
            "logs": new_logs,
        }

    new_logs.append(f"[GENERATOR] Research document: {len(research_doc)} chars")

    # Build output directory path
    connector_slug = connector_name.lower().replace(" ", "-").replace("_", "-")
    connector_dir = OUTPUT_BASE_DIR / f"{connector_type}-{connector_slug}"

    new_logs.append(f"[GENERATOR] Output directory: {connector_dir}")

    try:
        # Get the generator agent
        agent = _get_generator_agent()

        # Execute the generator agent
        # Determine if this is FIX mode (triggered by test failures)
        is_fix_mode = bool(test_review_feedback) and connector_dir.exists()

        if is_fix_mode:
            new_logs.append(_log(f"[GENERATOR] FIX MODE - Fixing code to pass existing tests..."))
            new_logs.append(f"[GENERATOR] Connector dir: {connector_dir}")
            new_logs.append(f"[GENERATOR] Errors to fix: {len(test_review_feedback)}")
        else:
            new_logs.append(_log(f"[GENERATOR] GENERATE MODE - Creating new code..."))

        result = await agent.execute(
            connector_name=connector_name,
            connector_type=connector_type,
            research_doc_content=research_doc,
            fix_errors=test_review_feedback if test_review_feedback else None,
            review_feedback=review_feedback if review_feedback else None,
            connector_dir=str(connector_dir) if is_fix_mode else None,
        )

        if not result.success:
            new_logs.append(_log(f"[GENERATOR] FAILED: {result.error}"))
            return {
                "current_phase": PipelinePhase.GENERATING.value,
                "errors": [f"Generator failed: {result.error}"],
                "logs": new_logs,
            }

        # Read all generated files from disk for persistence in SQLite
        generated_files = _read_generated_files(connector_dir)

        if not generated_files:
            new_logs.append(_log(f"[GENERATOR] WARNING: No files found in output directory"))
            return {
                "current_phase": PipelinePhase.GENERATING.value,
                "errors": ["Generator failed: No files were generated"],
                "logs": new_logs,
            }

        new_logs.append(_log(f"[GENERATOR] Completed! Generated {len(generated_files)} files"))
        for file_path in sorted(generated_files.keys()):
            file_size = len(generated_files[file_path])
            new_logs.append(f"[GENERATOR]   - {file_path} ({file_size} chars)")

        # Structure the generated code for state persistence
        # This stores the full file contents in SQLite
        generated_code = {
            "files": generated_files,
            "connector_name": connector_name,
            "connector_type": connector_type,
            "action": action,
            "reason": reason,
            "generated_at": datetime.utcnow().isoformat(),
            "duration_seconds": result.duration_seconds,
            "tokens_used": result.tokens_used,
            "file_count": len(generated_files),
            "total_size": sum(len(content) for content in generated_files.values()),
        }

        return {
            "generated_code": generated_code,
            "connector_dir": str(connector_dir),
            "current_phase": PipelinePhase.GENERATING.value,
            # Clear feedback after processing (use empty list for reducer)
            "test_review_feedback": [],
            "review_feedback": [],
            "logs": new_logs,
        }

    except Exception as e:
        logger.exception(f"Generator agent exception: {e}")
        new_logs.append(_log(f"[GENERATOR] EXCEPTION: {str(e)}"))
        return {
            "current_phase": PipelinePhase.GENERATING.value,
            "errors": [f"Generator exception: {str(e)}"],
            "logs": new_logs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Mock Generator Node (Real Agent)
# ─────────────────────────────────────────────────────────────────────────────

# Singleton agent instance (reuse for efficiency)
_mock_generator_agent = None


def _get_mock_generator_agent() -> MockGeneratorAgent:
    """Get or create the mock generator agent singleton."""
    global _mock_generator_agent
    if _mock_generator_agent is None:
        _mock_generator_agent = MockGeneratorAgent()
    return _mock_generator_agent


async def mock_generator_node(state: PipelineState) -> Dict[str, Any]:
    """Real mock generator agent - uses Claude Agent SDK for fixture generation.

    Calls MockGeneratorAgent.execute() which:
    - Reads IMPLEMENTATION.md from Generator output
    - Analyzes test files to understand fixture requirements
    - Researches mock library requirements (universe_domain, etc.)
    - Generates comprehensive fixtures and conftest.py
    - Does NOT run tests (that's Tester's job)

    Only runs on first generation when fixtures don't exist.
    On retry loops (VALID+FAIL → Generator → Tester), this node is SKIPPED.

    Returns state updates with:
    - mock_generation_output: Dict with fixture metadata
    - fixtures_created: List of fixture file paths
    - mock_generation_skipped: True if skipped (fixtures already exist)
    - current_phase: "mock_generating"
    - logs: New log entries
    """
    connector_name = state["connector_name"]
    connector_type = state.get("connector_type", "source")
    connector_dir = state.get("connector_dir", "")
    generated_code = state.get("generated_code", {})
    research_output = state.get("research_output", {})

    # Collect NEW logs only (reducer will merge with existing)
    new_logs: List[str] = []

    # Validate connector directory
    if not connector_dir:
        # Build it from connector name if not provided
        connector_slug = connector_name.lower().replace(" ", "-").replace("_", "-")
        connector_dir = str(OUTPUT_BASE_DIR / f"{connector_type}-{connector_slug}")
        new_logs.append(f"[MOCK_GENERATOR] Built connector_dir from name: {connector_dir}")

    connector_path = Path(connector_dir)
    if not connector_path.exists():
        new_logs.append(_log(f"[MOCK_GENERATOR] ERROR: Connector directory not found: {connector_dir}"))
        return {
            "current_phase": PipelinePhase.MOCK_GENERATING.value,
            "mock_generation_skipped": True,
            "errors": [f"MockGenerator failed: Connector directory not found"],
            "logs": new_logs,
        }

    # Check if fixtures already exist (fast-path skip)
    fixtures_dir = connector_path / "tests" / "fixtures"
    conftest_path = connector_path / "tests" / "conftest.py"

    if fixtures_dir.exists() and conftest_path.exists():
        new_logs.append(_log(f"[MOCK_GENERATOR] Fixtures already exist, skipping generation"))
        new_logs.append(f"[MOCK_GENERATOR] Found fixtures at: {fixtures_dir}")
        new_logs.append(f"[MOCK_GENERATOR] Found conftest at: {conftest_path}")

        return {
            "current_phase": PipelinePhase.MOCK_GENERATING.value,
            "mock_generation_skipped": True,
            "logs": new_logs,
        }

    # Fixtures don't exist - run MockGenerator
    new_logs.append(_log(f"[MOCK_GENERATOR] Generating fixtures and conftest.py for {connector_name}..."))
    new_logs.append(f"[MOCK_GENERATOR] Working directory: {connector_dir}")

    # Extract IMPLEMENTATION.md summary from generated_code (if available)
    implementation_summary = None
    if generated_code and "implementation_summary" in generated_code:
        implementation_summary = generated_code["implementation_summary"]
        new_logs.append(f"[MOCK_GENERATOR] Using IMPLEMENTATION summary from Generator")
    elif (connector_path / "IMPLEMENTATION.md").exists():
        # Fallback: read from file
        implementation_summary = (connector_path / "IMPLEMENTATION.md").read_text()
        new_logs.append(f"[MOCK_GENERATOR] Read IMPLEMENTATION.md from file")

    # Extract research summary
    research_summary = None
    if research_output:
        research_summary = research_output.get("full_document", "")
        new_logs.append(f"[MOCK_GENERATOR] Using research output ({len(research_summary)} chars)")

    # Extract client methods from generated code
    client_methods = None
    if generated_code and "client_methods" in generated_code:
        client_methods = generated_code["client_methods"]
        new_logs.append(f"[MOCK_GENERATOR] Found {len(client_methods)} client methods from Generator")

    try:
        # Get the mock generator agent
        agent = _get_mock_generator_agent()

        # Execute the mock generator agent
        new_logs.append(_log(f"[MOCK_GENERATOR] Calling Claude Agent SDK (max 35 turns)..."))

        result = await agent.execute(
            connector_name=connector_name,
            connector_type=connector_type,
            research_summary=research_summary,
            client_methods=client_methods,
        )

        if not result.success:
            new_logs.append(_log(f"[MOCK_GENERATOR] FAILED: {result.error}"))
            return {
                "current_phase": PipelinePhase.MOCK_GENERATING.value,
                "mock_generation_skipped": False,
                "errors": [f"MockGenerator failed: {result.error}"],
                "logs": new_logs,
            }

        # Parse the mock generation output
        try:
            output_data = json.loads(result.output) if isinstance(result.output, str) else result.output
        except (json.JSONDecodeError, TypeError):
            output_data = {"raw_output": result.output}

        # Extract fixture information
        fixtures_created_list = []
        if fixtures_dir.exists():
            fixtures_created_list = [str(f.relative_to(connector_path)) for f in fixtures_dir.rglob("*.json")]

        fixture_count = output_data.get("fixture_count", len(fixtures_created_list))

        new_logs.append(_log(f"[MOCK_GENERATOR] Completed! Created {fixture_count} fixtures"))
        new_logs.append(f"[MOCK_GENERATOR] Fixtures directory: {fixtures_dir}")
        new_logs.append(f"[MOCK_GENERATOR] conftest.py: {conftest_path}")

        # Structure the mock generation output
        mock_output = {
            "fixtures_dir": str(fixtures_dir),
            "conftest_path": str(conftest_path),
            "fixture_count": fixture_count,
            "duration_seconds": result.duration_seconds,
            "tokens_used": result.tokens_used,
            "generated_at": datetime.utcnow().isoformat(),
        }

        return {
            "mock_generation_output": mock_output,
            "fixtures_created": fixtures_created_list,
            "mock_generation_skipped": False,
            "current_phase": PipelinePhase.MOCK_GENERATING.value,
            "logs": new_logs,
        }

    except Exception as e:
        logger.exception(f"MockGenerator agent exception: {e}")
        new_logs.append(_log(f"[MOCK_GENERATOR] EXCEPTION: {str(e)}"))
        return {
            "current_phase": PipelinePhase.MOCK_GENERATING.value,
            "mock_generation_skipped": False,
            "errors": [f"MockGenerator exception: {str(e)}"],
            "logs": new_logs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tester Node (Real Agent)
# ─────────────────────────────────────────────────────────────────────────────

# Singleton agent instance (reuse for efficiency)
_tester_agent: Optional[TesterAgent] = None


def _get_tester_agent() -> TesterAgent:
    """Get or create the tester agent singleton."""
    global _tester_agent
    if _tester_agent is None:
        _tester_agent = TesterAgent()
    return _tester_agent


async def tester_node(state: PipelineState) -> Dict[str, Any]:
    """Real tester agent - uses Claude Agent SDK for comprehensive testing.

    Calls TesterAgent.execute() which:
    - Searches online for testing patterns specific to the API
    - Reads IMPLEMENTATION.md and source code
    - Creates mock servers using httpretty
    - Generates and runs comprehensive tests
    - Reports detailed results with specific errors

    Supports three modes:
    - GENERATE: First run - create tests from scratch
    - RERUN: From Generator after fix - just re-run existing tests
    - FIX: From TestReviewer (INVALID) - fix tests based on feedback

    Returns state updates with:
    - test_output: Dict containing test results and details
    - current_phase: "testing"
    - logs: New log entries
    """
    connector_name = state["connector_name"]
    connector_type = state.get("connector_type", "source")
    connector_dir = state.get("connector_dir", "")
    generated_code = state.get("generated_code", {})
    mock_generation_output = state.get("mock_generation_output", {})
    test_retries = state.get("test_retries", 0)
    gen_fix_retries = state.get("gen_fix_retries", 0)
    test_review_decision = state.get("test_review_decision", "")
    test_review_feedback = state.get("test_review_feedback", [])

    # Collect NEW logs only (reducer will merge with existing)
    new_logs: List[str] = []

    # Determine the operating mode based on state
    # Priority:
    # 1. If test_review_decision is "invalid" -> FIX mode (tests were wrong)
    # 2. If gen_fix_retries > 0 and tests exist -> RERUN mode (generator fixed code)
    # 3. Otherwise -> GENERATE mode (first run)

    mode = TesterMode.GENERATE  # Default

    if test_review_decision == "invalid" and test_retries > 0:
        # Tests were marked invalid by TestReviewer - need to fix them
        mode = TesterMode.FIX
        new_logs.append(_log(f"[TESTER] FIX MODE - Fixing tests for {connector_name} (retry {test_retries})..."))
        new_logs.append(f"[TESTER] TestReviewer determined tests are invalid")
        new_logs.append(f"[TESTER] Feedback items: {len(test_review_feedback)}")
    elif gen_fix_retries > 0:
        # Generator fixed code - just re-run existing tests
        mode = TesterMode.RERUN
        new_logs.append(_log(f"[TESTER] RERUN MODE - Re-running tests for {connector_name} (gen fix #{gen_fix_retries})..."))
        new_logs.append(f"[TESTER] Generator fixed code, re-running existing tests")
    elif test_retries > 0:
        # Previous test run, but not from TestReviewer invalid verdict
        # This might be a retry after some other failure - use RERUN if tests exist
        mode = TesterMode.RERUN
        new_logs.append(_log(f"[TESTER] RERUN MODE - Re-testing {connector_name} (retry {test_retries})..."))
    else:
        # First run - generate tests from scratch
        mode = TesterMode.GENERATE
        new_logs.append(_log(f"[TESTER] GENERATE MODE - Creating tests for {connector_name}..."))

    # Log fixture information if MockGenerator ran
    if mock_generation_output:
        fixture_count = mock_generation_output.get("fixture_count", 0)
        fixtures_dir = mock_generation_output.get("fixtures_dir", "N/A")
        conftest_path = mock_generation_output.get("conftest_path", "N/A")
        new_logs.append(f"[TESTER] MockGenerator created {fixture_count} fixtures")
        new_logs.append(f"[TESTER] Fixtures directory: {fixtures_dir}")
        new_logs.append(f"[TESTER] conftest.py: {conftest_path}")
    else:
        new_logs.append(f"[TESTER] No mock generation output (MockGenerator was skipped or not run)")

    # Validate connector directory
    if not connector_dir:
        # Build it from connector name if not provided
        connector_slug = connector_name.lower().replace(" ", "-").replace("_", "-")
        connector_dir = str(OUTPUT_BASE_DIR / f"{connector_type}-{connector_slug}")
        new_logs.append(f"[TESTER] Built connector_dir from name: {connector_dir}")

    connector_path = Path(connector_dir)
    if not connector_path.exists():
        new_logs.append(_log(f"[TESTER] ERROR: Connector directory not found: {connector_dir}"))
        return {
            "current_phase": PipelinePhase.TESTING.value,
            "test_results": {
                "status": "error",
                "passed": False,
                "errors": [f"Connector directory not found: {connector_dir}"],
            },
            "errors": [f"Tester failed: Connector directory not found"],
            "logs": new_logs,
        }

    # Get IMPLEMENTATION.md content from generated_code if available
    implementation_doc = None
    if generated_code and "files" in generated_code:
        implementation_doc = generated_code["files"].get("IMPLEMENTATION.md")
        if implementation_doc:
            new_logs.append(f"[TESTER] Using IMPLEMENTATION.md from state ({len(implementation_doc)} chars)")

    # Get files dict for context
    generated_files = generated_code.get("files", {}) if generated_code else {}

    try:
        # Get the tester agent
        agent = _get_tester_agent()

        # Execute the tester agent with the appropriate mode
        new_logs.append(_log(f"[TESTER] Calling Claude Agent SDK in {mode.value.upper()} mode..."))
        new_logs.append(f"[TESTER] Connector dir: {connector_dir}")
        new_logs.append(f"[TESTER] Files available: {list(generated_files.keys())[:10]}")

        # Extract test issues from feedback for FIX mode
        test_issues = []
        fix_feedback = []
        if mode == TesterMode.FIX and test_review_feedback:
            for fb in test_review_feedback:
                if fb.startswith("TEST_ISSUE:"):
                    test_issues.append(fb.replace("TEST_ISSUE:", "").strip())
                elif fb.startswith("FIX:"):
                    fix_feedback.append(fb.replace("FIX:", "").strip())
                else:
                    fix_feedback.append(fb)

        result = await agent.execute(
            connector_dir=connector_dir,
            connector_name=connector_name,
            connector_type=connector_type,
            implementation_doc=implementation_doc,
            generated_code=generated_files,
            mode=mode,
            test_issues=test_issues if test_issues else None,
            fix_feedback=fix_feedback if fix_feedback else None,
        )

        if not result.success:
            new_logs.append(_log(f"[TESTER] Tests FAILED"))

            # Parse the test output for detailed errors
            test_output = {}
            if result.output:
                try:
                    test_output = json.loads(result.output)
                except json.JSONDecodeError:
                    test_output = {"raw_output": result.output}

            # Extract errors for feedback to generator
            errors = test_output.get("errors", [])
            if result.error:
                errors.append(result.error)

            new_logs.append(f"[TESTER] Errors found: {len(errors)}")
            for error in errors[:5]:
                new_logs.append(f"[TESTER]   - {error[:100]}...")

            return {
                "current_phase": PipelinePhase.TESTING.value,
                "test_results": {
                    "status": "failed",
                    "passed": False,
                    "errors": errors,
                    "details": test_output,
                    "duration_seconds": result.duration_seconds,
                    "tokens_used": result.tokens_used,
                },
                "logs": new_logs,
            }

        # Tests passed!
        new_logs.append(_log(f"[TESTER] Tests PASSED!"))

        # Parse successful test output
        test_output = {}
        if result.output:
            try:
                test_output = json.loads(result.output)
            except json.JSONDecodeError:
                test_output = {"raw_output": result.output}

        tests_passed = test_output.get("unit_tests_passed", 0)
        tests_failed = test_output.get("unit_tests_failed", 0)
        new_logs.append(f"[TESTER] Results: {tests_passed} passed, {tests_failed} failed")

        return {
            "current_phase": PipelinePhase.TESTING.value,
            "test_results": {
                "status": "passed",
                "passed": True,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "details": test_output,
                "tested_at": datetime.utcnow().isoformat(),
                "duration_seconds": result.duration_seconds,
                "tokens_used": result.tokens_used,
            },
            "logs": new_logs,
        }

    except Exception as e:
        logger.exception(f"Tester agent exception: {e}")
        new_logs.append(_log(f"[TESTER] EXCEPTION: {str(e)}"))
        return {
            "current_phase": PipelinePhase.TESTING.value,
            "test_results": {
                "status": "error",
                "passed": False,
                "errors": [f"Tester exception: {str(e)}"],
            },
            "errors": [f"Tester exception: {str(e)}"],
            "logs": new_logs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Test Reviewer Node (Real Agent)
# ─────────────────────────────────────────────────────────────────────────────

# Singleton agent instance (reuse for efficiency)
_test_reviewer_agent: Optional[TestReviewerAgent] = None


def _get_test_reviewer_agent() -> TestReviewerAgent:
    """Get or create the test reviewer agent singleton."""
    global _test_reviewer_agent
    if _test_reviewer_agent is None:
        _test_reviewer_agent = TestReviewerAgent()
    return _test_reviewer_agent


async def test_reviewer_node(state: PipelineState) -> Dict[str, Any]:
    """Real test reviewer agent - analyzes test results to determine root cause.

    Calls TestReviewerAgent.execute() which:
    - Analyzes test failures
    - Reads both test code and connector code
    - Determines if problem is in TESTS or CONNECTOR CODE
    - Returns decision with context for next agent

    Decisions:
    - INVALID: Tests are buggy -> route back to Tester with feedback
    - VALID_FAIL: Code is buggy -> route back to Generator with feedback
    - VALID_PASS: Tests passed -> route to Reviewer

    Returns state updates with:
    - test_review_decision: Decision string
    - test_review_feedback: List of issues for next agent
    - test_retries: Incremented if INVALID
    - gen_fix_retries: Incremented if VALID_FAIL
    - current_phase: "test_reviewing"
    - logs: New log entries
    """
    connector_name = state["connector_name"]
    connector_dir = state.get("connector_dir", "")
    connector_type = state.get("connector_type", "source")
    test_output = state.get("test_results", {})
    generated_code = state.get("generated_code", {})
    test_retries = state.get("test_retries", 0)
    gen_fix_retries = state.get("gen_fix_retries", 0)

    # Collect NEW logs only
    new_logs: List[str] = []
    new_logs.append(_log(f"[TEST_REVIEWER] Analyzing test results for {connector_name}..."))

    # Validate connector directory
    if not connector_dir:
        connector_slug = connector_name.lower().replace(" ", "-").replace("_", "-")
        connector_dir = str(OUTPUT_BASE_DIR / f"{connector_type}-{connector_slug}")

    # Quick path: tests passed
    if test_output.get("passed", False) or test_output.get("status") == "passed":
        new_logs.append(_log(f"[TEST_REVIEWER] Tests PASSED - routing to reviewer"))
        return {
            "current_phase": PipelinePhase.TEST_REVIEWING.value,
            "test_review_decision": "valid_pass",
            "test_review_feedback": [],
            "logs": new_logs,
        }

    # Tests failed - need to analyze
    new_logs.append(f"[TEST_REVIEWER] Tests failed - analyzing root cause")
    new_logs.append(f"[TEST_REVIEWER] Test status: {test_output.get('status')}")
    new_logs.append(f"[TEST_REVIEWER] Errors: {len(test_output.get('errors', []))}")

    try:
        agent = _get_test_reviewer_agent()

        new_logs.append(_log(f"[TEST_REVIEWER] Calling Claude Agent SDK..."))

        result = await agent.execute(
            connector_dir=connector_dir,
            connector_name=connector_name,
            test_output=test_output,
            generated_code=generated_code.get("files", {}) if generated_code else {},
        )

        decision = result.get("decision", "VALID_FAIL").lower()
        confidence = result.get("confidence", 0.5)
        analysis = result.get("analysis", "")
        test_issues = result.get("test_issues", [])
        code_issues = result.get("code_issues", [])
        recommendations = result.get("recommendations", [])

        new_logs.append(_log(f"[TEST_REVIEWER] Decision: {decision.upper()} (confidence: {confidence:.2f})"))
        new_logs.append(f"[TEST_REVIEWER] Analysis: {analysis[:200]}...")

        # Prepare feedback based on decision
        if decision == "invalid":
            # Tests are buggy - send feedback to Tester
            new_logs.append(f"[TEST_REVIEWER] Tests are INVALID - routing to Tester")
            new_logs.append(f"[TEST_REVIEWER] Test issues: {test_issues[:3]}")

            feedback = []
            feedback.extend([f"TEST_ISSUE: {issue}" for issue in test_issues[:10]])
            feedback.extend([f"FIX: {rec}" for rec in recommendations[:5]])

            return {
                "current_phase": PipelinePhase.TEST_REVIEWING.value,
                "test_review_decision": "invalid",
                "test_review_feedback": feedback,
                "test_retries": test_retries + 1,
                "logs": new_logs,
            }

        elif decision == "valid_fail":
            # Code is buggy - send feedback to Generator
            new_logs.append(f"[TEST_REVIEWER] Code has BUGS - routing to Generator")
            new_logs.append(f"[TEST_REVIEWER] Code issues: {code_issues[:3]}")

            feedback = []
            feedback.extend([f"CODE_BUG: {issue}" for issue in code_issues[:10]])
            feedback.extend([f"FIX: {rec}" for rec in recommendations[:5]])

            # Also include original test errors for context
            original_errors = test_output.get("errors", [])
            feedback.extend([f"TEST_ERROR: {err}" for err in original_errors[:5]])

            return {
                "current_phase": PipelinePhase.TEST_REVIEWING.value,
                "test_review_decision": "valid_fail",
                "test_review_feedback": feedback,
                "gen_fix_retries": gen_fix_retries + 1,
                "logs": new_logs,
            }

        else:  # valid_pass (shouldn't happen if we got here, but handle it)
            new_logs.append(f"[TEST_REVIEWER] Tests PASSED - routing to Reviewer")
            return {
                "current_phase": PipelinePhase.TEST_REVIEWING.value,
                "test_review_decision": "valid_pass",
                "test_review_feedback": [],
                "logs": new_logs,
            }

    except Exception as e:
        logger.exception(f"Test reviewer agent exception: {e}")
        new_logs.append(_log(f"[TEST_REVIEWER] EXCEPTION: {str(e)}"))

        # On error, default to treating it as code failure
        return {
            "current_phase": PipelinePhase.TEST_REVIEWING.value,
            "test_review_decision": "valid_fail",
            "test_review_feedback": [f"Test review failed: {str(e)}"],
            "gen_fix_retries": gen_fix_retries + 1,
            "errors": [f"Test reviewer exception: {str(e)}"],
            "logs": new_logs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Publisher Node (Real Agent)
# ─────────────────────────────────────────────────────────────────────────────

# Singleton agent instance
_publisher_agent = None


def _get_publisher_agent() -> PublisherAgentNew:
    """Get or create the publisher agent singleton."""
    global _publisher_agent
    if _publisher_agent is None:
        _publisher_agent = PublisherAgentNew()
    return _publisher_agent


async def publisher_node(state: PipelineState) -> Dict[str, Any]:
    """Real publisher agent - publishes connector to GitHub repository.

    Calls PublisherAgentNew.execute() which:
    - Initializes Git repository
    - Configures remote with authentication token
    - Creates/checks out branch
    - Stages and commits all files
    - Pushes to GitHub
    - Optionally creates PR

    Returns state updates with:
    - publish_output: Dict containing commit hash, branch name, repository URL
    - current_phase: "publishing"
    - logs: New log entries
    """
    connector_name = state["connector_name"]
    connector_dir = state.get("connector_dir", "")
    generated_code = state.get("generated_code", {})

    # Collect NEW logs only (reducer will merge with existing)
    new_logs: List[str] = []
    new_logs.append(_log(f"[PUBLISHER] Publishing {connector_name} to GitHub..."))

    # Get GitHub configuration from environment or config
    from ...config import get_settings
    settings = get_settings()

    repo_owner = settings.github_repo_owner
    repo_name = settings.github_repo_name
    personal_access_token = settings.github_token.get_secret_value() if settings.github_token else None

    if not repo_owner or not repo_name:
        error_msg = "GitHub repository owner and name must be configured (GITHUB_REPO_OWNER, GITHUB_REPO_NAME)"
        new_logs.append(_log(f"[PUBLISHER] ERROR: {error_msg}"))
        return {
            "current_phase": PipelinePhase.PUBLISHING.value,
            "errors": [error_msg],
            "logs": new_logs,
        }

    if not personal_access_token:
        error_msg = "GitHub personal access token must be configured (GITHUB_TOKEN)"
        new_logs.append(_log(f"[PUBLISHER] ERROR: {error_msg}"))
        return {
            "current_phase": PipelinePhase.PUBLISHING.value,
            "errors": [error_msg],
            "logs": new_logs,
        }

    new_logs.append(_log(f"[PUBLISHER] Target: {repo_owner}/{repo_name}"))

    try:
        # Get the publisher agent
        agent = _get_publisher_agent()

        # Collect generated files for publishing
        from ...models.schemas import GeneratedFile
        generated_files = []

        for file_path, content in generated_code.items():
            generated_files.append(GeneratedFile(
                path=file_path,
                content=content
            ))

        new_logs.append(_log(f"[PUBLISHER] Publishing {len(generated_files)} files"))

        # Execute the publisher agent
        result = await agent.execute(
            generated_files=generated_files,
            connector_name=connector_name,
            output_dir=connector_dir,
            repo_owner=repo_owner,
            repo_name=repo_name,
            personal_access_token=personal_access_token,
            branch_name=None,  # Auto-generate: connector/<name>
            create_pr=False,  # Just push, don't create PR
        )

        if not result.success:
            new_logs.append(_log(f"[PUBLISHER] FAILED: {result.error}"))
            return {
                "current_phase": PipelinePhase.PUBLISHING.value,
                "errors": [f"Publishing failed: {result.error}"],
                "logs": new_logs,
            }

        # Parse the publish output
        publish_data = json.loads(result.output) if result.output else {}

        branch_name = publish_data.get("branch_name", "unknown")
        commit_hash = publish_data.get("commit_hash", "")
        remote_url = publish_data.get("remote_url", "")

        new_logs.append(_log(f"[PUBLISHER] SUCCESS! Pushed to branch: {branch_name}"))
        if commit_hash:
            new_logs.append(_log(f"[PUBLISHER] Commit: {commit_hash[:8]}"))
        if remote_url:
            new_logs.append(_log(f"[PUBLISHER] View: {remote_url}/tree/{branch_name}"))

        # Structure the publish output
        publish_output = {
            "branch_name": branch_name,
            "commit_hash": commit_hash,
            "remote_url": remote_url,
            "repository": f"{repo_owner}/{repo_name}",
            "published_at": datetime.utcnow().isoformat(),
            "duration_seconds": result.duration_seconds,
            "files_published": len(generated_files),
        }

        return {
            "publish_output": publish_output,
            "current_phase": PipelinePhase.PUBLISHING.value,
            "logs": new_logs,
        }

    except Exception as e:
        logger.exception(f"Publisher agent exception: {e}")
        new_logs.append(_log(f"[PUBLISHER] EXCEPTION: {str(e)}"))

        return {
            "current_phase": PipelinePhase.PUBLISHING.value,
            "errors": [f"Publisher exception: {str(e)}"],
            "logs": new_logs,
        }
