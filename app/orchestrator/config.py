"""Configuration for the orchestrator v2.

Native LangGraph async implementation without Celery.
Supports persistent checkpointing via SQLite or PostgreSQL.
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings


class OrchestratorSettings(BaseSettings):
    """Settings for the orchestrator v2."""

    # ─────────────────────────────────────────────────────────────
    # Checkpointing Configuration
    # ─────────────────────────────────────────────────────────────
    # Type of checkpointer: "memory", "sqlite", or "postgres"
    checkpointer_type: Literal["memory", "sqlite", "postgres"] = "sqlite"

    # SQLite database path (relative to working directory)
    sqlite_db_path: str = "orchestrator_checkpoints.db"

    # PostgreSQL connection URL
    # Format: postgresql://user:password@host:port/database
    postgres_url: Optional[str] = None

    # ─────────────────────────────────────────────────────────────
    # Pipeline v2 Retry Configuration
    # ─────────────────────────────────────────────────────────────
    # TestReviewer -> Tester (invalid tests)
    max_test_retries: int = 3

    # TestReviewer -> Generator (valid tests, code fails)
    max_gen_fix_retries: int = 3

    # Reviewer -> Generator (REJECT:CODE)
    max_review_retries: int = 2

    # Reviewer -> Research (REJECT:CONTEXT)
    max_research_retries: int = 1

    # ─────────────────────────────────────────────────────────────
    # Mock task durations (for testing)
    # ─────────────────────────────────────────────────────────────
    mock_research_duration: int = 10  # seconds
    mock_generator_duration: int = 15
    mock_tester_duration: int = 8
    mock_reviewer_duration: int = 6
    mock_publisher_duration: int = 5

    # ─────────────────────────────────────────────────────────────
    # Pipeline Execution Settings
    # ─────────────────────────────────────────────────────────────
    # Maximum concurrent pipelines
    max_concurrent_pipelines: int = 10

    # Pipeline timeout (seconds)
    pipeline_timeout: int = 1200  # 20 minutes

    class Config:
        env_prefix = "ORCHESTRATOR_"
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env that don't belong to this class


settings = OrchestratorSettings()
