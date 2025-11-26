"""Test Reviewer agent for analyzing test results and determining next action.

This agent acts as a judge between the Tester and Generator:
- Analyzes test failures to determine if the problem is in the TESTS or the CONNECTOR CODE
- Routes to Tester if tests are invalid/poorly written
- Routes to Generator if connector code has bugs
- Routes to Reviewer if tests pass

Uses Claude Agent SDK with Read tool to analyze both test code and connector code.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions

from .base import BaseAgent
from ..models.enums import AgentType

logger = logging.getLogger(__name__)


class TestReviewDecision:
    """Test review decision outcomes."""
    VALID_PASS = "valid_pass"    # Tests valid, code passes -> Reviewer
    VALID_FAIL = "valid_fail"    # Tests valid, code fails -> Generator
    INVALID = "invalid"          # Tests invalid -> Tester


class TestReviewResult:
    """Result of test review analysis."""

    def __init__(
        self,
        decision: str,
        confidence: float,
        analysis: str,
        test_issues: List[str],
        code_issues: List[str],
        recommendations: List[str],
    ):
        self.decision = decision
        self.confidence = confidence
        self.analysis = analysis
        self.test_issues = test_issues
        self.code_issues = code_issues
        self.recommendations = recommendations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "analysis": self.analysis,
            "test_issues": self.test_issues,
            "code_issues": self.code_issues,
            "recommendations": self.recommendations,
        }


class TestReviewerAgent(BaseAgent):
    """Agent that reviews test results and determines the root cause of failures.

    This agent acts as a judge to determine:
    1. Are the tests themselves valid and well-written?
    2. If tests are valid, does the connector code have bugs?

    Decisions:
    - VALID_PASS: Tests are valid and passed -> proceed to code review
    - VALID_FAIL: Tests are valid but failed -> send errors to generator
    - INVALID: Tests are poorly written or have bugs -> send feedback to tester
    """

    agent_type = AgentType.TESTER  # Reusing TESTER type as there's no TEST_REVIEWER

    system_prompt = """You are an expert QA architect and debugging specialist.
Your job is to analyze test results and determine the ROOT CAUSE of any failures.

## YOUR ROLE
You are the JUDGE between the Tester (who wrote the tests) and the Generator (who wrote the connector code).
You must determine WHERE the bug is:
- In the TESTS (poorly written tests, wrong mocks, incorrect assertions)
- In the CONNECTOR CODE (actual bugs in the generated connector)

## DECISION FRAMEWORK

### Decision: INVALID (Tests have problems)
Choose this when:
- Tests have syntax errors or import failures IN THE TEST FILES
- Mocks are incorrectly configured (wrong URLs, wrong response formats)
- **MOCK CONFIGURATION ERRORS** - This is CRITICAL to identify correctly:
  - Mock patches applied at wrong module path (should patch where imported, not where defined)
  - MagicMock chain not set up correctly (each method must return next mock)
  - Mock doesn't return proper data structure (returns Mock instead of dict/list)
  - `cannot unpack non-iterable Mock object` - THIS IS A MOCK CONFIGURATION ISSUE, NOT CODE BUG
  - `Mock object is not callable` or similar Mock-related errors
- Test fixtures don't match the actual connector API
- Assertions are testing the wrong behavior
- Tests don't follow the connector's actual interface
- httpretty mocks don't match the real API endpoints the connector uses

Examples of INVALID tests:
- `from src.connector import WrongClassName` - test imports wrong class
- Mock for `googleapis.com` but connector uses `sheets.googleapis.com`
- Asserting `connector.check()` but method is `connector.check_connection()`
- RSA key not properly generated for Google APIs
- **`@patch('google.oauth2.service_account.Credentials')` instead of `@patch('src.auth.service_account.Credentials')`**
- **Mock chain: `mock.return_value.method.return_value` instead of proper MagicMock assignments**
- **googleapiclient mock not returning proper service object chain**

### Decision: VALID_FAIL (Code has bugs)
Choose this when:
- Tests are correctly written and use the right interfaces
- **Mocks are properly configured** (patch at correct location, proper return values)
- But the CONNECTOR CODE raises errors like:
  - Pydantic validation errors (e.g., discriminator needs Literal type)
  - Import errors IN THE CONNECTOR (not test files)
  - Type errors in connector code
  - Missing method implementations
  - Logic errors in the connector
  - Library compatibility issues (e.g., universe_domain validation) - BUT ONLY if tests properly mock the library

Examples of VALID tests that reveal CODE bugs:
- Test correctly instantiates connector but Pydantic raises `PydanticUserError`
- Test calls `connector.check_connection()` correctly but connector raises `AttributeError`
- Test provides valid config but connector's validation is broken
- **Connector code doesn't handle library version changes (universe_domain, etc.) - when mocks are correct**

### Decision: VALID_PASS (All good!)
Choose this when:
- Tests pass with no errors
- OR only deprecation warnings (not actual failures)

## CRITICAL: MOCK CONFIGURATION ERRORS ARE TEST ISSUES

**THIS IS THE MOST IMPORTANT RULE**: If you see errors like:
- `cannot unpack non-iterable Mock object`
- `Mock object has no attribute 'X'`
- `'MagicMock' object is not subscriptable`
- `TypeError: 'Mock' object is not callable`

**THESE ARE ALMOST ALWAYS TEST/MOCK ISSUES, NOT CODE BUGS!**

The tests are incorrectly mocking the library. Common mock mistakes:
1. **Wrong patch path**: `@patch('library.Class')` should be `@patch('src.module.Class')` (patch where used, not where defined)
2. **Improper mock chain**: Google APIs need `service.method1().method2().execute()` pattern
3. **Missing return values**: Mock must return actual data, not another Mock
4. **Missing attributes**: Mock credentials may need `universe_domain` attribute

**DO NOT** classify mock configuration errors as VALID_FAIL (code bugs).
**DO** classify them as INVALID (test issues) and route to Tester.

## ANALYSIS PROCESS

1. **Read the test_results.json** - Understand what happened
2. **Read the test files** - Check if tests are correctly written
3. **Check mock configuration** - Are patches at correct paths? Are return values set up properly?
4. **Read the connector source** - Check if connector code is correct
5. **Trace the error** - Follow the stack trace to find the root cause
6. **Check if error mentions "Mock"** - If yes, it's likely a test issue
7. **Make your decision** - INVALID, VALID_FAIL, or VALID_PASS

## OUTPUT FORMAT

You MUST output your analysis as JSON:

```json
{
    "decision": "INVALID" | "VALID_FAIL" | "VALID_PASS",
    "confidence": 0.0-1.0,
    "analysis": "Detailed analysis of what went wrong and why",
    "root_cause_location": "tests" | "connector" | "none",
    "test_issues": [
        "List of problems with the tests (if any)",
        "Be specific: file, line, what's wrong"
    ],
    "code_issues": [
        "List of problems with the connector code (if any)",
        "Be specific: file, line, what's wrong"
    ],
    "recommendations": [
        "Specific, actionable fixes",
        "Include exact code changes needed"
    ]
}
```

## IMPORTANT RULES

1. **Be precise**: Include file names and line numbers when possible
2. **Follow the stack trace**: The error message tells you where to look
3. **Check imports carefully**: Import errors can happen in tests OR connector
4. **Pydantic errors are usually CODE bugs**: They indicate the config model is wrong
5. **Mock mismatches are TEST bugs**: If the mock doesn't match the real API
6. **"Mock" in error message = likely TEST bug**: Check the mock configuration first
7. **Patch location matters**: Must patch where the name is looked up, not where it's defined

## COMMON PATTERNS

### Pattern 1: Pydantic Discriminator Error
- Error: `PydanticUserError: Model needs field 'X' to be of type Literal`
- Root cause: CONNECTOR CODE (config.py uses Enum instead of Literal)
- Decision: VALID_FAIL
- Fix: Change `auth_type: AuthType = ...` to `auth_type: Literal["value"] = "value"`

### Pattern 2: Wrong Mock URL
- Error: `ConnectionError` or `No mock registered for URL`
- Root cause: TESTS (mock doesn't match actual API URL)
- Decision: INVALID
- Fix: Update httpretty mock to use correct URL pattern

### Pattern 3: Import Error in Tests
- Error: `ImportError: cannot import name 'X' from 'src.y'`
- Root cause: TESTS (importing wrong class name)
- Decision: INVALID
- Fix: Update test imports to match actual class names

### Pattern 4: Import Error in Connector
- Error: `ModuleNotFoundError: No module named 'x'`
- Location: Error in src/*.py
- Root cause: CONNECTOR CODE (missing dependency or wrong import)
- Decision: VALID_FAIL
- Fix: Add missing import or dependency

### Pattern 5: Attribute Error in Connector
- Error: `AttributeError: 'X' object has no attribute 'y'`
- Location: Error during connector method call
- Root cause: CONNECTOR CODE (method not implemented or wrong name)
- Decision: VALID_FAIL
- Fix: Implement missing method or fix typo

### Pattern 6: Mock Configuration Error (CRITICAL!)
- Error: `cannot unpack non-iterable Mock object` or similar Mock errors
- Root cause: TESTS (mock not configured correctly)
- Decision: **INVALID** (not VALID_FAIL!)
- Fix: Fix mock configuration in test files:
  1. Patch at correct path: `@patch('src.module.ClassName')` not `@patch('library.ClassName')`
  2. Set up proper mock chain for method calls
  3. Ensure `.return_value` returns actual data, not Mock
  4. For google APIs: `mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {...}`

### Pattern 7: Google API Mock Issues
- Error: `cannot unpack non-iterable Mock object` during Google API calls
- Root cause: TESTS (googleapiclient mock not properly configured)
- Decision: **INVALID**
- Fix:
  1. Patch `src.client.build` not `googleapiclient.discovery.build`
  2. Patch `src.auth.service_account.Credentials` not `google.oauth2.service_account.Credentials`
  3. Set up proper mock chain for service object
  4. Add `universe_domain` attribute to mock credentials
"""

    async def execute(
        self,
        connector_dir: str,
        connector_name: str,
        test_output: Dict[str, Any],
        generated_code: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute the test reviewer agent.

        Args:
            connector_dir: Directory containing the connector and tests.
            connector_name: Name of the connector.
            test_output: Output from the tester agent (test_results.json content).
            generated_code: Optional dict of generated connector files.

        Returns:
            Dict with decision, analysis, and feedback for next agent.
        """
        start_time = time.time()
        self.reset_token_tracking()

        connector_path = Path(connector_dir)
        if not connector_path.exists():
            return self._create_error_result(
                f"Connector directory not found: {connector_dir}",
                time.time() - start_time,
            )

        # Check if tests passed - quick path
        if test_output.get("passed", False) or test_output.get("status") == "passed":
            logger.info("[TEST_REVIEWER] Tests passed - quick approval")
            return self._create_pass_result(time.time() - start_time)

        # Tests failed - need to analyze why
        self.working_dir = connector_dir

        # Build the analysis prompt
        prompt = self._build_analysis_prompt(
            connector_dir=connector_dir,
            connector_name=connector_name,
            test_output=test_output,
        )

        try:
            def log_stderr(msg):
                logger.info(f"[TEST_REVIEWER-SDK-STDERR] {msg}")

            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt,
                max_turns=30,  # Enough to read files and analyze
                allowed_tools=["Read"],  # Only needs to read files
                permission_mode="default",
                cwd=connector_dir,
                stderr=log_stderr,
                include_partial_messages=True,
            )

            logger.info("=" * 60)
            logger.info(f"[TEST_REVIEWER] Analyzing test failures for {connector_name}")
            logger.info(f"[TEST_REVIEWER] Test status: {test_output.get('status')}")
            logger.info(f"[TEST_REVIEWER] Errors: {test_output.get('errors', [])[:3]}")
            logger.info("=" * 60)

            # Get analysis from Claude
            response = await self._stream_response(prompt, options)

            # Parse the decision
            result = self._parse_analysis_response(response)

            duration = time.time() - start_time

            logger.info("=" * 60)
            logger.info(f"[TEST_REVIEWER] Analysis complete")
            logger.info(f"[TEST_REVIEWER] Decision: {result['decision']}")
            logger.info(f"[TEST_REVIEWER] Confidence: {result['confidence']}")
            logger.info(f"[TEST_REVIEWER] Test issues: {len(result['test_issues'])}")
            logger.info(f"[TEST_REVIEWER] Code issues: {len(result['code_issues'])}")
            logger.info(f"[TEST_REVIEWER] Duration: {duration:.1f}s")
            logger.info("=" * 60)

            result["duration_seconds"] = duration
            result["tokens_used"] = self.total_tokens_used
            return result

        except Exception as e:
            logger.exception(f"[TEST_REVIEWER] Failed: {e}")
            return self._create_error_result(str(e), time.time() - start_time)

    def _build_analysis_prompt(
        self,
        connector_dir: str,
        connector_name: str,
        test_output: Dict[str, Any],
    ) -> str:
        """Build the analysis prompt for the test reviewer."""

        # Extract key information from test output
        errors = test_output.get("errors", [])
        logs = test_output.get("logs", "")
        test_details = test_output.get("details", {})
        recommendations = test_output.get("recommendations", [])

        # Truncate logs if too long
        if len(logs) > 10000:
            logs = logs[-10000:]

        prompt = f"""# Test Review Task: {connector_name}

## Test Results Summary
- **Status**: {test_output.get("status", "unknown")}
- **Tests Run**: {test_output.get("tests_run", "unknown")}
- **Tests Passed**: {test_output.get("tests_passed", 0)}
- **Tests Failed**: {test_output.get("tests_failed", 0)}

## Errors Reported
```
{chr(10).join(errors[:20])}
```

## Tester's Recommendations
```
{chr(10).join(recommendations[:10])}
```

## Test Logs (last 10000 chars)
```
{logs}
```

---

## Your Task

1. **Read the test files** to understand how tests are written:
   - `{connector_dir}/tests/test_results.json` (if exists)
   - `{connector_dir}/tests/conftest.py`
   - `{connector_dir}/tests/test_*.py` files

2. **Read the connector source** to understand the actual implementation:
   - `{connector_dir}/src/config.py` - Configuration and validation
   - `{connector_dir}/src/connector.py` - Main connector class
   - `{connector_dir}/src/auth.py` - Authentication

3. **Trace the errors** to find the ROOT CAUSE:
   - Follow stack traces
   - Check if error is in test file or connector file
   - Identify if it's a test bug or code bug

4. **Make your decision**:
   - INVALID: Tests are wrong -> feedback to Tester
   - VALID_FAIL: Code is wrong -> feedback to Generator
   - VALID_PASS: Tests pass (shouldn't happen here)

## Output

Provide your analysis as JSON with:
- decision: "INVALID" | "VALID_FAIL" | "VALID_PASS"
- confidence: 0.0-1.0
- analysis: Detailed explanation
- root_cause_location: "tests" | "connector"
- test_issues: List of test problems (for INVALID decision)
- code_issues: List of code problems (for VALID_FAIL decision)
- recommendations: Specific fixes for the next agent

Start by reading the relevant files, then provide your JSON analysis.
"""
        return prompt

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the analysis response from Claude."""
        try:
            # Find JSON block in response
            json_start = response.rfind("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                # Try to find the complete JSON object
                bracket_count = 0
                json_str = ""
                in_string = False
                escape_next = False

                for i, char in enumerate(response[json_start:]):
                    json_str += char

                    if escape_next:
                        escape_next = False
                        continue

                    if char == "\\":
                        escape_next = True
                        continue

                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue

                    if not in_string:
                        if char == "{":
                            bracket_count += 1
                        elif char == "}":
                            bracket_count -= 1
                            if bracket_count == 0:
                                break

                data = json.loads(json_str)

                # Normalize decision
                decision = data.get("decision", "VALID_FAIL").upper()
                if decision not in ["INVALID", "VALID_FAIL", "VALID_PASS"]:
                    decision = "VALID_FAIL"

                return {
                    "decision": decision,
                    "confidence": float(data.get("confidence", 0.8)),
                    "analysis": data.get("analysis", ""),
                    "root_cause_location": data.get("root_cause_location", "unknown"),
                    "test_issues": data.get("test_issues", []),
                    "code_issues": data.get("code_issues", []),
                    "recommendations": data.get("recommendations", []),
                    "success": True,
                }

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"[TEST_REVIEWER] Failed to parse JSON: {e}")

        # Fallback: analyze response text for decision indicators
        response_lower = response.lower()

        # Check for mock-related errors first (these are TEST issues, not code bugs)
        mock_error_indicators = [
            "cannot unpack non-iterable mock",
            "mock object",
            "magicmock",
            "mock is not callable",
            "mock has no attribute",
            "patch at wrong",
            "mock configuration",
            "mock chain",
        ]

        if any(indicator in response_lower for indicator in mock_error_indicators):
            decision = "INVALID"
            test_issues = ["Mock configuration error detected - tests need to be fixed"]
            code_issues = []
        elif "invalid" in response_lower and "test" in response_lower:
            decision = "INVALID"
            test_issues = ["Could not parse detailed issues - tests may be invalid"]
            code_issues = []
        elif "pydantic" in response_lower or "discriminator" in response_lower:
            decision = "VALID_FAIL"
            test_issues = []
            code_issues = ["Pydantic validation error detected in connector code"]
        else:
            decision = "VALID_FAIL"
            test_issues = []
            code_issues = ["Tests failed - see logs for details"]

        return {
            "decision": decision,
            "confidence": 0.6,
            "analysis": response[:1000],
            "root_cause_location": "tests" if decision == "INVALID" else "connector",
            "test_issues": test_issues,
            "code_issues": code_issues,
            "recommendations": ["Manual review recommended - could not fully parse analysis"],
            "success": True,
        }

    def _create_pass_result(self, duration: float) -> Dict[str, Any]:
        """Create result for tests that passed."""
        return {
            "decision": "VALID_PASS",
            "confidence": 1.0,
            "analysis": "Tests passed successfully",
            "root_cause_location": "none",
            "test_issues": [],
            "code_issues": [],
            "recommendations": [],
            "success": True,
            "duration_seconds": duration,
            "tokens_used": 0,
        }

    def _create_error_result(self, error: str, duration: float) -> Dict[str, Any]:
        """Create result for analysis errors."""
        return {
            "decision": "VALID_FAIL",  # Default to fixing code on error
            "confidence": 0.5,
            "analysis": f"Error during analysis: {error}",
            "root_cause_location": "unknown",
            "test_issues": [],
            "code_issues": [error],
            "recommendations": ["Fix error and retry"],
            "success": False,
            "error": error,
            "duration_seconds": duration,
            "tokens_used": 0,
        }
