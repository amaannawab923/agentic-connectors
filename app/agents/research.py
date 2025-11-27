"""Research agent for gathering connector implementation patterns.

Uses Claude Agent SDK for research and documentation analysis.
"""

import logging
import time
from typing import Optional

from .base import BaseAgent
from ..models.enums import AgentType
from ..models.schemas import AgentResult

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Agent that researches connector implementation patterns.

    This agent uses Claude Agent SDK to:
    - Analyze connector requirements
    - Research API patterns and best practices
    - Search open source connector repos (Airbyte, Meltano, Singer)
    - Generate comprehensive research documentation
    """

    agent_type = AgentType.RESEARCH

    system_prompt = """You are an expert software engineer specializing in data connector development.
Your task is to research and analyze connector implementations to extract best practices,
patterns, and implementation details.

You have access to tools to search the web and fetch documentation. Use them to:
1. Find the official API documentation for the service
2. Search GitHub for existing connector implementations in:
   - airbytehq/airbyte repository (source connectors)
   - Meltano extractors
   - Singer.io taps
   - Other open source data connector projects
3. Analyze authentication patterns, rate limits, and error handling

When researching, focus on:
1. Authentication patterns (OAuth2, API keys, service accounts)
2. Rate limiting and retry strategies
3. Error handling approaches
4. Pagination implementations
5. Schema inference patterns
6. Configuration requirements
7. Testing strategies

## 🚨 CRITICAL: API Token/Key Format Research

**ALWAYS research the CURRENT token/API key format:**

1. **Search for Recent Changes**:
   - Query: "{API_NAME} API token format 2024 2025"
   - Query: "{API_NAME} API key format change"
   - Query: "{API_NAME} authentication token prefix"

2. **Check Official Changelog**:
   - Look for API changelog or release notes
   - Note ANY token format changes in the last 2 years
   - Document ALL valid token prefixes/formats

3. **Document ALL Valid Formats**:
   - If tokens changed format (e.g., `secret_` → `ntn_`), document BOTH
   - Note: "As of [DATE], tokens use format X"
   - Note: "Legacy tokens use format Y (still supported)"
   - Example: "Notion tokens: `secret_*` (pre-Sept 2024) and `ntn_*` (Sept 2024+)"

4. **Follow Vendor Guidance**:
   - If vendor says "treat as opaque string", note that prominently
   - If vendor says "don't validate format", FLAG THIS for Generator
   - Example: Notion says "don't use regex to validate tokens"

5. **Required Output in Authentication Section**:
   ```markdown
   ### Token Format (CRITICAL)

   **Current Format** (as of YYYY-MM-DD):
   - Prefix: `xyz_`
   - Length: ~50 characters
   - Example: `xyz_1234567890abcdef...`

   **Legacy Formats** (still supported):
   - Old prefix: `abc_` (deprecated but valid)

   **Validation Guidance**:
   - ⚠️ [VENDOR SAYS: "Treat as opaque string, don't validate format"]
   - ✅ Recommended: Only validate minimum length
   - ❌ Do NOT hardcode prefix validation (format may change)
   ```

**WHY THIS MATTERS**: API providers frequently change token formats for security reasons.
Hardcoding format validation breaks when APIs evolve. Your research MUST capture current
state AND any recent changes.

Provide detailed, actionable information that can be used to implement a production-ready connector.
Include code examples where relevant.

Output your research as a comprehensive markdown document with these sections:
1. Executive Summary
2. API Overview
3. Authentication Patterns (**MUST include Token Format subsection with recent changes**)
4. Error Handling
5. Rate Limiting & Pagination
6. Configuration Schema
7. File Structure
8. Code Samples
9. Known Issues & Limitations
10. References (include changelog URLs)
"""

    async def execute(
        self,
        connector_name: str,
        additional_context: Optional[str] = None,
    ) -> AgentResult:
        """Execute the research agent.

        Args:
            connector_name: Natural name of the connector (e.g., 'Google Sheets', 'Stripe').
            additional_context: Any additional context or requirements for the research.

        Returns:
            AgentResult with research document.
        """
        start_time = time.time()
        self.reset_token_tracking()

        # Build the research prompt
        prompt = self._build_research_prompt(
            connector_name=connector_name,
            additional_context=additional_context,
        )

        # Create options with enough turns to research AND compile the final document
        from claude_agent_sdk import ClaudeAgentOptions
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            max_turns=15,  # Enough for research (5-8 turns) + final document compilation
            allowed_tools=["WebSearch", "WebFetch", "Read"],
            cwd=self.working_dir,
        )

        try:
            # Get research response from Claude
            logger.info(f"Starting research for {connector_name} with max_turns=10")
            research_doc = await self._stream_response(prompt, options=options)

            duration = time.time() - start_time
            logger.info(f"Research completed for {connector_name} in {duration:.1f}s")

            return self._create_result(
                success=True,
                output=research_doc,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.exception("Research agent failed")
            return self._create_result(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _build_research_prompt(
        self,
        connector_name: str,
        additional_context: Optional[str],
    ) -> str:
        """Build the research prompt."""
        # Convert natural name to slug for repo searching
        connector_slug = connector_name.lower().replace(" ", "-").replace("_", "-")

        prompt = f"""# Research Task: {connector_name} Connector

Research implementation patterns for a **{connector_name}** source connector.

## Quick Research Steps (do these efficiently in 2-3 searches)

1. **Search once** for "{connector_name} API authentication rate limits documentation"
2. **Search once** for "airbyte source-{connector_slug} OR tap-{connector_slug} github"
3. **Fetch the official API docs** if you find them

## Key Information Needed

- **Authentication**: How to authenticate (OAuth2, API key, service account)
- **Rate Limits**: Requests per minute/day, how to handle 429 errors
- **Pagination**: How the API handles large result sets
- **Key Endpoints**: Main data endpoints to extract data from
- **Error Codes**: Common errors and how to handle them

## Connector Info
- Name: {connector_name}
- Slug: {connector_slug}
- Type: source
"""

        if additional_context:
            prompt += f"""
## Additional Context
{additional_context}
"""

        prompt += """
## Output Format

Provide a concise markdown document with:

1. **Executive Summary** (2-3 sentences)
2. **Authentication** - How to authenticate with code example
3. **Key Endpoints** - List main endpoints with descriptions
4. **Rate Limits** - Limits and retry strategy
5. **Pagination** - How to paginate results
6. **Error Handling** - Key error codes
7. **Python Code Example** - Working authentication + basic API call

Keep it focused and actionable. Don't over-research - provide practical implementation guidance.
"""

        return prompt
