"""Base agent class using Claude Agent SDK.

This module provides the foundation for all agents in the connector generator,
using the official Claude Agent SDK for streaming responses and tool execution.
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
    SystemMessage,
)

from ..config import Settings, get_settings
from ..models.enums import AgentType
from ..models.schemas import AgentResult

logger = logging.getLogger(__name__)

# Enable more verbose logging for debugging
logging.getLogger("claude_agent_sdk").setLevel(logging.DEBUG)


def _truncate(text: str, max_len: int = 100) -> str:
    """Truncate text for logging with ellipsis."""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _format_tool_input(tool_name: str, tool_input: dict) -> str:
    """Format tool input for readable logging."""
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "unknown")
        content_len = len(tool_input.get("content", ""))
        return f"file={file_path} ({content_len} chars)"
    elif tool_name == "Read":
        return f"file={tool_input.get('file_path', 'unknown')}"
    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return f"cmd={_truncate(cmd, 60)}"
    elif tool_name == "Glob":
        return f"pattern={tool_input.get('pattern', '')}"
    elif tool_name == "Grep":
        return f"pattern={tool_input.get('pattern', '')} path={tool_input.get('path', '.')}"
    elif tool_name == "WebSearch":
        return f"query={tool_input.get('query', '')}"
    elif tool_name == "WebFetch":
        return f"url={_truncate(tool_input.get('url', ''), 60)}"
    else:
        # Generic fallback - show first few keys
        keys = list(tool_input.keys())[:3]
        return f"keys={keys}"


class BaseAgent(ABC):
    """Abstract base class for all agents using Claude Agent SDK.

    This class provides:
    - Streaming async responses via query()
    - Tool configuration via ClaudeAgentOptions
    - Token tracking and cost estimation
    - Error handling

    Subclasses must implement:
    - agent_type: The type of agent
    - system_prompt: The system prompt for the agent
    - execute(): The main execution method
    """

    agent_type: AgentType = AgentType.RESEARCH
    system_prompt: str = "You are a helpful AI assistant."

    def __init__(
        self,
        settings: Optional[Settings] = None,
        working_dir: Optional[str] = None,
    ):
        """Initialize the base agent.

        Args:
            settings: Application settings. Uses default if not provided.
            working_dir: Working directory for file operations.
        """
        self.settings = settings or get_settings()
        self.working_dir = working_dir or str(Path.cwd())

        # Token tracking for cost estimation
        self.total_tokens_used: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.call_count: int = 0
        self.total_cost: float = 0.0

        # Get agent-specific options
        agent_name = self.agent_type.value.lower() if hasattr(self.agent_type, 'value') else str(self.agent_type).lower()
        self._agent_options = self.settings.get_agent_options(agent_name)

    def _create_options(
        self,
        additional_tools: Optional[List[str]] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> ClaudeAgentOptions:
        """Create ClaudeAgentOptions for this agent.

        Args:
            additional_tools: Additional tools to allow beyond defaults.
            custom_system_prompt: Override the default system prompt.

        Returns:
            Configured ClaudeAgentOptions instance.
        """
        allowed_tools = list(self._agent_options.get("allowed_tools", []))

        if additional_tools:
            allowed_tools.extend(additional_tools)

        return ClaudeAgentOptions(
            model=self.settings.claude_model,
            system_prompt=custom_system_prompt or self.system_prompt,
            max_turns=self._agent_options.get("max_turns", 50),
            allowed_tools=allowed_tools if allowed_tools else None,
            cwd=self.working_dir,
        )

    async def _stream_response(
        self,
        prompt: str,
        options: Optional[ClaudeAgentOptions] = None,
    ) -> str:
        """Stream a response from Claude using the SDK.

        Uses the query() function from claude-agent-sdk which returns
        an async iterator of Message objects.

        Args:
            prompt: The prompt to send to Claude.
            options: Optional ClaudeAgentOptions. Uses agent defaults if not provided.

        Returns:
            The complete response text (from ResultMessage.result).

        Raises:
            Exception: If there's an error during the query.
        """
        import asyncio

        if options is None:
            options = self._create_options()

        logger.info(f"[AGENT] Starting query with prompt length: {len(prompt)} chars")
        logger.info(f"[AGENT] Options: max_turns={options.max_turns}, allowed_tools={options.allowed_tools}")

        # Run the SDK query in a separate thread to avoid event loop conflicts with uvicorn
        def run_sync_query():
            """Run the SDK query synchronously in a thread."""
            import asyncio

            async def _query():
                start_time = time.time()
                message_count = 0
                turn_count = 0
                tool_calls = []
                files_written = []
                final_result = None
                accumulated_text = []  # Accumulate all assistant text blocks

                logger.info("=" * 60)
                logger.info("[AGENT] Starting agent execution...")
                logger.info("=" * 60)

                async for message in query(prompt=prompt, options=options):
                    message_count += 1
                    elapsed = time.time() - start_time
                    msg_type = type(message).__name__

                    # Log every message type for debugging
                    logger.info(f"[{elapsed:6.1f}s] >>> Received: {msg_type}, {message}")

                    if isinstance(message, SystemMessage):
                        subtype = getattr(message, 'subtype', 'unknown')
                        logger.info(f"           SYSTEM: {subtype}")
                        if hasattr(message, 'data') and message.data:
                            if 'session_id' in message.data:
                                logger.info(f"           Session: {message.data['session_id'][:20]}...")

                    elif isinstance(message, AssistantMessage):
                        turn_count += 1
                        num_blocks = len(message.content) if message.content else 0
                        logger.info(f"[{elapsed:6.1f}s] TURN {turn_count}: {num_blocks} content blocks")

                        for i, block in enumerate(message.content or []):
                            if isinstance(block, TextBlock):
                                # Log agent's thinking/explanation (truncated)
                                text = getattr(block, 'text', '')
                                if text:
                                    accumulated_text.append(text)  # Accumulate text
                                    preview = _truncate(text, 120)
                                    logger.info(f"           THINKING: {preview}")
                            elif isinstance(block, ToolUseBlock):
                                # Log tool usage with formatted input
                                tool_name = getattr(block, 'name', 'unknown')
                                tool_input = getattr(block, 'input', {}) or {}
                                tool_calls.append(tool_name)
                                formatted = _format_tool_input(tool_name, tool_input)
                                logger.info(f"           TOOL: {tool_name} -> {formatted}")

                                # Track files being written
                                if tool_name == "Write":
                                    file_path = tool_input.get("file_path", "")
                                    if file_path:
                                        files_written.append(file_path)
                                        logger.info(f"           >>> Writing file: {file_path}")

                    elif isinstance(message, ToolResultBlock):
                        # Log tool execution results
                        tool_id = getattr(message, 'tool_use_id', 'unknown')
                        is_error = getattr(message, 'is_error', False)
                        content = getattr(message, 'content', '')
                        status = "ERROR" if is_error else "OK"

                        if isinstance(content, str):
                            preview = _truncate(content, 80)
                        elif isinstance(content, list):
                            preview = f"[{len(content)} items]"
                        else:
                            preview = str(type(content))

                        logger.info(f"[{elapsed:6.1f}s] RESULT ({status}): {preview}")

                    elif isinstance(message, ResultMessage):
                        logger.info("=" * 60)
                        logger.info(f"[{elapsed:6.1f}s] COMPLETED")
                        if hasattr(message, 'total_cost_usd') and message.total_cost_usd:
                            logger.info(f"           Cost: ${message.total_cost_usd:.4f}")
                        if hasattr(message, 'result') and message.result:
                            final_result = message.result
                            logger.info(f"           Result: {len(final_result)} chars")
                        logger.info("=" * 60)

                    elif msg_type == 'StreamEvent':
                        # Handle streaming events - these contain real-time updates
                        event = getattr(message, 'event', None)
                        if event:
                            event_type = getattr(event, 'type', None)

                            # content_block_start - new block starting
                            if event_type == 'content_block_start':
                                block = getattr(event, 'content_block', None)
                                if block:
                                    block_type = getattr(block, 'type', 'unknown')
                                    if block_type == 'tool_use':
                                        tool_name = getattr(block, 'name', 'unknown')
                                        logger.info(f"[{elapsed:6.1f}s] STARTING: Tool '{tool_name}'")
                                    elif block_type == 'text':
                                        logger.info(f"[{elapsed:6.1f}s] STARTING: Text response")

                            # content_block_delta - incremental content
                            elif event_type == 'content_block_delta':
                                delta = getattr(event, 'delta', None)
                                if delta:
                                    delta_type = getattr(delta, 'type', None)
                                    if delta_type == 'text_delta':
                                        text = getattr(delta, 'text', '')
                                        if text and len(text) > 20:
                                            # Only log substantial text chunks
                                            preview = _truncate(text, 80)
                                            logger.info(f"[{elapsed:6.1f}s] TEXT: {preview}")
                                    elif delta_type == 'input_json_delta':
                                        # Tool input being streamed - check for file paths
                                        partial = getattr(delta, 'partial_json', '')
                                        if 'file_path' in partial:
                                            logger.info(f"[{elapsed:6.1f}s] WRITING: {_truncate(partial, 100)}")

                            # content_block_stop - block finished
                            elif event_type == 'content_block_stop':
                                pass  # Don't log stop events to reduce noise

                            # message_start, message_delta, message_stop
                            elif event_type in ('message_start', 'message_stop'):
                                pass  # Skip these to reduce noise

                            else:
                                # Log other event types for debugging
                                logger.debug(f"[{elapsed:6.1f}s] STREAM: {event_type}")

                    else:
                        # Log any other message types - make it visible!
                        logger.info(f"[{elapsed:6.1f}s] UNHANDLED: {msg_type}")
                        # Try to print attributes for debugging
                        attrs = [a for a in dir(message) if not a.startswith('_')]
                        logger.debug(f"           Attributes: {attrs[:10]}")

                duration = time.time() - start_time
                logger.info(f"[AGENT] Summary: {duration:.1f}s, {turn_count} turns, {len(tool_calls)} tool calls")
                if files_written:
                    logger.info(f"[AGENT] Files written: {len(files_written)}")
                    for f in files_written:
                        logger.info(f"        - {f}")

                # Use final_result if available, otherwise use accumulated text
                if final_result:
                    logger.info(f"[AGENT] Using ResultMessage.result ({len(final_result)} chars)")
                    return final_result
                elif accumulated_text:
                    combined = "\n\n".join(accumulated_text)
                    logger.info(f"[AGENT] Using accumulated text ({len(combined)} chars from {len(accumulated_text)} blocks)")
                    return combined
                else:
                    logger.warning("[AGENT] No response captured - both final_result and accumulated_text are empty")
                    return ""

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_query())
            finally:
                loop.close()

        try:
            # Run in thread pool to avoid event loop conflicts
            result = await asyncio.to_thread(run_sync_query)
            self.call_count += 1
            return result

        except Exception as e:
            logger.error(f"[AGENT] Error: {e}")
            import traceback
            logger.error(f"[AGENT] Traceback: {traceback.format_exc()}")
            raise

    def estimate_cost(self) -> float:
        """Get the actual cost from SDK tracking.

        Returns:
            Total cost in USD from ResultMessage.
        """
        return self.total_cost

    def reset_token_tracking(self) -> None:
        """Reset token tracking counters."""
        self.total_tokens_used = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.call_count = 0
        self.total_cost = 0.0

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this agent.

        Returns:
            Dictionary with usage statistics.
        """
        return {
            "agent_type": self.agent_type.value,
            "call_count": self.call_count,
            "total_cost_usd": self.total_cost,
        }

    @abstractmethod
    async def execute(self, **kwargs) -> AgentResult:
        """Execute the agent's main task.

        This method must be implemented by subclasses to define
        the specific behavior of each agent type.

        Returns:
            AgentResult containing the outcome of the execution.
        """
        pass

    def _create_result(
        self,
        success: bool,
        output: Optional[str] = None,
        error: Optional[str] = None,
        duration_seconds: float = 0.0,
    ) -> AgentResult:
        """Create a standardized AgentResult.

        Args:
            success: Whether the execution was successful.
            output: The output string if successful.
            error: The error message if failed.
            duration_seconds: How long the execution took.

        Returns:
            Configured AgentResult instance.
        """
        return AgentResult(
            agent=self.agent_type,
            success=success,
            output=output,
            error=error,
            duration_seconds=duration_seconds,
            tokens_used=self.total_tokens_used,
        )
