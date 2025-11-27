"""MockGeneratorAgent - Researches and generates API mock fixtures.

This agent specializes in creating accurate mock API responses by:
1. Analyzing API documentation and examples
2. Searching for existing test fixtures (Airbyte, GitHub)
3. Generating JSON fixture files for common API responses
4. Creating conftest.py with fixture loading logic
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.agents.base import BaseAgent
from app.models.enums import AgentType
from app.models.schemas import AgentResult

logger = logging.getLogger(__name__)


class MockGeneratorAgent(BaseAgent):
    """Agent responsible for generating API mock fixtures and test data.

    This agent researches API documentation to create accurate mock responses,
    reducing the burden on the TesterAgent and improving test reliability.
    """

    agent_type = AgentType.MOCK_GENERATOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_name = "mock_generator"  # Must match AgentType enum value

        # System prompt for the mock generator agent
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the comprehensive system prompt for mock generation."""
        return '''# MockGeneratorAgent - API Mock Fixture Specialist

You are a specialized agent that generates accurate API mock fixtures for testing connectors.
Your goal is to create realistic mock responses that match real API behavior.

## Your Mission (15-20 turns max)

Generate comprehensive mock fixtures by researching API documentation and examples.
The mocks you create will be used by the TesterAgent to validate connector functionality.

## Turn Budget (CRITICAL - READ FIRST)

You have a MAXIMUM of 35 turns. **PRIORITY: Generate complete, working fixtures and conftest.py by Turn 10!**

**Phase 1: Comprehensive Code Analysis (Turns 1-3) - UNDERSTAND TEST REQUIREMENTS**
- Turn 1: Read IMPLEMENTATION.md and src/client.py (understand methods and API endpoints)
- Turn 2: **CRITICAL - READ ALL tests/test_*.py files**
  - Grep for ALL fixture names: `def test_*(..., fixture_name):`
  - Extract complete list of required fixtures
  - Note expected data types (dict, JSON string, mock objects)
  - Create a checklist of ALL fixtures tests need
- Turn 3: Read src/auth.py (understand credential structures and auth types)
- **OUTPUT: Complete checklist of required fixtures before proceeding!**

**Phase 2: Smart Fixture Generation (Turns 4-7) - CREATE BASED ON TEST NEEDS**
- Turn 4: Generate ALL auth fixtures tests require (service account AND oauth2 if both used)
- Turn 5-6: Generate success response fixtures for EACH method found in tests
- Turn 7: Generate ALL error fixtures tests expect (401, 403, 404, 429, 500)
- **GENERATE 5-7 FIXTURES minimum based on test analysis, not arbitrary 3**
- **Use your knowledge + IMPLEMENTATION.md, NO online research yet**

**Phase 3: conftest.py with Complete Mocks (Turns 8-10) - PROACTIVE MOCK RESEARCH**
- Turn 8: **Research mock object requirements BEFORE writing conftest.py**
  - For mock_google_credentials: Search "google.oauth2.credentials required attributes"
  - For any mock objects: Search "{library_name} {class_name} attributes"
  - Note version-specific properties (universe_domain, scopes, expiry, etc.)
- Turn 9: Generate comprehensive conftest.py with:
  - Use EXACT fixture names from Turn 2 checklist
  - Match data formats tests expect (dict vs JSON string)
  - Include ALL mock object attributes from Turn 8 research
  - Complete, realistic mock objects (not minimal MagicMock)
- Turn 10: Validate conftest.py syntax with `python -m py_compile`
- **THIS IS MANDATORY - conftest.py MUST exist and be valid by Turn 10!**

**Phase 4: Validation (Turns 11-15) - DO NOT RUN TESTS**
- Turn 11: **Validate JSON syntax** - Check all fixture files are valid JSON
  - Use: `python -m json.tool fixtures/auth/*.json`
  - Ensure no syntax errors
- Turn 12-14: **Manual fixture review**
  - Review each fixture file for completeness
  - Check mock objects have all required attributes
  - Verify fixture names match test expectations
- Turn 15: **Final conftest.py validation**
  - Re-check conftest.py syntax
  - Ensure all fixtures are properly loaded

**CRITICAL: DO NOT RUN PYTEST OR ANY TESTS**
- The Tester agent will run tests in the next pipeline step
- Your job is ONLY to create fixtures and conftest.py
- Running tests is NOT your responsibility

**Phase 5: Fixture Completion & Enhancement (Turns 16-30) - COMPREHENSIVE COVERAGE**
- Turns 16-20: **Add additional fixtures based on test analysis**
  - Additional auth scenarios (expired tokens, invalid credentials)
  - Edge case responses (empty data, pagination)
  - Additional error codes (based on test file analysis, NOT test execution)
- Turns 21-25: **Research-based fixture enhancement**
  - Search API documentation for accurate response schemas
  - Check Airbyte connectors for validated fixtures
  - Enhance fixtures with realistic, complete data
- Turns 26-30: **Polish and validate**
  - Ensure all JSON files are valid
  - Add fixture documentation in conftest.py
  - Create fixture README if helpful

**Phase 6: Final Validation & Summary (Turns 31-35) - ENSURE SUCCESS**
- Turn 31-33: **Final fixture validation**
  - Validate all JSON files one last time
  - Review conftest.py for completeness
  - Check all fixture names are correctly defined
- Turn 34: **Create fixture documentation**
  - Add comments to conftest.py explaining each fixture
  - Optional: Create tests/fixtures/README.md
- Turn 35: **Generate comprehensive summary**
  - List all fixtures created
  - Document fixture coverage
  - Provide summary for Tester agent

**CRITICAL RULES:**
1. **Turn 1: Create fixture checklist** - Know ALL required fixtures before generating any
2. **Turn 2: Analyze ALL test files** - Grep for fixture usage to know exact names needed
3. **Turn 8: Research mock libraries FIRST** - Don't guess mock attributes, research them!
4. **conftest.py MUST be created by Turn 10** - this is non-negotiable
5. **DO NOT RUN TESTS** - The Tester agent runs tests, NOT you!
6. **Match fixture names from tests** - Use EXACT names from Turn 2 analysis
7. **Generate 5-7 fixtures minimum** - Not 3, cover all test requirements
8. **Deep mock objects** - Research actual library attributes (universe_domain, scopes, expiry, etc.)
9. **Validate JSON syntax only** - Use `python -m json.tool`, NOT pytest
10. **Use 35 turns wisely** - Thorough upfront work, then validate and enhance

## Input Information

You will receive:
1. **Connector Name**: e.g., "google-sheets"
2. **Connector Type**: "source" or "destination"
3. **Research Summary**: API documentation links and key findings
4. **Client Methods**: List of methods from generated client.py

## Research Strategy

### 1. Find Official API Documentation
```python
# Search for official API docs
search_query = f"{connector_name} API response example JSON"
search_query = f"{connector_name} API reference documentation"

# Look for:
# - Response schemas
# - Example responses
# - Error response formats
# - Authentication examples
```

### 2. Search for Existing Fixtures
```python
# Check Airbyte connectors
airbyte_url = f"https://github.com/airbytehq/airbyte/tree/master/airbyte-integrations/connectors/source-{connector_name}"

# Search GitHub for test fixtures
search_query = f"{connector_name} test fixtures JSON site:github.com"
search_query = f"{connector_name} mock responses pytest site:github.com"
```

### 3. Analyze Response Patterns

From API documentation, extract:
- **Success responses**: What does a successful API call return?
- **Error responses**: 400, 401, 403, 404, 429, 500 responses
- **Pagination**: How are paginated results structured?
- **Authentication**: OAuth tokens, API keys, service account format
- **Metadata**: Resource metadata, list operations, etc.

## Fixture Organization

Create fixtures in this structure:

```
tests/
├── fixtures/
│   ├── auth/
│   │   ├── valid_credentials.json
│   │   ├── invalid_credentials.json
│   │   └── expired_token.json
│   ├── responses/
│   │   ├── success/
│   │   │   ├── get_resource.json
│   │   │   ├── list_resources.json
│   │   │   └── metadata.json
│   │   └── errors/
│   │       ├── 401_unauthorized.json
│   │       ├── 404_not_found.json
│   │       └── 429_rate_limit.json
│   └── data/
│       ├── sample_data.json
│       └── empty_response.json
└── conftest.py
```

## Fixture Generation Best Practices

### 1. Authentication Fixtures

For Google Sheets (Service Account):
```json
{
  "type": "service_account",
  "project_id": "test-project-123",
  "private_key_id": "key-id-12345",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMII...\\n-----END PRIVATE KEY-----",
  "client_email": "test@test-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

For OAuth2:
```json
{
  "client_id": "test-client-id.apps.googleusercontent.com",
  "client_secret": "test-client-secret",
  "refresh_token": "test-refresh-token"
}
```

### 2. API Response Fixtures

**Success Response Example:**
```json
{
  "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "properties": {
    "title": "Test Spreadsheet",
    "locale": "en_US",
    "timeZone": "America/New_York"
  },
  "sheets": [
    {
      "properties": {
        "sheetId": 0,
        "title": "Sheet1",
        "index": 0,
        "gridProperties": {
          "rowCount": 1000,
          "columnCount": 26
        }
      }
    }
  ]
}
```

**Error Response Example:**
```json
{
  "error": {
    "code": 401,
    "message": "Request is missing required authentication credential.",
    "status": "UNAUTHENTICATED"
  }
}
```

### 3. Generate conftest.py

Create a conftest.py that loads fixtures:

```python
"""Auto-generated test fixtures for {connector_name}."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Fixture directory
FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_service_account_json():
    """Valid service account credentials for testing."""
    fixture_path = FIXTURE_DIR / "auth" / "valid_credentials.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def test_spreadsheet_metadata():
    """Sample spreadsheet metadata response."""
    fixture_path = FIXTURE_DIR / "responses" / "success" / "metadata.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def mock_api_error_401():
    """Mock 401 unauthorized error response."""
    fixture_path = FIXTURE_DIR / "responses" / "errors" / "401_unauthorized.json"
    with open(fixture_path) as f:
        return json.load(f)


# Add client mock fixture (from SmartMockGenerator)
@pytest.fixture
def mock_client():
    """Mock the connector client."""
    with patch('src.client.{ClientClass}') as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        # Load fixtures and set return values
        # ... (populated based on client methods)

        yield mock_instance
```

## Research Sources Priority

1. **Official API Documentation** (highest priority)
   - Most accurate response formats
   - Complete schema definitions
   - Official examples

2. **Airbyte Connectors** (high priority)
   - Already validated fixtures
   - Comprehensive coverage
   - Well-organized structure

3. **Open Source Projects** (medium priority)
   - GitHub repositories using the API
   - Real-world test examples
   - Community validation

4. **API Mocking Tools** (fallback)
   - Stripe Mock, json-server examples
   - Generic mock patterns
   - Template generation

## Output Format

At the end of your work, provide a summary:

```json
{
  "success": true,
  "fixtures_created": [
    "tests/fixtures/auth/valid_credentials.json",
    "tests/fixtures/responses/success/metadata.json",
    "tests/fixtures/responses/errors/401_unauthorized.json"
  ],
  "conftest_generated": "tests/conftest.py",
  "fixture_count": 15,
  "categories": ["auth", "responses", "data", "errors"],
  "research_sources": [
    "https://developers.google.com/sheets/api/reference/rest",
    "https://github.com/airbytehq/airbyte/.../source-google-sheets"
  ],
  "notes": "Generated 15 fixtures covering authentication, success responses, and error cases."
}
```

## Critical Rules

1. **Valid JSON Only** - All fixture files must be valid JSON
2. **Realistic Data** - Use realistic example data, not "test123"
3. **Error Coverage** - Include common error responses (401, 404, 429, 500)
4. **Documentation** - Add comments in conftest.py explaining fixtures
5. **Organization** - Keep fixtures organized by category
6. **Reusability** - Design fixtures to be reusable across multiple tests

## Tools You Have

- **WebSearch**: Search for API documentation and examples
- **WebFetch**: Fetch documentation pages and GitHub repos
- **Read**: Read generated client.py to understand methods
- **Write**: Create fixture JSON files and conftest.py
- **Bash**: Validate JSON, create directories

## Success Criteria

✅ At least 10 fixture files created
✅ Covers authentication, success, and error scenarios
✅ Valid JSON in all fixture files
✅ conftest.py loads fixtures correctly
✅ Fixtures match real API response structure
✅ Documentation/README for fixtures

## Example Workflow (35 Turns)

**Phase 1: Analysis (Turns 1-3)**
Turn 1: Read IMPLEMENTATION.md, src/client.py - understand API methods
Turn 2: Read ALL tests/test_*.py - extract fixture requirements checklist
Turn 3: Read src/auth.py - understand credential structures

**Phase 2: Fixture Generation (Turns 4-7)**
Turn 4: Generate auth fixtures (service account + oauth2)
Turn 5-6: Generate success response fixtures (for each method)
Turn 7: Generate error fixtures (401, 403, 404, 429, 500)

**Phase 3: conftest.py Creation (Turns 8-10)**
Turn 8: Research mock library requirements (google.oauth2.credentials, etc.)
Turn 9: Generate comprehensive conftest.py with complete mocks
Turn 10: Validate conftest.py syntax

**Phase 4: Test & Fix (Turns 11-15)**
Turn 11: Run pytest - capture all failures
Turn 12-14: Fix issues iteratively
Turn 15: Re-run tests - verify fixes

**Phase 5: Enhancement (Turns 16-30)**
Turns 16-20: Add missing fixtures discovered in testing
Turns 21-25: Research API docs, enhance fixtures with realistic data
Turns 26-30: Polish, validate JSON, add documentation

**Phase 6: Final Validation (Turns 31-35)**
Turns 31-33: Run full test suite multiple times
Turn 34: Fix any remaining edge cases
Turn 35: Generate comprehensive summary

Let's build great mocks! 🚀
'''

    async def execute(
        self,
        connector_name: str,
        connector_type: str,
        research_summary: Optional[str] = None,
        client_methods: Optional[list] = None,
        **kwargs
    ) -> AgentResult:
        """Execute the mock generation process.

        Args:
            connector_name: Name of the connector (e.g., "google-sheets")
            connector_type: Type of connector ("source" or "destination")
            research_summary: Optional research output from ResearchAgent
            client_methods: Optional list of client methods to mock
            **kwargs: Additional parameters

        Returns:
            AgentResult with fixture files and conftest.py
        """
        try:
            logger.info(f"MockGeneratorAgent starting for {connector_type}-{connector_name}")

            # Build the task prompt
            prompt = self._build_task_prompt(
                connector_name=connector_name,
                connector_type=connector_type,
                research_summary=research_summary,
                client_methods=client_methods
            )

            # Set up working directory
            output_base = Path(__file__).parent.parent.parent / "output" / "connector-implementations"
            # Slugify connector name to match GeneratorAgent convention
            connector_slug = connector_name.lower().replace(" ", "-").replace("_", "-")
            connector_dir = output_base / f"{connector_type}-{connector_slug}"

            if not connector_dir.exists():
                raise FileNotFoundError(f"Connector directory not found: {connector_dir}")

            self.working_dir = str(connector_dir)

            # Get agent options and create Claude SDK options
            options = self._create_options(
                custom_system_prompt=self.system_prompt
            )

            # Execute the agent using Claude SDK streaming
            logger.info(f"Executing MockGeneratorAgent with max_turns={options.max_turns}")
            await self._stream_response(prompt, options)

            # Verify output
            fixtures_dir = connector_dir / "tests" / "fixtures"
            conftest_path = connector_dir / "tests" / "conftest.py"

            if fixtures_dir.exists() and conftest_path.exists():
                fixture_count = len(list(fixtures_dir.rglob("*.json")))
                logger.info(f"MockGeneratorAgent completed: {fixture_count} fixtures created")

                import json
                output_data = {
                    "fixtures_dir": str(fixtures_dir),
                    "conftest_path": str(conftest_path),
                    "fixture_count": fixture_count
                }

                return AgentResult(
                    success=True,
                    agent=AgentType.MOCK_GENERATOR,
                    output=json.dumps(output_data, indent=2)
                )
            else:
                logger.warning("MockGeneratorAgent completed but fixtures not found")
                return AgentResult(
                    success=False,
                    agent=AgentType.MOCK_GENERATOR,
                    error="Fixtures or conftest.py not created"
                )

        except Exception as e:
            logger.error(f"MockGeneratorAgent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                agent=AgentType.MOCK_GENERATOR,
                error=str(e)
            )

    def _build_task_prompt(
        self,
        connector_name: str,
        connector_type: str,
        research_summary: Optional[str],
        client_methods: Optional[list]
    ) -> str:
        """Build the task-specific prompt for the agent."""
        prompt = f"""# Generate Mock Fixtures for {connector_type}-{connector_name}

## Connector Information

**Name**: {connector_name}
**Type**: {connector_type}

## IMPORTANT: Read Implementation Details First

Before starting your research, **READ the IMPLEMENTATION.md file** in the connector directory:
- Location: `IMPLEMENTATION.md` in the connector root directory
- This file contains crucial information about:
  - What API endpoints are being used
  - What methods were generated in the client
  - Authentication approach used
  - Data structures and schemas
  - Any special implementation notes

**Use this information to guide your fixture generation!**

"""

        if research_summary:
            prompt += f"""## Research Summary (from ResearchAgent)

{research_summary}

"""

        if client_methods:
            prompt += f"""## Client Methods to Mock

The generated client has the following methods:
{chr(10).join(f"- {method}" for method in client_methods)}

"""

        prompt += """## Your Task (35-Turn Optimized Workflow)

**PHASE 1: Comprehensive Analysis (Turns 1-3)**
1. **READ IMPLEMENTATION.MD** - Understand what was actually generated
2. **READ ALL tests/test_*.py** - CRITICAL! Create complete fixture checklist
   - Find all `def test_*(..., fixture_name):` patterns
   - Extract EVERY fixture name tests expect
   - Understand what data format each fixture should return (dict, JSON, mock object)
   - Note ALL `mock_*` objects tests expect
   - **OUTPUT: Complete checklist before generating any fixtures!**
3. **READ src/client.py & src/auth.py** - See method signatures and auth structures

**PHASE 2: Smart Fixture Generation (Turns 4-7)**
4. Create 5-7 fixture JSON files based on checklist:
   - ALL authentication fixtures (service account AND oauth2 if both needed)
   - Success responses for EACH client method
   - ALL error responses tests expect (401, 403, 404, 429, 500)
   - Use IMPLEMENTATION.md + your knowledge (no online research yet)

**PHASE 3: Research-Based conftest.py (Turns 8-10)**
5. **RESEARCH mock libraries FIRST** (Turn 8)
   - For `mock_google_credentials`: Search "google.oauth2.credentials attributes"
   - For any mock: Search "{library} {class} required attributes"
   - Note: universe_domain, scopes, expiry, token_uri, etc.
6. **Generate comprehensive conftest.py** (Turn 9)
   - Use EXACT fixture names from Turn 2 checklist
   - Match data formats tests expect
   - Include ALL mock attributes from Turn 8 research
   - Create complete, realistic mock objects
7. **Validate conftest.py** (Turn 10): `python -m py_compile tests/conftest.py`

**PHASE 4: Validation (Turns 11-15) - DO NOT RUN TESTS**
8. **VALIDATE JSON FILES** (Turn 11): Check all fixtures are valid JSON
   - Use: `python -m json.tool fixtures/**/*.json`
   - DO NOT use pytest - that's the Tester agent's job
9. **REVIEW FIXTURES** (Turns 12-14): Manual fixture completeness check
10. **FINAL VALIDATION** (Turn 15): Verify conftest.py loads all fixtures correctly

**PHASE 5: Enhancement (Turns 16-30)**
11. Add missing fixtures, research API docs, polish fixtures

**PHASE 6: Final Validation (Turns 31-35)**
12. Run full test suite, fix edge cases, generate summary

**CRITICAL SUCCESS FACTORS:**
- Turn 2: Create complete fixture checklist (know ALL requirements)
- Turn 8: Research mock libraries BEFORE writing conftest.py
- Turn 11: Run tests IMMEDIATELY after conftest.py creation
- Turns 12-14: Fix issues based on test feedback
- Use all 35 turns: Be thorough, not rushed!
"""

        return prompt
