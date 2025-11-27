"""Configuration settings for the Connector Generator using Claude Agent SDK."""

from datetime import timezone, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Configured for Claude Agent SDK integration with proper
    permission modes, tool allowlists, and context management.
    """

    # API Settings
    app_name: str = "Connector Generator"
    app_version: str = "1.0.0"
    debug: bool = False

    # Claude Agent SDK Settings
    claude_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use"
    )
    max_turns: int = Field(
        default=50,
        description="Maximum conversation turns per agent"
    )
    tester_max_turns: int = Field(
        default=40,
        description="Maximum turns for tester agent (reduced to prevent infinite mocking loops)"
    )
    permission_mode: str = Field(
        default="acceptEdits",
        description="Permission mode: 'default', 'acceptEdits', 'bypassPermissions'"
    )

    # Agent Tool Allowlists
    research_allowed_tools: List[str] = Field(
        default=["Read", "WebFetch", "WebSearch", "Bash"],
        description="Tools allowed for research agent"
    )
    generator_allowed_tools: List[str] = Field(
        default=["Read", "Write", "Bash"],
        description="Tools allowed for generator agent"
    )
    tester_allowed_tools: List[str] = Field(
        default=["Read", "Write", "Bash", "WebSearch", "WebFetch"],
        description="Tools allowed for tester agent"
    )
    reviewer_allowed_tools: List[str] = Field(
        default=["Read"],
        description="Tools allowed for reviewer agent"
    )
    publisher_allowed_tools: List[str] = Field(
        default=["Read", "Bash"],
        description="Tools allowed for publisher agent"
    )
    mock_generator_allowed_tools: List[str] = Field(
        default=["Read", "Write", "Bash", "WebSearch", "WebFetch"],
        description="Tools allowed for mock generator agent"
    )
    mock_generator_max_turns: int = Field(
        default=35,
        description="Maximum turns for mock generator agent"
    )

    # Budget Settings (per connector)
    max_budget: float = Field(
        default=7.00,
        description="Maximum budget in USD per connector generation"
    )
    warning_threshold: float = Field(
        default=5.00,
        description="Budget threshold to trigger warnings"
    )
    force_publish_threshold: float = Field(
        default=6.00,
        description="Budget threshold to force publish"
    )

    # Pipeline Settings
    max_test_retries: int = Field(default=3, description="Maximum test retry attempts")
    max_review_cycles: int = Field(default=2, description="Maximum review cycles")

    # GitHub Settings
    github_token: Optional[SecretStr] = Field(
        default=None,
        description="GitHub personal access token for publishing"
    )
    github_repo_owner: str = Field(
        default="",
        description="GitHub repository owner"
    )
    github_repo_name: str = Field(
        default="connectors",
        description="GitHub repository name"
    )
    github_base_branch: str = Field(
        default="main",
        description="Base branch for PRs"
    )

    # Output Settings
    output_base_dir: str = Field(
        default="./generated",
        description="Directory to store generated connectors"
    )
    templates_dir: str = Field(
        default="./templates",
        description="Directory containing connector templates"
    )

    # Agent Cost Configuration (estimated costs in USD)
    cost_per_research: float = Field(default=0.60, description="Cost per research operation")
    cost_per_generation: float = Field(default=0.80, description="Cost per generation operation")
    cost_per_test: float = Field(default=0.10, description="Cost per test operation")
    cost_per_review: float = Field(default=0.13, description="Cost per review operation")
    token_cost_per_million: float = Field(default=9.0, description="Average cost per million tokens")

    # CORS Settings (for production)
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # Redis Settings (for job queue - future use)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def get_cost_config(self) -> Dict[str, float]:
        """Get cost configuration as dictionary."""
        return {
            "research": self.cost_per_research,
            "generation": self.cost_per_generation,
            "test": self.cost_per_test,
            "review": self.cost_per_review,
        }

    def get_agent_options(self, agent_type: str) -> Dict[str, Any]:
        """Get Claude Agent SDK options for a specific agent type.

        Args:
            agent_type: One of 'research', 'generator', 'mock_generator', 'tester', 'reviewer', 'publisher'

        Returns:
            Dictionary of options for ClaudeAgentOptions
        """
        tool_mapping = {
            "research": self.research_allowed_tools,
            "generator": self.generator_allowed_tools,
            "mock_generator": self.mock_generator_allowed_tools,
            "tester": self.tester_allowed_tools,
            "reviewer": self.reviewer_allowed_tools,
            "publisher": self.publisher_allowed_tools,
        }

        # Use agent-specific max_turns
        if agent_type == "tester":
            max_turns = self.tester_max_turns
        elif agent_type == "mock_generator":
            max_turns = self.mock_generator_max_turns
        else:
            max_turns = self.max_turns

        return {
            "max_turns": max_turns,
            "permission_mode": self.permission_mode,
            "allowed_tools": tool_mapping.get(agent_type, []),
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
