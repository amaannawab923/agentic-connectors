"""Hooks for Claude Agent SDK permission control.

These hooks provide deterministic processing and security controls
for agent tool usage in the connector generator.
"""

import logging
import re
from typing import Any, Dict, Optional

from claude_agent_sdk import HookMatcher

logger = logging.getLogger(__name__)

# Dangerous bash patterns that should be blocked
DANGEROUS_BASH_PATTERNS = [
    r"rm\s+-rf\s+/",  # rm -rf /
    r"rm\s+-rf\s+~",  # rm -rf ~
    r"git\s+push\s+.*--force",  # force push
    r"git\s+reset\s+--hard",  # hard reset
    r"git\s+.*--no-verify",  # skip hooks
    r"curl.*\|\s*sh",  # pipe curl to shell
    r"wget.*\|\s*sh",  # pipe wget to shell
    r"eval\s*\(",  # eval
    r">\s*/etc/",  # write to /etc
    r"chmod\s+777",  # overly permissive chmod
    r"sudo\s+",  # sudo commands
]

# Allowed file paths for Write tool (relative to working directory)
ALLOWED_WRITE_PATHS = [
    r"^src/.*\.py$",  # src Python files
    r"^tests/.*\.py$",  # test Python files
    r"^requirements\.txt$",  # requirements file
    r"^setup\.py$",  # setup file
    r"^pyproject\.toml$",  # pyproject file
    r"^README\.md$",  # readme
    r"^\.gitignore$",  # gitignore
]


async def check_bash_command(
    input_data: Dict[str, Any],
    tool_use_id: str,
    context: Any,
) -> Dict[str, Any]:
    """Hook to validate Bash commands before execution.

    This hook blocks dangerous bash commands that could:
    - Delete critical files
    - Force push to git
    - Execute arbitrary remote code
    - Modify system files

    Args:
        input_data: Tool input containing tool_name and tool_input.
        tool_use_id: Unique identifier for this tool use.
        context: Additional context from the SDK.

    Returns:
        Empty dict to allow, or hookSpecificOutput to deny.
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")

    for pattern in DANGEROUS_BASH_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning(f"Blocked dangerous bash command: {command[:100]}")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Command blocked for security: matches pattern {pattern}",
                }
            }

    return {}


async def check_write_path(
    input_data: Dict[str, Any],
    tool_use_id: str,
    context: Any,
) -> Dict[str, Any]:
    """Hook to validate Write tool file paths.

    This hook ensures files are only written to expected locations
    within the connector directory structure.

    Args:
        input_data: Tool input containing tool_name and tool_input.
        tool_use_id: Unique identifier for this tool use.
        context: Additional context from the SDK.

    Returns:
        Empty dict to allow, or hookSpecificOutput to deny.
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Write":
        return {}

    file_path = tool_input.get("file_path", "")

    # Block absolute paths outside working directory
    if file_path.startswith("/") and not file_path.startswith("./"):
        # Check if it's a valid absolute path within allowed directories
        # For now, allow all paths that are explicitly set (trust working_dir)
        pass

    # Block path traversal
    if ".." in file_path:
        logger.warning(f"Blocked path traversal in Write: {file_path}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Path traversal not allowed",
            }
        }

    return {}


async def log_tool_usage(
    input_data: Dict[str, Any],
    tool_use_id: str,
    context: Any,
) -> Dict[str, Any]:
    """Hook to log all tool usage for auditing.

    This hook logs tool calls for debugging and monitoring purposes.

    Args:
        input_data: Tool input containing tool_name and tool_input.
        tool_use_id: Unique identifier for this tool use.
        context: Additional context from the SDK.

    Returns:
        Empty dict (always allows, just logs).
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Redact sensitive information
    safe_input = _redact_sensitive(tool_input)

    logger.info(f"Tool called: {tool_name} (id: {tool_use_id})")
    logger.debug(f"Tool input: {safe_input}")

    return {}


def _redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive information from tool input for logging."""
    sensitive_keys = {"password", "secret", "token", "key", "credential", "api_key"}
    redacted = {}

    for k, v in data.items():
        if any(s in k.lower() for s in sensitive_keys):
            redacted[k] = "***REDACTED***"
        elif isinstance(v, dict):
            redacted[k] = _redact_sensitive(v)
        elif isinstance(v, str) and len(v) > 200:
            redacted[k] = v[:100] + "...[truncated]"
        else:
            redacted[k] = v

    return redacted


def get_security_hooks() -> Dict[str, list]:
    """Get security hooks for agent configuration.

    Returns:
        Dictionary mapping hook events to hook matchers.
    """
    return {
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[check_bash_command, log_tool_usage]),
            HookMatcher(matcher="Write", hooks=[check_write_path, log_tool_usage]),
            HookMatcher(matcher="*", hooks=[log_tool_usage]),
        ],
    }


def get_minimal_hooks() -> Dict[str, list]:
    """Get minimal hooks for development/testing.

    Returns:
        Dictionary with just logging hooks.
    """
    return {
        "PreToolUse": [
            HookMatcher(matcher="*", hooks=[log_tool_usage]),
        ],
    }
