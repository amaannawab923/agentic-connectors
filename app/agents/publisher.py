"""Publisher agent for pushing connector code to GitHub.

Uses Claude Agent SDK with Bash tool for git operations.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from ..models.enums import AgentType
from ..models.schemas import AgentResult, GeneratedFile

logger = logging.getLogger(__name__)


class PublisherAgent(BaseAgent):
    """Agent that publishes connector code to GitHub.

    This agent uses Claude Agent SDK with:
    - Built-in Bash tool for git commands
    - GitHub CLI (gh) for PR creation
    - Safe git operations with verification
    """

    agent_type = AgentType.PUBLISHER

    system_prompt = """You are a DevOps engineer responsible for publishing code to GitHub.
Your task is to safely commit and push connector code and create a pull request.

Use the Bash tool to:
1. Check git status
2. Create a new branch: git checkout -b connector/<name>
3. Stage files: git add <files>
4. Commit with a descriptive message
5. Push to remote: git push -u origin <branch>
6. Create PR using: gh pr create --title "..." --body "..."

IMPORTANT SAFETY RULES:
- NEVER run destructive git commands (hard reset, force push to main)
- NEVER skip commit hooks (--no-verify)
- Always verify branch before pushing
- Use descriptive commit messages

Output the PR URL when complete, or the branch name if PR creation fails."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name: Optional[str] = None
        self.pr_url: Optional[str] = None

    async def execute(
        self,
        generated_files: List[GeneratedFile],
        connector_name: str,
        output_dir: str,
        repo_path: Optional[str] = None,
        create_pr: bool = True,
    ) -> AgentResult:
        """Execute the publisher agent.

        Args:
            generated_files: List of generated code files.
            connector_name: Name of the connector.
            output_dir: Directory containing the connector code.
            repo_path: Path to the git repository (if different from output_dir).
            create_pr: Whether to create a pull request.

        Returns:
            AgentResult with PR URL if successful.
        """
        start_time = time.time()
        self.reset_token_tracking()

        # Determine working directory
        work_dir = repo_path or output_dir
        self.working_dir = work_dir
        self.branch_name = f"connector/{connector_name}"

        # Ensure output directory exists and has the files
        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
            for gen_file in generated_files:
                file_path = output_path / gen_file.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(gen_file.content)

        # Build the publish prompt
        prompt = self._build_publish_prompt(
            connector_name=connector_name,
            output_dir=output_dir,
            repo_path=repo_path,
            create_pr=create_pr,
        )

        try:
            # Create options with Bash tool enabled
            options = self._create_options()

            # Stream the publish response
            response = await self._stream_response(prompt, options)

            # Parse PR URL from response
            self.pr_url = self._extract_pr_url(response)

            duration = time.time() - start_time

            output = self.pr_url or f"Code committed to branch: {self.branch_name}"

            return self._create_result(
                success=True,
                output=output,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.exception("Publisher agent failed")
            return self._create_result(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _build_publish_prompt(
        self,
        connector_name: str,
        output_dir: str,
        repo_path: Optional[str],
        create_pr: bool,
    ) -> str:
        """Build the publish prompt."""
        branch_name = f"connector/{connector_name}"

        prompt = f"""# Publish Connector Code

Publish the generated connector code for **{connector_name}**.

## Configuration
- Connector directory: {output_dir}
- Repository path: {repo_path or output_dir}
- Branch name: {branch_name}
- Create PR: {"Yes" if create_pr else "No"}

## Steps

1. **Check Git Status**
   ```bash
   git status
   ```

2. **Create Branch** (if it doesn't exist)
   ```bash
   git checkout -b {branch_name} || git checkout {branch_name}
   ```

3. **Stage Connector Files**
   ```bash
   git add {output_dir}
   ```

4. **Create Commit**
   ```bash
   git commit -m "Add {connector_name} connector

Generated connector implementation for {connector_name}.

Features:
- Authentication support
- Rate limiting
- Error handling
- Schema inference

Generated with Connector Generator"
   ```

5. **Push to Remote**
   ```bash
   git push -u origin {branch_name}
   ```
"""

        if create_pr:
            prompt += f"""
6. **Create Pull Request**
   ```bash
   gh pr create --title "Add {connector_name} connector" --body "## Summary

This PR adds a new connector for **{connector_name}**.

## Changes

- New connector implementation in \`{output_dir}/\`
- Authentication support (OAuth2, API Key, Service Account)
- Rate limiting and retry logic
- Error handling
- Schema inference

## Checklist

- [ ] Code review completed
- [ ] Tests passing
- [ ] Documentation updated

---
Generated with Connector Generator"
   ```
"""

        prompt += """
## Output

Report:
1. The branch name created
2. Files committed
3. Push status
4. PR URL (if created)

If any step fails, report the error and what was accomplished.
"""

        return prompt

    def _extract_pr_url(self, response: str) -> Optional[str]:
        """Extract PR URL from response."""
        import re

        # Look for GitHub PR URL pattern
        pr_patterns = [
            r'https://github\.com/[^/]+/[^/]+/pull/\d+',
            r'PR URL:\s*(https://[^\s]+)',
            r'Pull request:\s*(https://[^\s]+)',
        ]

        for pattern in pr_patterns:
            match = re.search(pattern, response)
            if match:
                return match.group(0) if match.lastindex is None else match.group(1)

        return None

    def get_pr_url(self) -> Optional[str]:
        """Get the created PR URL."""
        return self.pr_url

    def get_branch_name(self) -> Optional[str]:
        """Get the created branch name."""
        return self.branch_name
