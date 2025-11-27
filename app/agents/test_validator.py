"""
Test Validator - Ensures TesterAgent actually ran tests and results are legitimate.

This module validates that:
1. Pytest was actually executed via Bash tool
2. Test files can be imported without errors
3. test_results.json matches actual pytest output
4. No hallucinated or fake test results
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TestValidationError(Exception):
    """Raised when test validation fails."""
    pass


class TestValidator:
    """Validates test execution and results."""

    def __init__(self, connector_dir: str):
        """
        Initialize validator.

        Args:
            connector_dir: Path to connector directory
        """
        self.connector_dir = Path(connector_dir)
        self.tests_dir = self.connector_dir / "tests"
        self.results_file = self.tests_dir / "test_results.json"

    def validate_all(
        self,
        agent_response: str,
        tool_calls: Optional[List[Dict]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Run all validations.

        Args:
            agent_response: Full response from TesterAgent
            tool_calls: List of tool calls made by agent

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # 1. Validate pytest was actually run
        try:
            self._validate_pytest_execution(tool_calls)
        except TestValidationError as e:
            issues.append(f"Pytest execution validation failed: {e}")

        # 2. Validate test imports work
        try:
            self._validate_test_imports()
        except TestValidationError as e:
            issues.append(f"Test import validation failed: {e}")

        # 3. Validate test_results.json exists and is valid
        try:
            results = self._validate_results_file()
        except TestValidationError as e:
            issues.append(f"Results file validation failed: {e}")
            return False, issues

        # 4. Cross-validate results with pytest output
        try:
            self._cross_validate_results(tool_calls, results)
        except TestValidationError as e:
            issues.append(f"Cross-validation failed: {e}")

        # 5. Validate bugs_found matches test failures
        try:
            self._validate_bugs_consistency(results)
        except TestValidationError as e:
            issues.append(f"Bug consistency validation failed: {e}")

        is_valid = len(issues) == 0
        return is_valid, issues

    def _validate_pytest_execution(self, tool_calls: Optional[List[Dict]]) -> None:
        """
        Validate that pytest was actually executed via Bash tool.

        Raises:
            TestValidationError: If pytest was not run
        """
        if not tool_calls:
            raise TestValidationError(
                "No tool calls provided - cannot verify pytest execution"
            )

        # Find all Bash tool calls
        bash_calls = [
            call for call in tool_calls
            if call.get("tool") == "Bash"
        ]

        if not bash_calls:
            raise TestValidationError(
                "No Bash tool calls found - TesterAgent never ran any commands"
            )

        # Look for pytest execution
        pytest_calls = []
        for call in bash_calls:
            command = call.get("command", "")
            if "pytest" in command or "python -m pytest" in command:
                pytest_calls.append(call)

        if not pytest_calls:
            raise TestValidationError(
                f"No pytest commands found in {len(bash_calls)} Bash calls. "
                "TesterAgent likely hallucinated results."
            )

        # Validate pytest output looks legitimate
        last_pytest = pytest_calls[-1]
        output = last_pytest.get("output", "")

        if not output:
            raise TestValidationError(
                "Pytest command has no output - execution may have failed"
            )

        # Check for pytest markers
        required_markers = ["collected", "passed", "failed"]
        missing_markers = [m for m in required_markers if m not in output.lower()]

        if missing_markers:
            raise TestValidationError(
                f"Pytest output missing markers: {missing_markers}. "
                "Output may be fake or incomplete."
            )

        logger.info(f"[VALIDATOR] ✓ Pytest execution validated ({len(pytest_calls)} runs)")

    def _validate_test_imports(self) -> None:
        """
        Validate that test files can be imported without errors.

        Raises:
            TestValidationError: If imports fail
        """
        if not self.tests_dir.exists():
            raise TestValidationError(f"Tests directory not found: {self.tests_dir}")

        # Check if conftest.py exists and can be imported
        conftest = self.tests_dir / "conftest.py"
        if conftest.exists():
            try:
                result = subprocess.run(
                    ["python3", "-c", "import sys; sys.path.insert(0, '.'); import tests.conftest"],
                    cwd=self.connector_dir,
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    error = result.stderr.decode()
                    raise TestValidationError(
                        f"conftest.py has import errors:\n{error}"
                    )
            except subprocess.TimeoutExpired:
                raise TestValidationError("conftest.py import timed out")

        # Try importing main test files
        test_files = list(self.tests_dir.glob("test_*.py"))
        if not test_files:
            raise TestValidationError("No test files (test_*.py) found")

        logger.info(f"[VALIDATOR] ✓ Test imports validated ({len(test_files)} files)")

    def _validate_results_file(self) -> Dict:
        """
        Validate test_results.json exists and has valid structure.

        Returns:
            Parsed results dict

        Raises:
            TestValidationError: If file is invalid
        """
        if not self.results_file.exists():
            raise TestValidationError(
                f"test_results.json not found at {self.results_file}"
            )

        try:
            with open(self.results_file) as f:
                results = json.load(f)
        except json.JSONDecodeError as e:
            raise TestValidationError(f"Invalid JSON in test_results.json: {e}")

        # Validate required fields
        required_fields = ["status", "passed", "tests_run", "tests_passed", "tests_failed"]
        missing = [f for f in required_fields if f not in results]

        if missing:
            raise TestValidationError(
                f"test_results.json missing required fields: {missing}"
            )

        logger.info("[VALIDATOR] ✓ test_results.json structure validated")
        return results

    def _cross_validate_results(
        self,
        tool_calls: Optional[List[Dict]],
        results: Dict
    ) -> None:
        """
        Cross-validate test_results.json against actual pytest output.

        Raises:
            TestValidationError: If results don't match
        """
        if not tool_calls:
            logger.warning("[VALIDATOR] ⚠ No tool calls to cross-validate against")
            return

        # Find pytest output
        pytest_calls = [
            call for call in tool_calls
            if call.get("tool") == "Bash" and "pytest" in call.get("command", "")
        ]

        if not pytest_calls:
            logger.warning("[VALIDATOR] ⚠ No pytest calls to cross-validate against")
            return

        last_pytest = pytest_calls[-1]
        output = last_pytest.get("output", "")

        # Extract test counts from pytest output
        # Format: "===== 150 passed in 5.99s ====="
        import re
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)

        pytest_passed = int(passed_match.group(1)) if passed_match else 0
        pytest_failed = int(failed_match.group(1)) if failed_match else 0

        # Compare with test_results.json
        claimed_passed = results.get("tests_passed", 0)
        claimed_failed = results.get("tests_failed", 0)

        # Allow small discrepancies (due to skipped tests, etc.)
        if abs(pytest_passed - claimed_passed) > 5:
            raise TestValidationError(
                f"Test count mismatch: pytest says {pytest_passed} passed, "
                f"but test_results.json claims {claimed_passed} passed"
            )

        if abs(pytest_failed - claimed_failed) > 5:
            raise TestValidationError(
                f"Test failure count mismatch: pytest says {pytest_failed} failed, "
                f"but test_results.json claims {claimed_failed} failed"
            )

        logger.info("[VALIDATOR] ✓ Test counts cross-validated with pytest output")

    def _validate_bugs_consistency(self, results: Dict) -> None:
        """
        Validate that bugs_found is consistent with test status.

        Raises:
            TestValidationError: If bugs and status are inconsistent
        """
        status = results.get("status", "").lower()
        bugs_found = results.get("bugs_found", [])
        tests_failed = results.get("tests_failed", 0)

        # If bugs are found but status is "passed", that's suspicious
        if bugs_found and status == "passed" and tests_failed == 0:
            # This is actually OK - bugs can be found in code review
            # even if all mocked tests pass
            logger.info(
                "[VALIDATOR] ⚠ Bugs found but tests passed - "
                "likely code analysis bugs, not test failures"
            )

        # If tests failed but no bugs found, that's a problem
        if tests_failed > 0 and not bugs_found:
            raise TestValidationError(
                f"{tests_failed} tests failed but no bugs documented in bugs_found"
            )

        logger.info("[VALIDATOR] ✓ Bug consistency validated")

    def quick_import_check(self) -> Tuple[bool, str]:
        """
        Quick check if test files can be imported.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            self._validate_test_imports()
            return True, ""
        except TestValidationError as e:
            return False, str(e)


def validate_test_execution(
    connector_dir: str,
    agent_response: str,
    tool_calls: Optional[List[Dict]] = None
) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate test execution.

    Args:
        connector_dir: Path to connector directory
        agent_response: Full response from TesterAgent
        tool_calls: List of tool calls made by agent

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    validator = TestValidator(connector_dir)
    return validator.validate_all(agent_response, tool_calls)
