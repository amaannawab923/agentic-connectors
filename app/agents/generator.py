"""Code generator agent for creating connector code.

Uses Claude Agent SDK with Write tool for file generation.
Supports two modes:
1. GENERATE mode: Create new connector from research
2. FIX mode: Fix existing code to pass tests (with internal retry loop)
"""

import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from ..models.enums import AgentType
from ..models.schemas import AgentResult, GeneratedFile

logger = logging.getLogger(__name__)


class GeneratorAgent(BaseAgent):
    """Agent that generates connector code based on research.

    This agent uses Claude Agent SDK with:
    - Built-in Write tool for file creation
    - Built-in Read tool for context
    - Built-in Bash tool for running tests in FIX mode
    - Automatic context management for large codebases

    Two operational modes:
    1. GENERATE mode: Fresh code generation from research
    2. FIX mode: Fix existing code to pass existing tests (max 3 internal retries)
    """

    agent_type = AgentType.GENERATOR

    # System prompt for GENERATE mode (creating new code)
    system_prompt_generate = """You are an expert Python developer specializing in data connector development.
Your task is to generate production-ready connector code based on research documentation.

When generating code:
1. Follow Python best practices and PEP 8 style guidelines
2. Use comprehensive type hints throughout
3. Implement robust error handling with custom exceptions
4. Include detailed docstrings for all classes and methods
5. Implement rate limiting and retry logic
6. Use Pydantic for configuration validation
7. Structure code in a modular, maintainable way
8. Do NOT use any external connector frameworks (no Airbyte CDK, no Singer SDK)
9. Create standalone, self-contained implementations

## 🚨 CRITICAL: API Token/Key Validation Rules

**NEVER hardcode API token/key format validation!**

### ❌ WRONG - Don't Do This:
```python
@field_validator("api_key")
def validate_key(cls, v):
    if not v.startswith("sk_"):  # DON'T HARDCODE PREFIX!
        raise ValueError("Key must start with sk_")
    return v
```

### ✅ CORRECT - Do This Instead:

**Option 1: No Format Validation (BEST)**
```python
# Let the API itself reject invalid tokens
api_key: str = Field(
    ...,
    description="API key from provider",
    min_length=20  # Only validate minimum length
)
# No @field_validator for format - treat as opaque string
```

**Option 2: If Research Documents Multiple Formats**
```python
@field_validator("token")
def validate_token(cls, v):
    # Research shows: old format 'secret_*', new format 'ntn_*' (both valid)
    # Support ALL documented formats
    valid_prefixes = ["secret_", "ntn_"]
    if not any(v.startswith(p) for p in valid_prefixes):
        raise ValueError(f"Token must start with one of: {valid_prefixes}")
    return v
```

**Option 3: If Vendor Says "Treat as Opaque String"**
```python
# NO validation at all - vendor explicitly says don't validate
token: str = Field(..., description="Integration token")
```

### WHY This Matters

API providers change token formats frequently for security reasons:
- Stripe: `sk_test_*` → `rk_test_*` (recent)
- Notion: `secret_*` → `ntn_*` (Sept 2024)
- GitHub: `ghp_*`, `github_pat_*` (multiple formats)

Hardcoding format breaks when APIs evolve. **Always prefer permissive validation.**

### Implementation Guidelines

1. **Check Research Doc**: Look for "Token Format" section with vendor guidance
2. **If vendor says "don't validate"**: Don't validate format, only length
3. **If multiple formats documented**: Accept ALL of them
4. **If uncertain**: Default to minimum length validation only
5. **Never assume**: Token format from examples may be outdated

Generated file structure should be:
- src/__init__.py - Package exports
- src/auth.py - Authentication handling
- src/client.py - API client with rate limiting
- src/config.py - Configuration management with Pydantic (**Follow token validation rules!**)
- src/connector.py - Main connector class
- src/streams.py - Data stream definitions
- src/utils.py - Utility functions
- requirements.txt - Python dependencies

Use the Write tool to create each file with complete, runnable code.
Make sure each file is syntactically correct and can be imported independently."""

    # System prompt for FIX mode (fixing code to pass tests)
    system_prompt_fix = """You are an expert Python developer specializing in debugging and fixing code.
Your task is to FIX existing connector code so that it passes the existing tests.

## YOUR MISSION
The tests have already been written and validated. They correctly test the expected behavior.
Your job is to fix the CONNECTOR CODE (not the tests) to make all tests pass.

## FIX MODE WORKFLOW

1. **Read the test results** to understand what failed and why
2. **Read the test files** to understand what behavior is expected
3. **Read the connector source code** to find the bugs
4. **Research solutions if needed** - Use WebSearch to find correct patterns for unfamiliar libraries
5. **Fix the bugs** using the Edit or Write tool
6. **Run the tests** using Bash to verify your fixes
7. **Repeat** until all tests pass (max 3 attempts)

## CRITICAL RULES

1. **DO NOT modify test files** - The tests are correct
2. **Only modify src/*.py files** - That's where the bugs are
3. **Run tests after each fix** - Verify your changes work
4. **Be precise** - Fix exactly what's broken, don't refactor unnecessarily
5. **Research when stuck** - If you don't know the correct pattern for a library, USE WEBSEARCH

## RESEARCH GUIDANCE

When encountering library-specific errors you're unsure about, USE WEBSEARCH to find solutions:
- Search for "how to [do X] with [library] python"
- Search for the specific error message
- Look for official documentation or Stack Overflow answers

Examples of when to search:
- `universe_domain` validation errors in google-api-python-client
- OAuth2 credential configuration patterns
- Pydantic v2 migration issues
- API client library compatibility issues

## COMMON FIX PATTERNS

### Pydantic Discriminator Error
If you see: `PydanticUserError: Model needs field 'X' to be of type Literal`
Fix: Change `field: SomeEnum = Field(default=SomeEnum.VALUE)`
To: `field: Literal["value"] = Field(default="value")`
Add: `from typing import Literal` to imports

### Import Errors
If you see: `ImportError: cannot import name 'X'`
Fix: Check the actual class/function names in the source files

### Attribute Errors
If you see: `AttributeError: 'X' has no attribute 'Y'`
Fix: Check if the method/attribute exists, add it if missing

### Google API universe_domain Error
If you see: `UniverseMismatchError` or `universe_domain` validation failure:
- This is a compatibility issue with google-api-python-client >= 2.100.0
- Search for "google-api-python-client universe_domain fix" to find the solution
- Usually requires setting universe_domain on credentials or client options

### Library Version Compatibility
If errors suggest library version incompatibility:
- Search for "[library] [version] breaking changes"
- Check if API has changed between versions

## TEST VERIFICATION

After making fixes, run:
```bash
source venv/bin/activate
cd {connector_dir}
python -m pytest tests/ -v --tb=short
```

Report the test results and whether all tests pass."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generated_files: List[GeneratedFile] = []

    async def execute(
        self,
        connector_name: str,
        connector_type: str = "source",
        research_doc_path: Optional[str] = None,
        research_doc_content: Optional[str] = None,
        fix_errors: Optional[List[str]] = None,
        review_feedback: Optional[List[str]] = None,
        connector_dir: Optional[str] = None,
        test_results_path: Optional[str] = None,
        max_fix_attempts: int = 3,
    ) -> AgentResult:
        """Execute the generator agent.

        Args:
            connector_name: Name of the connector (e.g., 'Google Sheets').
            connector_type: Type of connector (source/destination).
            research_doc_path: Path to the research document .md file.
            research_doc_content: Direct research content (alternative to path).
            fix_errors: List of errors to fix from failed tests (triggers FIX mode).
            review_feedback: List of improvements from code review.
            connector_dir: Directory containing the connector (for FIX mode).
            test_results_path: Path to test_results.json (for FIX mode).
            max_fix_attempts: Maximum attempts to fix code in FIX mode (default 3).

        Returns:
            AgentResult with generated files info.
        """
        start_time = time.time()
        self.reset_token_tracking()
        self.generated_files = []

        # Determine mode: FIX or GENERATE
        is_fix_mode = bool(fix_errors) and bool(connector_dir)

        if is_fix_mode:
            return await self._execute_fix_mode(
                connector_name=connector_name,
                connector_type=connector_type,
                connector_dir=connector_dir,
                fix_errors=fix_errors,
                test_results_path=test_results_path,
                max_fix_attempts=max_fix_attempts,
                start_time=start_time,
            )
        else:
            return await self._execute_generate_mode(
                connector_name=connector_name,
                connector_type=connector_type,
                research_doc_path=research_doc_path,
                research_doc_content=research_doc_content,
                review_feedback=review_feedback,
                start_time=start_time,
            )

    async def _execute_fix_mode(
        self,
        connector_name: str,
        connector_type: str,
        connector_dir: str,
        fix_errors: List[str],
        test_results_path: Optional[str],
        max_fix_attempts: int,
        start_time: float,
    ) -> AgentResult:
        """Execute in FIX mode - fix existing code to pass tests.

        This mode:
        1. Reads test results and existing tests
        2. Fixes the connector code
        3. Runs tests to verify
        4. Retries up to max_fix_attempts times
        """
        logger.info("=" * 60)
        logger.info(f"[GENERATOR] FIX MODE for {connector_name}")
        logger.info(f"[GENERATOR] Connector dir: {connector_dir}")
        logger.info(f"[GENERATOR] Max attempts: {max_fix_attempts}")
        logger.info(f"[GENERATOR] Errors to fix: {len(fix_errors)}")
        logger.info("=" * 60)

        connector_path = Path(connector_dir)
        if not connector_path.exists():
            return self._create_result(
                success=False,
                error=f"Connector directory not found: {connector_dir}",
                duration_seconds=time.time() - start_time,
            )

        self.working_dir = connector_dir

        # Build the fix prompt
        prompt = self._build_fix_prompt(
            connector_name=connector_name,
            connector_dir=connector_dir,
            fix_errors=fix_errors,
            test_results_path=test_results_path,
            max_fix_attempts=max_fix_attempts,
        )

        try:
            from claude_agent_sdk import ClaudeAgentOptions

            def log_stderr(msg):
                logger.info(f"[GENERATOR-FIX-SDK-STDERR] {msg}")

            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt_fix,
                max_turns=50,  # More turns for read-fix-test cycles
                allowed_tools=["Read", "Write", "Edit", "Bash", "WebSearch", "WebFetch"],
                permission_mode="acceptEdits",
                cwd=connector_dir,
                stderr=log_stderr,
                include_partial_messages=True,
            )

            logger.info(f"[GENERATOR] Starting FIX mode with max_turns=50")

            # Stream the fix response
            response = await self._stream_response(prompt, options)

            # Check if tests pass now by looking at the response or running tests
            tests_passed = self._check_tests_passed(connector_dir, response)

            # Collect updated files
            generated_files = self._collect_generated_files(connector_dir)
            self.generated_files = generated_files

            duration = time.time() - start_time

            logger.info("=" * 60)
            logger.info(f"[GENERATOR] FIX MODE COMPLETED")
            logger.info(f"[GENERATOR] Tests passed: {tests_passed}")
            logger.info(f"[GENERATOR] Files: {len(generated_files)}")
            logger.info(f"[GENERATOR] Duration: {duration:.1f}s")
            logger.info("=" * 60)

            output_summary = json.dumps({
                "mode": "fix",
                "output_dir": connector_dir,
                "tests_passed": tests_passed,
                "files_updated": len(generated_files),
                "file_paths": [str(connector_path / f.path) for f in generated_files],
            })

            return self._create_result(
                success=True,
                output=output_summary,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.exception("[GENERATOR] FIX mode failed")
            return self._create_result(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    async def _execute_generate_mode(
        self,
        connector_name: str,
        connector_type: str,
        research_doc_path: Optional[str],
        research_doc_content: Optional[str],
        review_feedback: Optional[List[str]],
        start_time: float,
    ) -> AgentResult:
        """Execute in GENERATE mode - create new connector from research."""
        logger.info("=" * 60)
        logger.info(f"[GENERATOR] GENERATE MODE for {connector_name}")
        logger.info("=" * 60)

        # Read research document
        if research_doc_path:
            research_path = Path(research_doc_path)
            if not research_path.exists():
                return self._create_result(
                    success=False,
                    error=f"Research document not found: {research_doc_path}",
                    duration_seconds=time.time() - start_time,
                )
            research_doc = research_path.read_text(encoding="utf-8")
            logger.info(f"Read research doc from: {research_doc_path} ({len(research_doc)} chars)")
        elif research_doc_content:
            research_doc = research_doc_content
        else:
            return self._create_result(
                success=False,
                error="Either research_doc_path or research_doc_content must be provided",
                duration_seconds=time.time() - start_time,
            )

        # Create output directory
        connector_slug = connector_name.lower().replace(" ", "-").replace("_", "-")
        output_dir = Path(__file__).parent.parent.parent / "output" / "connector-implementations" / f"{connector_type}-{connector_slug}"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir = str(output_dir)

        logger.info(f"Output directory: {output_dir}")

        # Build the generation prompt
        prompt = self._build_generation_prompt(
            connector_name=connector_name,
            connector_type=connector_type,
            research_doc=research_doc,
            output_dir=str(output_dir),
            review_feedback=review_feedback,
        )

        try:
            from claude_agent_sdk import ClaudeAgentOptions

            def log_stderr(msg):
                logger.info(f"[GENERATOR-SDK-STDERR] {msg}")

            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt_generate,
                max_turns=25,
                allowed_tools=["Read", "Write", "Bash"],
                permission_mode="acceptEdits",
                cwd=str(output_dir),
                stderr=log_stderr,
                include_partial_messages=True,
            )

            logger.info(f"Starting code generation for {connector_name} with max_turns=25")

            # Stream the generation response
            response = await self._stream_response(prompt, options)

            # Collect generated files
            generated_files = self._collect_generated_files(str(output_dir))

            # Fallback to inline files if needed
            inline_files = self._parse_files_from_response(response)
            if inline_files and not generated_files:
                for f in inline_files:
                    file_path = output_dir / f.path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(f.content, encoding="utf-8")
                    logger.info(f"Saved inline file: {file_path}")
                generated_files = inline_files

            if not generated_files:
                raise ValueError("No files were generated")

            self.generated_files = generated_files
            duration = time.time() - start_time

            logger.info(f"Generated {len(generated_files)} files in {duration:.1f}s")

            file_paths = [str(output_dir / f.path) for f in generated_files]
            output_summary = json.dumps({
                "mode": "generate",
                "output_dir": str(output_dir),
                "files_generated": len(generated_files),
                "file_paths": file_paths,
            })

            return self._create_result(
                success=True,
                output=output_summary,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.exception("Generator agent failed")
            return self._create_result(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _build_fix_prompt(
        self,
        connector_name: str,
        connector_dir: str,
        fix_errors: List[str],
        test_results_path: Optional[str],
        max_fix_attempts: int,
    ) -> str:
        """Build the prompt for FIX mode."""
        prompt = f"""# Code Fix Task: {connector_name}

## YOUR MISSION
Fix the connector code to make all tests pass. The tests are correct - the bugs are in the connector code.

## Connector Directory
`{connector_dir}`

## Errors to Fix
The TestReviewer identified these issues in the CONNECTOR CODE (not tests):

"""
        for i, error in enumerate(fix_errors, 1):
            prompt += f"{i}. {error}\n"

        prompt += f"""

## FIX WORKFLOW (Max {max_fix_attempts} attempts)

### Step 1: Understand the Problem
Read these files to understand what's expected:
- `{connector_dir}/tests/test_results.json` - Detailed test results
- `{connector_dir}/tests/test_*.py` - Test files (to understand expected behavior)
- `{connector_dir}/src/config.py` - Configuration (likely has Pydantic issues)
- `{connector_dir}/src/connector.py` - Main connector
- `{connector_dir}/src/auth.py` - Authentication

### Step 2: Fix the Code
Based on the errors, modify the source files in `{connector_dir}/src/`:
- Use the Edit tool for precise changes
- Or Write tool to rewrite entire files if needed

### Step 3: Verify the Fix
Run the tests to verify your fix:
```bash
source venv/bin/activate
cd {connector_dir}
python -m pytest tests/ -v --tb=short 2>&1
```

### Step 4: Iterate if Needed
If tests still fail, read the new error output and fix again.
Repeat until all tests pass or you've made {max_fix_attempts} attempts.

## COMMON FIXES

### Pydantic Literal Type for Discriminator
```python
# WRONG (causes PydanticUserError)
auth_type: AuthType = Field(default=AuthType.SERVICE_ACCOUNT, ...)

# CORRECT
from typing import Literal
auth_type: Literal["service_account"] = Field(default="service_account", ...)
```

### Missing Method/Attribute
Add the missing method or fix the typo in the method name.

### Import Error
Check that class names match between files.

## IMPORTANT
- ONLY modify files in `{connector_dir}/src/`
- DO NOT modify test files
- Run tests after each change to verify

Begin by reading the test results and source code, then make your fixes.
"""
        return prompt

    def _build_generation_prompt(
        self,
        connector_name: str,
        connector_type: str,
        research_doc: str,
        output_dir: str,
        review_feedback: Optional[List[str]] = None,
    ) -> str:
        """Build the code generation prompt."""
        truncated_research = research_doc[:30000] if len(research_doc) > 30000 else research_doc

        prompt = f"""# Code Generation Task

Generate a complete, production-ready **{connector_type}** connector for **{connector_name}**.

## Output Directory
**IMPORTANT**: Write all files to this directory using ABSOLUTE paths:
`{output_dir}`

For example, to create src/__init__.py, use the Write tool with file_path:
`{output_dir}/src/__init__.py`

## Research Document
Use the following research as a guide for implementation:

<research>
{truncated_research}
</research>

## Requirements

1. **Standalone Implementation**: No external connector frameworks
2. **Type Safety**: Complete type hints throughout
3. **Error Handling**: Custom exceptions, proper error propagation
4. **Rate Limiting**: Implement rate limiting with exponential backoff
5. **Configuration**: Pydantic models for validation
6. **Documentation**: Comprehensive docstrings
7. **Testability**: Clean interfaces for easy testing

## File Structure

Generate the following files using the Write tool with ABSOLUTE paths:

1. **{output_dir}/src/__init__.py** - Package exports
2. **{output_dir}/src/auth.py** - Authentication (OAuth2, API Key, Service Account support)
3. **{output_dir}/src/client.py** - API client with rate limiting and retries
4. **{output_dir}/src/config.py** - Configuration models using Pydantic
5. **{output_dir}/src/connector.py** - Main connector class with check/discover/read methods
6. **{output_dir}/src/streams.py** - Data stream definitions
7. **{output_dir}/src/utils.py** - Utility functions
8. **{output_dir}/requirements.txt** - Python dependencies
9. **{output_dir}/IMPLEMENTATION.md** - Implementation summary (REQUIRED)

## IMPORTANT: Pydantic Discriminated Unions

When using Pydantic's discriminator feature, you MUST use Literal types:

```python
from typing import Literal, Union
from pydantic import BaseModel, Field

class ServiceAccountCreds(BaseModel):
    # CORRECT: Use Literal for discriminator field
    auth_type: Literal["service_account"] = Field(default="service_account")
    ...

class OAuth2Creds(BaseModel):
    auth_type: Literal["oauth2"] = Field(default="oauth2")
    ...

class Config(BaseModel):
    credentials: Union[ServiceAccountCreds, OAuth2Creds] = Field(
        ...,
        discriminator="auth_type"  # Works because auth_type is Literal
    )
```

DO NOT use Enum types for discriminator fields - they will cause PydanticUserError.
"""

        if review_feedback:
            prompt += """
## Review Feedback

The code review identified these improvements:

"""
            for feedback in review_feedback:
                prompt += f"- {feedback}\n"

        prompt += """
## Instructions

1. Use the Write tool to create each file
2. Make sure each file is complete and syntactically correct
3. Include all necessary imports in each file
4. Follow the patterns from the research document
5. Ensure the connector can be imported and used immediately

Begin generating the connector code now.
"""

        return prompt

    def _check_tests_passed(self, connector_dir: str, response: str) -> bool:
        """Check if tests passed based on response or by running tests."""
        response_lower = response.lower()

        # Look for test success indicators in response
        success_indicators = [
            "all tests pass",
            "tests passed",
            "0 failed",
            "passed, 0 failed",
            '"passed": true',
        ]

        if any(indicator in response_lower for indicator in success_indicators):
            return True

        # Also check for failure indicators
        failure_indicators = [
            "tests failed",
            "failed,",
            '"passed": false',
        ]

        if any(indicator in response_lower for indicator in failure_indicators):
            return False

        # If unclear, try running tests directly
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=no", "-q"],
                cwd=connector_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Could not run tests to verify: {e}")
            return False

    def _parse_files_from_response(self, response: str) -> List[GeneratedFile]:
        """Parse file blocks from the response text."""
        files = []
        pattern = r'```file:([^\n]+)\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)

        for path, content in matches:
            path = path.strip()
            content = content.strip()
            files.append(GeneratedFile(
                path=path,
                content=content,
                description=f"Generated file: {path}",
            ))

        return files

    def _collect_generated_files(self, output_dir: str) -> List[GeneratedFile]:
        """Collect files that were written to the output directory."""
        files = []
        output_path = Path(output_dir)

        if not output_path.exists():
            return files

        for file_path in output_path.rglob("*.py"):
            relative_path = file_path.relative_to(output_path)
            try:
                content = file_path.read_text()
                files.append(GeneratedFile(
                    path=str(relative_path),
                    content=content,
                    description=f"Generated file: {relative_path}",
                ))
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")

        # Also get requirements.txt
        req_path = output_path / "requirements.txt"
        if req_path.exists():
            try:
                content = req_path.read_text()
                files.append(GeneratedFile(
                    path="requirements.txt",
                    content=content,
                    description="Python dependencies",
                ))
            except Exception as e:
                logger.warning(f"Failed to read requirements.txt: {e}")

        # Also get IMPLEMENTATION.md
        impl_path = output_path / "IMPLEMENTATION.md"
        if impl_path.exists():
            try:
                content = impl_path.read_text()
                files.append(GeneratedFile(
                    path="IMPLEMENTATION.md",
                    content=content,
                    description="Implementation summary for testing",
                ))
            except Exception as e:
                logger.warning(f"Failed to read IMPLEMENTATION.md: {e}")

        return files

    def get_generated_files(self) -> List[GeneratedFile]:
        """Get the list of generated files."""
        return self.generated_files.copy()

    def save_files_to_disk(self, output_dir: str) -> List[str]:
        """Save generated files to disk."""
        saved_paths = []
        output_path = Path(output_dir)

        for gen_file in self.generated_files:
            file_path = output_path / gen_file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                f.write(gen_file.content)

            saved_paths.append(str(file_path))
            logger.info(f"Saved: {file_path}")

        return saved_paths
