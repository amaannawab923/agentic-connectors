"""Code review agent for validating connector quality.

Uses Claude Agent SDK with Read tool for code analysis.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from ..models.enums import AgentType, ReviewDecision
from ..models.schemas import AgentResult, ReviewResult, ReviewComment, GeneratedFile

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent):
    """Agent that reviews generated connector code.

    This agent uses Claude Agent SDK with:
    - Built-in Read tool for code analysis
    - Structured JSON output for review results
    - LLM-as-judge pattern for code quality
    """

    agent_type = AgentType.REVIEWER

    system_prompt = """You are a senior software engineer conducting a thorough code review.

Your review should evaluate:

1. **Code Quality**
   - Readability and clarity
   - Naming conventions
   - Code organization
   - DRY principle adherence

2. **Type Safety**
   - Complete type hints
   - Proper use of Optional, Union, etc.
   - Pydantic model usage

3. **Error Handling**
   - Custom exceptions
   - Proper error propagation
   - Meaningful error messages
   - Retry logic

4. **Security**
   - No hardcoded credentials
   - Proper secret handling
   - Input validation
   - No sensitive data in logs

5. **Architecture**
   - Separation of concerns
   - Modularity
   - Clean interfaces
   - Testability

6. **Documentation**
   - Docstrings
   - Comments where needed
   - Clear APIs

Provide specific, actionable feedback with file paths and line references.
Rate the code from 0-10 and decide if it's approved or needs work.

Output your review in JSON format:
```json
{
    "decision": "approved" | "needs_work" | "rejected",
    "score": <0-10>,
    "summary": "brief summary",
    "comments": [
        {
            "file": "path/to/file.py",
            "line": <number or null>,
            "severity": "info" | "warning" | "error",
            "message": "comment message",
            "suggestion": "suggested fix or null"
        }
    ],
    "improvements_required": ["improvement 1", "improvement 2"]
}
```"""

    async def execute(
        self,
        generated_files: List[GeneratedFile],
        connector_name: str,
        test_passed: bool = True,
    ) -> AgentResult:
        """Execute the reviewer agent.

        Args:
            generated_files: List of generated code files.
            connector_name: Name of the connector.
            test_passed: Whether tests have passed.

        Returns:
            AgentResult with review results.
        """
        start_time = time.time()
        self.reset_token_tracking()

        # Build the review prompt with code
        prompt = self._build_review_prompt(
            generated_files=generated_files,
            connector_name=connector_name,
            test_passed=test_passed,
        )

        try:
            # Create options - only needs Read tool for examining code
            options = self._create_options()

            # Stream the review response
            response = await self._stream_response(prompt, options)

            # Parse the review result
            review_result = self._parse_review_response(response)

            duration = time.time() - start_time

            return AgentResult(
                agent=self.agent_type,
                success=True,
                output=json.dumps(review_result.model_dump()),
                duration_seconds=duration,
                tokens_used=self.total_tokens_used,
            )

        except Exception as e:
            logger.exception("Reviewer agent failed")
            return self._create_result(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _build_review_prompt(
        self,
        generated_files: List[GeneratedFile],
        connector_name: str,
        test_passed: bool,
    ) -> str:
        """Build the code review prompt."""
        prompt = f"""# Code Review Request

Please review the following connector code for **{connector_name}**.

**Test Status**: {"PASSED" if test_passed else "FAILED"}

## Files to Review

"""
        for gen_file in generated_files:
            if gen_file.path.endswith(".py"):
                prompt += f"""
### {gen_file.path}

```python
{gen_file.content}
```

"""

        prompt += """
## Review Instructions

Analyze the code thoroughly and provide your review in JSON format.

## Review Criteria

- **Score 8-10**: Excellent code, ready for production
- **Score 6-7**: Good code, minor improvements needed
- **Score 4-5**: Acceptable, but needs work before production
- **Score 0-3**: Significant issues, major rework needed

**Approved** if score >= 7 and no critical issues.
**Needs Work** if score 4-6 or has important issues to fix.
**Rejected** if score < 4 or has security/critical issues.

Focus on actionable feedback that can be implemented.
Output your review as JSON.
"""
        return prompt

    def _parse_review_response(self, response: str) -> ReviewResult:
        """Parse the review response from Claude."""
        try:
            # Find JSON block in response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # Parse comments
                comments = []
                for c in data.get("comments", []):
                    comments.append(ReviewComment(
                        file=c.get("file", "unknown"),
                        line=c.get("line"),
                        severity=c.get("severity", "info"),
                        message=c.get("message", ""),
                        suggestion=c.get("suggestion"),
                    ))

                # Determine decision
                decision_str = data.get("decision", "needs_work").lower()
                if decision_str == "approved":
                    decision = ReviewDecision.APPROVED
                elif decision_str == "rejected":
                    decision = ReviewDecision.REJECTED
                else:
                    decision = ReviewDecision.NEEDS_WORK

                return ReviewResult(
                    decision=decision,
                    approved=decision == ReviewDecision.APPROVED,
                    score=float(data.get("score", 5.0)),
                    comments=comments,
                    summary=data.get("summary", ""),
                    improvements_required=data.get("improvements_required", []),
                )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse JSON from review response: {e}")

        # Fallback: create a basic review result from text
        return ReviewResult(
            decision=ReviewDecision.NEEDS_WORK,
            approved=False,
            score=5.0,
            summary=response[:500],
            improvements_required=["Review response could not be parsed - manual review needed"],
        )

    def get_improvement_suggestions(self, review_result: ReviewResult) -> List[str]:
        """Extract improvement suggestions from review result.

        Args:
            review_result: The review result.

        Returns:
            List of improvement suggestions.
        """
        suggestions = review_result.improvements_required.copy()

        # Add suggestions from comments
        for comment in review_result.comments:
            if comment.severity in ["warning", "error"] and comment.suggestion:
                suggestions.append(f"{comment.file}: {comment.suggestion}")

        return suggestions
