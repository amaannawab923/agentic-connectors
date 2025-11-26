"""QA/Tester agent for validating generated connector code with mock servers.

Uses Claude Agent SDK to:
1. Search online for testing best practices for the specific API
2. Read connector documentation (IMPLEMENTATION.md) and source code
3. Create a mock server that mimics the target API
4. Test the connector against the mock server
5. Report detailed test results with specific error messages

Supports three modes:
- GENERATE: First run - create tests from scratch (default)
- RERUN: Coming from Generator after fix - just re-run existing tests
- FIX: Coming from TestReviewer (INVALID) - fix tests based on feedback, then run
"""

import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions

from .base import BaseAgent
from ..models.enums import AgentType, TestStatus
from ..models.schemas import AgentResult, TestResult

logger = logging.getLogger(__name__)


class TesterMode(str, Enum):
    """Operating modes for the TesterAgent."""
    GENERATE = "generate"  # First run: create tests from scratch
    RERUN = "rerun"        # From Generator: just re-run existing tests
    FIX = "fix"            # From TestReviewer (INVALID): fix tests, then run


class TesterAgent(BaseAgent):
    """QA Agent that tests generated connectors using mock servers.

    This agent uses Claude Agent SDK with web search to:
    - Research testing patterns for the specific API online
    - Read connector source code to understand exact interfaces
    - Generate accurate mock servers based on API documentation
    - Create comprehensive test suites
    - Run tests and report detailed results

    Supports three operating modes:
    - GENERATE: First run, create tests from scratch
    - RERUN: Re-run existing tests (after Generator fix)
    - FIX: Fix tests based on feedback (after TestReviewer INVALID)
    """

    agent_type = AgentType.TESTER

    # System prompt for GENERATE mode (full test creation)
    system_prompt_generate = """You are an expert QA automation engineer specializing in testing data connectors.
Your task is to create comprehensive tests that will CATCH BUGS in the generated connector code.

## YOUR MISSION
Find bugs. Break things. The connector was auto-generated and likely has issues.
Your job is to discover what's wrong so it can be fixed.

## ⚠️ CRITICAL: ALWAYS WRITE test_results.json AT THE END ⚠️

No matter what happens (tests pass OR fail), you MUST write `tests/test_results.json` as your FINAL action.
The system reads results ONLY from this file. Without it, your work is lost.

```json
{
    "status": "passed|failed",
    "passed": true|false,
    "tests_run": 7,
    "tests_passed": 5,
    "tests_failed": 2,
    "syntax_errors": [],
    "import_errors": [],
    "runtime_errors": [],
    "test_details": [
        {"name": "test_config_validation", "status": "passed", "error": null},
        {"name": "test_connection_check", "status": "failed", "error": "Pydantic discriminator error..."}
    ],
    "recommendations": ["Fix Pydantic Literal type for discriminator"],
    "logs": "full pytest output..."
}
```

## WORKFLOW

### Phase 1: Research (Use WebSearch)
Search for testing patterns specific to this API:
- "{API_NAME} python mock testing"
- "{API_NAME} pytest httpretty mock"
- "airbyte source-{connector} unit tests github"

### Phase 2: Understand the Connector (Read Source Code)
BEFORE writing any tests, you MUST read:
1. `IMPLEMENTATION.md` - Understand what the connector does
2. `src/connector.py` - Find the exact class name and method signatures
3. `src/config.py` - Understand configuration structure and validation
4. `src/auth.py` - Understand authentication requirements
5. `src/client.py` - Understand API interactions to mock
6. `src/streams.py` - Understand data stream definitions

### Phase 3: Setup Environment
```bash
cd {connector_dir}
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov httpretty responses
```

### Phase 4: Validate Syntax First (Quick Wins)
Before complex tests, check basic syntax:
```bash
python3 -m py_compile src/connector.py
python3 -m py_compile src/config.py
python3 -m py_compile src/auth.py
python3 -m py_compile src/client.py
python3 -m py_compile src/streams.py
```

### Phase 5: Test Imports
```python
# test_imports.py
import sys
sys.path.insert(0, 'src')

try:
    from connector import *
    print("connector.py: OK")
except Exception as e:
    print(f"connector.py: FAILED - {e}")

# Repeat for each module
```

### Phase 6: Create Test Suite

#### Directory Structure:
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures with mocks
├── test_syntax.py           # Syntax validation
├── test_imports.py          # Import validation
├── test_config.py           # Configuration tests
├── test_connection.py       # Connection check tests
├── test_discovery.py        # Schema discovery tests
├── test_read.py             # Data reading tests
├── test_results.json        # REQUIRED: Test results output
└── pytest.ini
```

#### conftest.py Template (CRITICAL - Mock Setup):
```python
import pytest
import httpretty
import json
import re
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Generate valid RSA key for Google Service Account tests
@pytest.fixture(scope="session", autouse=True)
def generate_test_key():
    import subprocess
    subprocess.run([
        'openssl', 'genpkey', '-algorithm', 'RSA',
        '-out', '/tmp/test_private_key.pem',
        '-pkeyopt', 'rsa_keygen_bits:2048'
    ], capture_output=True)

    with open('/tmp/test_private_key.pem', 'r') as f:
        return f.read()

@pytest.fixture
def valid_private_key():
    try:
        with open('/tmp/test_private_key.pem', 'r') as f:
            return f.read()
    except:
        return "-----BEGIN PRIVATE KEY-----\\nMIIE...fake...\\n-----END PRIVATE KEY-----"

@pytest.fixture
def mock_oauth_token():
    return {
        "access_token": "mock-access-token-12345",
        "token_type": "Bearer",
        "expires_in": 3600
    }

@pytest.fixture
def mock_api():
    httpretty.enable(verbose=True, allow_net_connect=False)

    # Mock OAuth2 token endpoint (Google)
    httpretty.register_uri(
        httpretty.POST,
        "https://oauth2.googleapis.com/token",
        body=json.dumps({
            "access_token": "mock-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }),
        content_type="application/json"
    )

    # ADD API-SPECIFIC MOCKS HERE based on what you learned from source code

    yield httpretty

    httpretty.disable()
    httpretty.reset()
```

### Phase 7: Run Tests
```bash
source venv/bin/activate
python -m pytest tests/ -v --tb=long 2>&1 | tee pytest_output.txt
```

### Phase 8: WRITE RESULTS (MANDATORY)
After pytest completes, IMMEDIATELY use the Write tool to create `tests/test_results.json`.
Parse the pytest output and create a detailed report.

## KEY TESTING PATTERNS

### For Google APIs (Sheets, Drive, etc.):
- Mock `https://oauth2.googleapis.com/token` for OAuth
- Mock `https://sheets.googleapis.com/v4/spreadsheets/*` for API calls
- Use real RSA keys (generate with openssl) - Google validates key format
- Use httpretty with regex patterns for URL matching

### For REST APIs with API Keys:
- No OAuth mock needed
- Just mock the API endpoints
- Pass API key in headers or query params

### For Pydantic Validation Issues:
- Test that invalid configs raise ValidationError
- Test discriminator fields use Literal types
- Test required vs optional fields

## COMMON BUGS TO LOOK FOR

1. **Pydantic Discriminator Issues**: `auth_type` field must be `Literal["value"]` not `Enum`
2. **Import Errors**: Circular imports, missing dependencies
3. **Type Errors**: Wrong type hints, incompatible types
4. **Runtime Errors**: Unhandled exceptions, None access
5. **API Mismatch**: Wrong endpoint URLs, incorrect request format
6. **Authentication Issues**: Token refresh logic, credential validation

## REMEMBER
- Read the source code FIRST before writing tests
- Use WebSearch to find API-specific mocking patterns
- Generate real RSA keys for Google APIs
- ALWAYS write test_results.json at the end
- Include specific error messages so the generator can fix them
"""

    # System prompt for RERUN mode (just re-run existing tests)
    system_prompt_rerun = """You are a QA automation engineer responsible for re-running existing tests.

## YOUR MISSION
The connector code was just fixed by the Generator agent. Your job is simple:
1. Re-run the existing tests
2. Report the results

DO NOT modify any test files. DO NOT create new tests. Just run what exists.

## ⚠️ CRITICAL: ALWAYS WRITE test_results.json AT THE END ⚠️

No matter what happens (tests pass OR fail), you MUST write `tests/test_results.json` as your FINAL action.

## WORKFLOW

### Step 1: Setup Environment
```bash
cd {connector_dir}
source venv/bin/activate
# If venv doesn't exist, create it:
# python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt pytest httpretty
```

### Step 2: Generate RSA Key (if needed for Google APIs)
```bash
if [ ! -f /tmp/test_private_key.pem ]; then
    openssl genpkey -algorithm RSA -out /tmp/test_private_key.pem -pkeyopt rsa_keygen_bits:2048
fi
```

### Step 3: Run Tests
```bash
python -m pytest tests/ -v --tb=long 2>&1
```

### Step 4: WRITE RESULTS (MANDATORY)
Parse the pytest output and write `tests/test_results.json`:

```json
{
    "status": "passed|failed",
    "passed": true|false,
    "tests_run": 7,
    "tests_passed": 7,
    "tests_failed": 0,
    "syntax_errors": [],
    "import_errors": [],
    "runtime_errors": [],
    "test_details": [...],
    "recommendations": [],
    "logs": "full pytest output..."
}
```

## REMEMBER
- DO NOT modify test files
- DO NOT create new tests
- JUST run existing tests and report results
- ALWAYS write test_results.json
"""

    # System prompt for FIX mode (fix tests based on feedback)
    system_prompt_fix = """You are an expert QA automation engineer specializing in fixing test code.

## YOUR MISSION
The TestReviewer agent determined that the TESTS are wrong, not the connector code.
Your job is to FIX the test code so it correctly tests the connector.

## IMPORTANT CONTEXT
- The connector code is CORRECT - do not suggest changes to it
- The tests have bugs or incorrect assumptions
- Fix the tests to accurately test the connector behavior

## ⚠️ CRITICAL: ALWAYS WRITE test_results.json AT THE END ⚠️

After fixing and running tests, you MUST write `tests/test_results.json`.

## WORKFLOW

### Step 1: Read the TestReviewer Feedback
Understand WHY the tests were marked as invalid:
- Are the mocks incorrect?
- Are the assertions testing wrong behavior?
- Are there import issues in the tests?
- Are there wrong assumptions about the API?

### Step 2: Read the Connector Source Code
Understand what the connector ACTUALLY does:
- `src/connector.py` - Main connector class
- `src/config.py` - Configuration structure
- `src/client.py` - API client behavior
- `src/streams.py` - Stream definitions

### Step 3: Fix the Test Files
Use Edit tool to fix issues in:
- `tests/conftest.py` - Fix mock setup
- `tests/test_*.py` - Fix test assertions and expectations

### Step 4: Run Tests
```bash
cd {connector_dir}
source venv/bin/activate
python -m pytest tests/ -v --tb=long 2>&1
```

### Step 5: Iterate (Max 3 Attempts)
If tests still fail after fixes:
1. Analyze the new errors
2. Fix the issues
3. Re-run tests
4. Repeat up to 3 times

### Step 6: WRITE RESULTS (MANDATORY)
Write `tests/test_results.json` with detailed results.

## COMMON TEST ISSUES TO FIX

1. **Wrong Mock URLs**: API endpoint patterns don't match actual client calls
2. **Wrong Mock Responses**: Mock data structure doesn't match API format
3. **Wrong Assertions**: Testing wrong behavior or wrong return types
4. **Missing Mocks**: Some API calls not mocked, causing network errors
5. **Wrong Import Paths**: Tests importing from wrong module paths
6. **Configuration Mismatch**: Test config doesn't match actual config schema

## REMEMBER
- The connector code is CORRECT
- Fix the TESTS to match the connector behavior
- Run tests after each fix to verify
- Max 3 fix attempts
- ALWAYS write test_results.json
"""

    async def execute(
        self,
        connector_dir: str,
        connector_name: str,
        connector_type: str = "source",
        implementation_doc: Optional[str] = None,
        generated_code: Optional[Dict[str, str]] = None,
        mode: TesterMode = TesterMode.GENERATE,
        test_issues: Optional[List[str]] = None,
        fix_feedback: Optional[List[str]] = None,
    ) -> AgentResult:
        """Execute the QA/Tester agent.

        Args:
            connector_dir: Directory containing the connector code.
            connector_name: Name of the connector (e.g., "Google Sheets").
            connector_type: Type of connector (source/destination).
            implementation_doc: Optional IMPLEMENTATION.md content from state.
            generated_code: Optional dict of generated files from state.
            mode: Operating mode (GENERATE, RERUN, or FIX).
            test_issues: List of test issues from TestReviewer (for FIX mode).
            fix_feedback: List of feedback items for fixing tests (for FIX mode).

        Returns:
            AgentResult with detailed test results.
        """
        start_time = time.time()
        self.reset_token_tracking()

        logger.info(f"[TESTER] Starting in {mode.value.upper()} mode")

        # Verify connector directory exists
        connector_path = Path(connector_dir)
        if not connector_path.exists():
            return self._create_result(
                success=False,
                error=f"Connector directory not found: {connector_dir}",
                duration_seconds=time.time() - start_time,
            )

        # Check if tests exist (required for RERUN and FIX modes)
        tests_dir = connector_path / "tests"
        tests_exist = tests_dir.exists() and any(tests_dir.glob("test_*.py"))

        if mode in (TesterMode.RERUN, TesterMode.FIX) and not tests_exist:
            logger.warning(f"[TESTER] Tests not found for {mode.value} mode, falling back to GENERATE mode")
            mode = TesterMode.GENERATE

        # Check for documentation files (only needed for GENERATE mode)
        impl_path = connector_path / "IMPLEMENTATION.md"
        readme_path = connector_path / "README.md"

        has_impl = impl_path.exists()
        has_readme = readme_path.exists()

        if mode == TesterMode.GENERATE and not has_impl and not has_readme and not implementation_doc:
            logger.warning("No documentation files found, will rely on source code analysis")

        # Set working directory to connector directory
        self.working_dir = connector_dir

        # Select system prompt based on mode
        if mode == TesterMode.GENERATE:
            system_prompt = self.system_prompt_generate
        elif mode == TesterMode.RERUN:
            system_prompt = self.system_prompt_rerun
        else:  # FIX mode
            system_prompt = self.system_prompt_fix

        # Build the appropriate prompt based on mode
        if mode == TesterMode.GENERATE:
            prompt = self._build_test_prompt(
                connector_dir=connector_dir,
                connector_name=connector_name,
                connector_type=connector_type,
                has_impl=has_impl,
                has_readme=has_readme,
                implementation_doc=implementation_doc,
                generated_code=generated_code,
            )
        elif mode == TesterMode.RERUN:
            prompt = self._build_rerun_prompt(
                connector_dir=connector_dir,
                connector_name=connector_name,
            )
        else:  # FIX mode
            prompt = self._build_fix_prompt(
                connector_dir=connector_dir,
                connector_name=connector_name,
                test_issues=test_issues or [],
                fix_feedback=fix_feedback or [],
            )

        try:
            # Stderr callback for debugging
            def log_stderr(msg):
                logger.info(f"[TESTER-SDK-STDERR] {msg}")

            # Determine tools based on mode
            if mode == TesterMode.RERUN:
                # RERUN only needs Bash to run tests and Write for results
                allowed_tools = ["Read", "Write", "Bash"]
                max_turns = 15  # Quick mode
            elif mode == TesterMode.FIX:
                # FIX needs Edit to fix tests
                allowed_tools = ["Read", "Write", "Edit", "Bash"]
                max_turns = 40  # Medium mode
            else:  # GENERATE
                # Full tools for test creation
                allowed_tools = ["Read", "Write", "Bash", "WebSearch", "WebFetch"]
                max_turns = 60  # Full mode

            # Create options
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                max_turns=max_turns,
                allowed_tools=allowed_tools,
                permission_mode="acceptEdits",
                cwd=connector_dir,
                stderr=log_stderr,
                include_partial_messages=True,
            )

            logger.info("=" * 60)
            logger.info(f"[TESTER] Starting QA tests for {connector_name}")
            logger.info(f"[TESTER] Mode: {mode.value.upper()}")
            logger.info(f"[TESTER] Connector directory: {connector_dir}")
            logger.info(f"[TESTER] Tests exist: {tests_exist}")
            if mode == TesterMode.GENERATE:
                logger.info(f"[TESTER] Has IMPLEMENTATION.md: {has_impl}")
                logger.info(f"[TESTER] Has README.md: {has_readme}")
            logger.info(f"[TESTER] Tools: {allowed_tools}")
            logger.info(f"[TESTER] Max turns: {max_turns}")
            logger.info("=" * 60)

            # Stream the test response
            logger.info("[TESTER] Sending prompt to Claude Agent SDK...")
            response = await self._stream_response(prompt, options)

            logger.info("=" * 60)
            logger.info("[TESTER] Agent execution completed, parsing results...")
            logger.info(f"[TESTER] Response length: {len(response)} chars")

            # Try to read results from file first (most reliable)
            test_result = self._read_results_file(connector_dir)

            if test_result is not None:
                logger.info("[TESTER] Successfully read results from test_results.json")
            else:
                # Try pytest cache as second fallback
                logger.info("[TESTER] No test_results.json found, trying pytest cache...")
                test_result = self._read_pytest_cache(connector_dir)

                if test_result is not None:
                    logger.info("[TESTER] Successfully read results from pytest cache")
                else:
                    # Final fallback: parse response text
                    logger.info("[TESTER] No pytest cache found, parsing response text...")
                    test_result = self._parse_test_results(response)

            duration = time.time() - start_time
            test_result.duration_seconds = duration

            logger.info("=" * 60)
            logger.info(f"[TESTER] QA TESTS COMPLETED")
            logger.info(f"[TESTER] Status: {test_result.status.value}")
            logger.info(f"[TESTER] Passed: {test_result.passed}")
            logger.info(f"[TESTER] Tests passed: {test_result.unit_tests_passed}")
            logger.info(f"[TESTER] Tests failed: {test_result.unit_tests_failed}")
            logger.info(f"[TESTER] Connection test: {test_result.connection_test_passed}")
            logger.info(f"[TESTER] Data fetch test: {test_result.data_fetch_test_passed}")
            logger.info(f"[TESTER] Records read: {test_result.sample_records_count}")
            logger.info(f"[TESTER] Duration: {duration:.1f}s")
            if test_result.errors:
                logger.info(f"[TESTER] Errors: {test_result.errors}")
            logger.info("=" * 60)

            return AgentResult(
                agent=self.agent_type,
                success=test_result.passed,
                output=json.dumps(test_result.model_dump()),
                error="; ".join(test_result.errors) if test_result.errors else None,
                duration_seconds=duration,
                tokens_used=self.total_tokens_used,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.exception(f"[TESTER] QA agent failed after {duration:.1f}s")
            logger.error(f"[TESTER] Error: {str(e)}")
            return self._create_result(
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    def _build_test_prompt(
        self,
        connector_dir: str,
        connector_name: str,
        connector_type: str,
        has_impl: bool,
        has_readme: bool,
        implementation_doc: Optional[str] = None,
        generated_code: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build the test prompt for the QA agent."""

        # Create API-specific search terms
        api_name = connector_name.replace("-", " ").title()
        connector_slug = connector_name.lower().replace(" ", "-")

        prompt = f"""# QA Testing Task: {connector_name} {connector_type.title()} Connector

## Connector Location
`{connector_dir}`

## YOUR MISSION
Find bugs in this auto-generated connector. It likely has issues that need to be fixed.
Your test results will be used to improve the code.

---

## Phase 1: Research Testing Patterns (WebSearch)

Use WebSearch to find testing patterns for this specific API:

1. Search: "{api_name} API python mock testing httpretty"
2. Search: "airbyte source-{connector_slug} test github"
3. Search: "{api_name} API authentication mock pytest"

Learn:
- How to mock this specific API's endpoints
- What authentication flow to simulate
- Common edge cases and error responses

---

## Phase 2: Read Source Code (CRITICAL)

Before writing ANY tests, read these files to understand the actual implementation:

"""
        if has_impl:
            prompt += f"""
### Read IMPLEMENTATION.md first:
`{connector_dir}/IMPLEMENTATION.md`
"""

        if has_readme:
            prompt += f"""
### Read README.md:
`{connector_dir}/README.md`
"""

        prompt += f"""
### Then read ALL source files:
- `{connector_dir}/src/__init__.py`
- `{connector_dir}/src/connector.py` - **CRITICAL: Find exact class name and methods**
- `{connector_dir}/src/config.py` - **CRITICAL: Find config structure and validation**
- `{connector_dir}/src/auth.py` - **Find authentication classes**
- `{connector_dir}/src/client.py` - **Find API endpoints to mock**
- `{connector_dir}/src/streams.py` - **Find stream definitions**
- `{connector_dir}/src/utils.py`
- `{connector_dir}/requirements.txt`

**IMPORTANT**: Note the EXACT class names, method signatures, and import paths.
The tests must match what's actually in the code.

---

## Phase 3: Setup Environment

```bash
cd {connector_dir}
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov httpretty responses
```

For Google APIs, generate a valid RSA key:
```bash
openssl genpkey -algorithm RSA -out /tmp/test_private_key.pem -pkeyopt rsa_keygen_bits:2048
```

---

## Phase 4: Create Test Suite

Create the following test structure in `{connector_dir}/tests/`:

### 4.1 `tests/__init__.py`
```python
\"\"\"Test suite for {connector_name} connector.\"\"\"
```

### 4.2 `tests/pytest.ini`
```ini
[pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=long
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### 4.3 `tests/conftest.py` (CRITICAL - Setup Mocks)
Create fixtures that:
- Load the RSA key from /tmp/test_private_key.pem
- Setup httpretty mocks for OAuth2 token endpoint
- Setup httpretty mocks for the API endpoints
- Create valid test configuration
- Create connector instance

**Use the actual class names and config structure from the source code!**

### 4.4 `tests/test_syntax.py`
Validate Python syntax of all source files.

### 4.5 `tests/test_imports.py`
Test that all modules can be imported without errors.

### 4.6 `tests/test_config.py`
Test configuration validation:
- Valid config is accepted
- Missing required fields raise errors
- Invalid field types raise errors

### 4.7 `tests/test_connection.py`
Test connection checking with mocked API.

### 4.8 `tests/test_discovery.py`
Test schema discovery with mocked API.

### 4.9 `tests/test_read.py`
Test data reading with mocked API.

---

## Phase 5: Run Tests

```bash
source venv/bin/activate
cd {connector_dir}
python -m pytest tests/ -v --tb=long 2>&1
```

---

## Phase 6: WRITE RESULTS (MANDATORY FINAL STEP)

**You MUST write `{connector_dir}/tests/test_results.json` using the Write tool.**

Parse the pytest output and create this JSON:

```json
{{
    "status": "passed|failed",
    "passed": true|false,
    "tests_run": 7,
    "tests_passed": 5,
    "tests_failed": 2,
    "syntax_errors": ["src/config.py:25: SyntaxError: ..."],
    "import_errors": ["Cannot import GoogleSheetsConfig: Pydantic error..."],
    "runtime_errors": ["test_connection: AttributeError..."],
    "test_details": [
        {{"name": "test_syntax_validation", "status": "passed", "error": null}},
        {{"name": "test_config_validation", "status": "failed", "error": "PydanticUserError: Model needs Literal type"}}
    ],
    "recommendations": [
        "Fix auth_type field to use Literal['service_account'] instead of Enum default",
        "Add missing import for typing.Literal in config.py"
    ],
    "logs": "Full pytest output here..."
}}
```

**Include SPECIFIC error messages and actionable recommendations.**
The generator agent will use these to fix the code.

---

## IMPORTANT REMINDERS

1. **READ SOURCE CODE FIRST** - Tests must match actual implementation
2. **USE WEBSEARCH** - Find API-specific mocking patterns
3. **MOCK ALL HTTP CALLS** - Use httpretty with regex patterns
4. **GENERATE RSA KEY** - Google APIs validate key format
5. **WRITE test_results.json** - This is how results are captured
6. **BE SPECIFIC** - Include exact error messages for fixing

Begin testing now. Research, read code, create tests, run them, and write results.
"""
        return prompt

    def _build_rerun_prompt(
        self,
        connector_dir: str,
        connector_name: str,
    ) -> str:
        """Build prompt for RERUN mode - just run existing tests."""

        prompt = f"""# Re-Run Tests: {connector_name} Connector

## Connector Location
`{connector_dir}`

## YOUR TASK
The connector code was just fixed by the Generator agent. Simply re-run the existing tests and report results.

**DO NOT modify any test files. DO NOT create new tests. Just run what exists.**

---

## Step 1: Setup Environment

```bash
cd {connector_dir}

# Activate virtual environment (create if doesn't exist)
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pytest httpretty
fi
```

## Step 2: Generate RSA Key (if needed)

```bash
if [ ! -f /tmp/test_private_key.pem ]; then
    openssl genpkey -algorithm RSA -out /tmp/test_private_key.pem -pkeyopt rsa_keygen_bits:2048
fi
```

## Step 3: Run Tests

```bash
python -m pytest tests/ -v --tb=long 2>&1
```

## Step 4: WRITE RESULTS (MANDATORY)

Parse the pytest output and write `{connector_dir}/tests/test_results.json`:

```json
{{
    "status": "passed|failed",
    "passed": true|false,
    "tests_run": <count>,
    "tests_passed": <count>,
    "tests_failed": <count>,
    "syntax_errors": [],
    "import_errors": [],
    "runtime_errors": [],
    "test_details": [
        {{"name": "test_name", "status": "passed|failed", "error": null|"error message"}}
    ],
    "recommendations": [],
    "logs": "full pytest output..."
}}
```

---

**REMEMBER**:
- DO NOT modify test files
- DO NOT create new tests
- JUST run existing tests
- ALWAYS write test_results.json

Begin now. Run the tests and write results.
"""
        return prompt

    def _build_fix_prompt(
        self,
        connector_dir: str,
        connector_name: str,
        test_issues: List[str],
        fix_feedback: List[str],
    ) -> str:
        """Build prompt for FIX mode - fix tests based on feedback."""

        # Format the issues and feedback
        issues_text = "\n".join(f"- {issue}" for issue in test_issues) if test_issues else "No specific issues provided"
        feedback_text = "\n".join(f"- {fb}" for fb in fix_feedback) if fix_feedback else "No specific feedback provided"

        prompt = f"""# Fix Tests: {connector_name} Connector

## Connector Location
`{connector_dir}`

## YOUR TASK
The TestReviewer agent determined that the TESTS are wrong, not the connector code.
Your job is to FIX the test code so it correctly tests the connector.

**IMPORTANT**: The connector code is CORRECT. Do not modify connector source files.
Only fix the test files.

---

## Test Issues Identified

{issues_text}

## Feedback from TestReviewer

{feedback_text}

---

## Step 1: Read the Connector Source Code

Understand what the connector ACTUALLY does (so you can fix tests to match):

- `{connector_dir}/src/connector.py` - Main connector class
- `{connector_dir}/src/config.py` - Configuration structure
- `{connector_dir}/src/client.py` - API client behavior
- `{connector_dir}/src/auth.py` - Authentication handling
- `{connector_dir}/src/streams.py` - Stream definitions

## Step 2: Read and Analyze Test Files

Read the existing tests to understand what's wrong:

- `{connector_dir}/tests/conftest.py` - Mock setup and fixtures
- `{connector_dir}/tests/test_*.py` - Test files

## Step 3: Fix the Test Files

Based on the issues identified, fix the tests using the Edit tool:

Common fixes:
1. **Fix Mock URLs**: Update httpretty URL patterns to match actual API calls
2. **Fix Mock Responses**: Update response data to match actual API format
3. **Fix Assertions**: Update assertions to test actual behavior
4. **Fix Imports**: Fix import paths to match actual module structure
5. **Fix Config**: Update test configurations to match actual schema

## Step 4: Setup Environment

```bash
cd {connector_dir}
source venv/bin/activate || (python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt pytest httpretty)
```

## Step 5: Generate RSA Key (if needed)

```bash
if [ ! -f /tmp/test_private_key.pem ]; then
    openssl genpkey -algorithm RSA -out /tmp/test_private_key.pem -pkeyopt rsa_keygen_bits:2048
fi
```

## Step 6: Run Tests

```bash
python -m pytest tests/ -v --tb=long 2>&1
```

## Step 7: Iterate (Max 3 Attempts)

If tests still fail:
1. Analyze the new errors
2. Fix the issues
3. Re-run tests
4. Repeat up to 3 times total

## Step 8: WRITE RESULTS (MANDATORY)

Write `{connector_dir}/tests/test_results.json`:

```json
{{
    "status": "passed|failed",
    "passed": true|false,
    "tests_run": <count>,
    "tests_passed": <count>,
    "tests_failed": <count>,
    "syntax_errors": [],
    "import_errors": [],
    "runtime_errors": [],
    "test_details": [...],
    "recommendations": [],
    "logs": "full pytest output..."
}}
```

---

**REMEMBER**:
- The connector code is CORRECT - only fix TESTS
- Use Edit tool to fix test files
- Run tests after each fix
- Max 3 fix attempts
- ALWAYS write test_results.json

Begin now. Fix the tests and verify they pass.
"""
        return prompt

    def _read_results_file(self, connector_dir: str) -> Optional[TestResult]:
        """Read test results from the JSON file written by the agent."""
        results_file = Path(connector_dir) / "tests" / "test_results.json"

        if not results_file.exists():
            logger.info(f"[TESTER] Results file not found: {results_file}")
            return None

        try:
            with open(results_file, 'r') as f:
                data = json.load(f)

            logger.info(f"[TESTER] Read test results from {results_file}")
            logger.debug(f"[TESTER] Results data: {data}")

            status_str = data.get("status", "error").lower()
            if status_str == "passed":
                status = TestStatus.PASSED
            elif status_str == "failed":
                status = TestStatus.FAILED
            else:
                status = TestStatus.ERROR

            # Extract errors from various fields
            errors = []
            errors.extend(data.get("errors", []))
            errors.extend(data.get("syntax_errors", []))
            errors.extend(data.get("import_errors", []))
            errors.extend(data.get("runtime_errors", []))

            # Add recommendations as errors for feedback
            recommendations = data.get("recommendations", [])
            if recommendations:
                errors.extend([f"RECOMMENDATION: {r}" for r in recommendations])

            return TestResult(
                status=status,
                passed=data.get("passed", False),
                unit_tests_passed=data.get("tests_passed", 0),
                unit_tests_failed=data.get("tests_failed", 0),
                connection_test_passed=data.get("connection_test_passed", False),
                data_fetch_test_passed=data.get("read_test_passed", False),
                sample_records_count=data.get("records_read", 0),
                errors=errors[:20],  # Limit to 20 errors
                logs=data.get("logs", ""),
                duration_seconds=0.0,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"[TESTER] Failed to parse results file: {e}")
            return None
        except Exception as e:
            logger.warning(f"[TESTER] Error reading results file: {e}")
            return None

    def _read_pytest_cache(self, connector_dir: str) -> Optional[TestResult]:
        """Fallback: Read test results from pytest cache files."""
        cache_dir = Path(connector_dir) / "tests" / ".pytest_cache" / "v" / "cache"
        nodeids_file = cache_dir / "nodeids"
        lastfailed_file = cache_dir / "lastfailed"

        if not nodeids_file.exists():
            logger.info(f"[TESTER] Pytest cache not found: {nodeids_file}")
            return None

        try:
            with open(nodeids_file, 'r') as f:
                nodeids = json.load(f)
            total_tests = len(nodeids)

            failed_tests = []
            if lastfailed_file.exists():
                with open(lastfailed_file, 'r') as f:
                    failed_tests = list(json.load(f).keys())

            failed_count = len(failed_tests)
            passed_count = total_tests - failed_count
            all_passed = failed_count == 0

            logger.info(f"[TESTER] Read pytest cache: {passed_count} passed, {failed_count} failed")

            connection_passed = any("test_connection" in t and t not in failed_tests for t in nodeids)
            discover_passed = any("test_discover" in t and t not in failed_tests for t in nodeids)
            read_passed = any("test_read" in t and t not in failed_tests for t in nodeids)

            return TestResult(
                status=TestStatus.PASSED if all_passed else TestStatus.FAILED,
                passed=all_passed,
                unit_tests_passed=passed_count,
                unit_tests_failed=failed_count,
                connection_test_passed=connection_passed,
                data_fetch_test_passed=read_passed,
                sample_records_count=0,
                errors=failed_tests[:10] if failed_tests else [],
                logs=f"Parsed from pytest cache: {passed_count} passed, {failed_count} failed",
                duration_seconds=0.0,
            )

        except Exception as e:
            logger.warning(f"[TESTER] Error reading pytest cache: {e}")
            return None

    def _parse_test_results(self, response: str) -> TestResult:
        """Parse test results from the response text."""
        import re
        logger.info("[TESTER] Parsing test results from response...")

        # Strategy 1: Try to find JSON in response
        try:
            json_pattern = r'\{[^{}]*"status"[^{}]*"passed"[^{}]*\}'
            json_matches = re.findall(json_pattern, response, re.DOTALL)

            if not json_matches:
                json_start = response.rfind('{"status"')
                if json_start == -1:
                    json_start = response.rfind('{')

                if json_start >= 0:
                    bracket_count = 0
                    json_str = ""
                    for char in response[json_start:]:
                        json_str += char
                        if char == "{":
                            bracket_count += 1
                        elif char == "}":
                            bracket_count -= 1
                            if bracket_count == 0:
                                break

                    if bracket_count == 0:
                        json_matches = [json_str]

            for json_str in reversed(json_matches):
                try:
                    data = json.loads(json_str)
                    if "status" in data or "passed" in data:
                        logger.info(f"[TESTER] Successfully parsed JSON from response")

                        status_str = data.get("status", "error").lower()
                        if status_str == "passed":
                            status = TestStatus.PASSED
                        elif status_str == "failed":
                            status = TestStatus.FAILED
                        else:
                            status = TestStatus.ERROR

                        errors = data.get("errors", [])
                        errors.extend(data.get("syntax_errors", []))
                        errors.extend(data.get("import_errors", []))
                        errors.extend(data.get("recommendations", []))

                        return TestResult(
                            status=status,
                            passed=data.get("passed", False),
                            unit_tests_passed=data.get("tests_passed", 0),
                            unit_tests_failed=data.get("tests_failed", 0),
                            connection_test_passed=data.get("connection_test_passed", False),
                            data_fetch_test_passed=data.get("read_test_passed", False),
                            sample_records_count=data.get("records_read", 0),
                            errors=errors[:20],
                            logs=data.get("logs", response[-2000:]),
                            duration_seconds=0.0,
                        )
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.warning(f"[TESTER] Failed to parse test results JSON: {e}")

        # Strategy 2: Parse pytest output format
        logger.info("[TESTER] Trying to parse pytest output format...")
        pytest_result = self._parse_pytest_output(response)
        if pytest_result:
            return pytest_result

        # Strategy 3: Fallback text analysis
        logger.info("[TESTER] Using fallback text analysis...")
        return self._parse_fallback(response)

    def _parse_pytest_output(self, response: str) -> Optional[TestResult]:
        """Parse pytest output format."""
        import re

        summary_pattern = r'(\d+)\s+passed(?:,\s*(\d+)\s+(?:failed|error))?.*?in\s+[\d.]+s'
        summary_match = re.search(summary_pattern, response, re.IGNORECASE)

        if summary_match:
            passed_count = int(summary_match.group(1))
            failed_count = int(summary_match.group(2)) if summary_match.group(2) else 0

            logger.info(f"[TESTER] Parsed pytest output: {passed_count} passed, {failed_count} failed")

            # Extract error messages
            errors = []
            error_pattern = r'(FAILED|ERROR)\s+(\S+)\s*-\s*(.+?)(?=\n(?:FAILED|ERROR|=====|\Z))'
            error_matches = re.findall(error_pattern, response, re.DOTALL)
            for match in error_matches[:10]:
                test_name = match[1]
                error_msg = match[2].strip()[:200]
                errors.append(f"{test_name}: {error_msg}")

            # Also look for specific error types
            pydantic_errors = re.findall(r'pydantic\.\w+Error[:\s]+([^\n]+)', response)
            errors.extend(pydantic_errors[:5])

            import_errors = re.findall(r'ImportError[:\s]+([^\n]+)', response)
            errors.extend(import_errors[:5])

            all_passed = failed_count == 0

            return TestResult(
                status=TestStatus.PASSED if all_passed else TestStatus.FAILED,
                passed=all_passed,
                unit_tests_passed=passed_count,
                unit_tests_failed=failed_count,
                connection_test_passed="test_connection" in response and "PASSED" in response,
                data_fetch_test_passed="test_read" in response and "PASSED" in response,
                sample_records_count=0,
                errors=errors if errors else ([f"{failed_count} test(s) failed"] if not all_passed else []),
                logs=response[-4000:],
                duration_seconds=0.0,
            )

        # Check for individual PASSED/FAILED markers
        passed_tests = len(re.findall(r'::\w+\s+PASSED', response))
        failed_tests = len(re.findall(r'::\w+\s+FAILED', response))

        if passed_tests > 0 or failed_tests > 0:
            logger.info(f"[TESTER] Parsed pytest markers: {passed_tests} passed, {failed_tests} failed")
            all_passed = failed_tests == 0

            return TestResult(
                status=TestStatus.PASSED if all_passed else TestStatus.FAILED,
                passed=all_passed,
                unit_tests_passed=passed_tests,
                unit_tests_failed=failed_tests,
                connection_test_passed=passed_tests > 0,
                data_fetch_test_passed=passed_tests >= 3,
                sample_records_count=0,
                errors=[] if all_passed else [f"{failed_tests} test(s) failed"],
                logs=response[-4000:],
                duration_seconds=0.0,
            )

        return None

    def _parse_fallback(self, response: str) -> TestResult:
        """Fallback text analysis with improved accuracy."""
        response_lower = response.lower()

        # Extract specific errors from response
        errors = []

        # Look for Pydantic errors (common issue)
        import re
        pydantic_errors = re.findall(r'pydantic[.\w]*error[:\s]+([^\n]+)', response_lower)
        errors.extend([f"Pydantic: {e[:100]}" for e in pydantic_errors[:5]])

        # Look for import errors
        import_errors = re.findall(r'importerror[:\s]+([^\n]+)', response_lower)
        errors.extend([f"Import: {e[:100]}" for e in import_errors[:5]])

        # Look for syntax errors
        syntax_errors = re.findall(r'syntaxerror[:\s]+([^\n]+)', response_lower)
        errors.extend([f"Syntax: {e[:100]}" for e in syntax_errors[:5]])

        # Strong indicators of success
        success_indicators = [
            "all tests passed",
            "tests passed successfully",
            '"passed": true',
            '"status": "passed"',
        ]

        # Strong indicators of failure
        failure_indicators = [
            "tests failed",
            '"passed": false',
            '"status": "failed"',
            "assertion error",
            "traceback (most recent call last)",
        ]

        passed = any(indicator in response_lower for indicator in success_indicators)
        has_failures = any(indicator in response_lower for indicator in failure_indicators)

        if passed and not has_failures and not errors:
            final_status = TestStatus.PASSED
            final_passed = True
        else:
            final_status = TestStatus.FAILED
            final_passed = False

        logger.info(f"[TESTER] Fallback analysis: passed={final_passed}, errors={len(errors)}")

        return TestResult(
            status=final_status,
            passed=final_passed,
            unit_tests_passed=0,
            unit_tests_failed=0,
            connection_test_passed=False,
            data_fetch_test_passed=False,
            sample_records_count=0,
            errors=errors if errors else (["Tests failed - check logs"] if not final_passed else []),
            logs=response[-4000:],
            duration_seconds=0.0,
        )
