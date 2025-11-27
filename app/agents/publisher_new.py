"""Reliable publisher agent using direct subprocess calls for Git operations.

This implementation doesn't rely on LLM to execute bash commands - it executes
them directly using Python subprocess for guaranteed execution.
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseAgent
from ..models.enums import AgentType
from ..models.schemas import AgentResult, GeneratedFile

logger = logging.getLogger(__name__)


class PublisherAgentNew(BaseAgent):
    """Reliable publisher agent that directly executes Git commands.

    Unlike the base publisher that relies on LLM to execute bash commands,
    this implementation uses Python subprocess to guarantee command execution.
    """

    agent_type = AgentType.PUBLISHER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name: Optional[str] = None
        self.commit_hash: Optional[str] = None

    def _run_git_command(
        self,
        command: str,
        cwd: str,
        check: bool = True,
        capture_output: bool = True,
    ) -> Tuple[bool, str, str]:
        """Execute a git command directly using subprocess.

        Args:
            command: The git command to execute
            cwd: Working directory
            check: Whether to raise on failure
            capture_output: Whether to capture stdout/stderr

        Returns:
            Tuple of (success, stdout, stderr)
        """
        logger.info(f"Executing: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            stdout = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""

            success = result.returncode == 0

            if stdout:
                logger.info(f"  Output: {stdout[:200]}...")
            if stderr and not success:
                logger.error(f"  Error: {stderr[:200]}...")

            if check and not success:
                raise subprocess.CalledProcessError(
                    result.returncode, command, stdout, stderr
                )

            return success, stdout, stderr

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return False, "", "Command timed out after 5 minutes"
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return False, "", str(e)

    async def execute(
        self,
        generated_files: List[GeneratedFile],
        connector_name: str,
        output_dir: str,
        repo_owner: str,
        repo_name: str,
        personal_access_token: str,
        branch_name: Optional[str] = None,
        repo_path: Optional[str] = None,
        create_pr: bool = False,
    ) -> AgentResult:
        """Execute Git publishing operations directly.

        Args:
            generated_files: Files to publish
            connector_name: Name of the connector
            output_dir: Directory containing the code
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            personal_access_token: GitHub PAT for authentication
            branch_name: Branch to push to (default: connector/<name>)
            repo_path: Path to git repository (default: output_dir)
            create_pr: Whether to create a PR (not implemented yet)

        Returns:
            AgentResult with success/failure details
        """
        start_time = time.time()
        self.reset_token_tracking()

        # Set defaults
        work_dir = repo_path or output_dir
        self.branch_name = branch_name or f"connector/{connector_name}"

        logger.info(f"Publishing connector: {connector_name}")
        logger.info(f"Work directory: {work_dir}")
        logger.info(f"Branch: {self.branch_name}")
        logger.info(f"Repository: {repo_owner}/{repo_name}")

        try:
            # Ensure work directory exists
            work_path = Path(work_dir)
            if not work_path.exists():
                return self._create_result(
                    success=False,
                    error=f"Directory does not exist: {work_dir}",
                    duration_seconds=time.time() - start_time,
                )

            # Step 1: Initialize Git repository
            logger.info("Step 1: Initializing Git repository")
            success, stdout, stderr = self._run_git_command(
                "git init",
                cwd=work_dir,
                check=False,
            )
            if not success:
                return self._create_result(
                    success=False,
                    error=f"Failed to initialize git: {stderr}",
                    duration_seconds=time.time() - start_time,
                )

            # Step 2: Configure Git user
            logger.info("Step 2: Configuring Git user")
            self._run_git_command(
                'git config user.name "Connector Generator"',
                cwd=work_dir,
            )
            self._run_git_command(
                'git config user.email "generator@connectors.ai"',
                cwd=work_dir,
            )

            # Step 3: Configure remote with token authentication
            logger.info("Step 3: Configuring remote")

            # Remove existing remote if present
            self._run_git_command(
                "git remote remove origin",
                cwd=work_dir,
                check=False,
            )

            # Add remote with token authentication
            remote_url = f"https://{personal_access_token}@github.com/{repo_owner}/{repo_name}.git"
            success, stdout, stderr = self._run_git_command(
                f"git remote add origin {remote_url}",
                cwd=work_dir,
            )
            if not success:
                return self._create_result(
                    success=False,
                    error=f"Failed to add remote: {stderr}",
                    duration_seconds=time.time() - start_time,
                )

            # Step 4: Create or checkout branch
            logger.info(f"Step 4: Creating/checking out branch: {self.branch_name}")

            # Try to create new branch
            success, stdout, stderr = self._run_git_command(
                f"git checkout -b {self.branch_name}",
                cwd=work_dir,
                check=False,
            )

            # If branch already exists, just checkout
            if not success and "already exists" in stderr:
                logger.info(f"Branch {self.branch_name} already exists, checking out")
                success, stdout, stderr = self._run_git_command(
                    f"git checkout {self.branch_name}",
                    cwd=work_dir,
                )
                if not success:
                    return self._create_result(
                        success=False,
                        error=f"Failed to checkout branch: {stderr}",
                        duration_seconds=time.time() - start_time,
                    )

            # Step 5: Stage all files
            logger.info("Step 5: Staging files")
            success, stdout, stderr = self._run_git_command(
                "git add .",
                cwd=work_dir,
            )
            if not success:
                return self._create_result(
                    success=False,
                    error=f"Failed to stage files: {stderr}",
                    duration_seconds=time.time() - start_time,
                )

            # Step 6: Check if there's anything to commit
            logger.info("Step 6: Checking git status")
            success, stdout, stderr = self._run_git_command(
                "git status --porcelain",
                cwd=work_dir,
            )

            if not stdout.strip():
                logger.info("Nothing to commit - working tree clean")
                # Still need to push if remote doesn't have our branch
                logger.info("Checking if remote has our branch")
                success, stdout, stderr = self._run_git_command(
                    f"git ls-remote --heads origin {self.branch_name}",
                    cwd=work_dir,
                    check=False,
                )

                if not stdout.strip():
                    logger.info("Remote doesn't have branch, will push")
                else:
                    return self._create_result(
                        success=True,
                        output=json.dumps({
                            "success": True,
                            "message": "No changes to commit - already up to date",
                            "branch_name": self.branch_name,
                            "remote_url": f"https://github.com/{repo_owner}/{repo_name}",
                        }),
                        duration_seconds=time.time() - start_time,
                    )

            # Step 7: Create commit
            if stdout.strip():  # Only commit if there are changes
                logger.info("Step 7: Creating commit")
                commit_message = f"""feat: add {connector_name} connector

Generated connector implementation for {connector_name}.

Features:
- Authentication support
- Rate limiting and retry logic
- Error handling
- Schema inference
- Full type hints and documentation

Generated with Connector Generator v1.0"""

                success, stdout, stderr = self._run_git_command(
                    f'git commit -m "{commit_message}"',
                    cwd=work_dir,
                )
                if not success:
                    return self._create_result(
                        success=False,
                        error=f"Failed to create commit: {stderr}",
                        duration_seconds=time.time() - start_time,
                    )

                # Get commit hash
                success, commit_hash, stderr = self._run_git_command(
                    "git rev-parse HEAD",
                    cwd=work_dir,
                )
                if success:
                    self.commit_hash = commit_hash
                    logger.info(f"Created commit: {commit_hash}")

            # Step 8: Push to GitHub
            logger.info(f"Step 8: Pushing to GitHub ({repo_owner}/{repo_name}:{self.branch_name})")
            success, stdout, stderr = self._run_git_command(
                f"git push -u origin {self.branch_name}",
                cwd=work_dir,
            )

            if not success:
                # Check if it's a permission error
                if "403" in stderr or "Permission denied" in stderr:
                    error_msg = (
                        "GitHub authentication failed (403 Forbidden). "
                        "Please check:\n"
                        "1. Your personal access token is valid and not expired\n"
                        "2. The token has 'repo' scope permissions\n"
                        "3. You have write access to the repository"
                    )
                elif "404" in stderr:
                    error_msg = (
                        f"Repository not found: {repo_owner}/{repo_name}. "
                        "Please check the repository exists and you have access."
                    )
                else:
                    error_msg = f"Failed to push to GitHub: {stderr}"

                return self._create_result(
                    success=False,
                    error=error_msg,
                    duration_seconds=time.time() - start_time,
                )

            logger.info("Successfully pushed to GitHub!")

            # Step 9: Create PR if requested (using gh CLI)
            pr_url = None
            if create_pr:
                logger.info("Step 9: Creating pull request")
                pr_title = f"Add {connector_name} connector"
                pr_body = f"""## Summary

This PR adds a new connector for **{connector_name}**.

## Changes

- New connector implementation
- Authentication support
- Rate limiting and retry logic
- Error handling
- Schema inference
- Full documentation

## Generated

🤖 Generated with Connector Generator v1.0"""

                success, stdout, stderr = self._run_git_command(
                    f'gh pr create --title "{pr_title}" --body "{pr_body}"',
                    cwd=work_dir,
                    check=False,
                )

                if success and stdout:
                    pr_url = stdout.strip()
                    logger.info(f"Created PR: {pr_url}")
                else:
                    logger.warning(f"Failed to create PR (gh CLI may not be available): {stderr}")

            # Build success response
            duration = time.time() - start_time

            result_data = {
                "success": True,
                "branch_name": self.branch_name,
                "remote_url": f"https://github.com/{repo_owner}/{repo_name}",
                "message": f"Successfully published to branch {self.branch_name}",
            }

            if self.commit_hash:
                result_data["commit_hash"] = self.commit_hash

            if pr_url:
                result_data["pr_url"] = pr_url

            return AgentResult(
                agent=self.agent_type,
                success=True,
                output=json.dumps(result_data),
                duration_seconds=duration,
                tokens_used=0,  # No LLM calls in this implementation
            )

        except Exception as e:
            logger.exception("Publisher failed with exception")
            return self._create_result(
                success=False,
                error=f"Unexpected error: {str(e)}",
                duration_seconds=time.time() - start_time,
            )

    def get_branch_name(self) -> Optional[str]:
        """Get the branch name that was pushed."""
        return self.branch_name

    def get_commit_hash(self) -> Optional[str]:
        """Get the commit hash that was created."""
        return self.commit_hash
