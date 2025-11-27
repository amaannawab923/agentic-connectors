"""
Configuration models for the Notion source connector.

This module defines Pydantic models for validating and managing
connector configuration, including authentication credentials.
"""

from datetime import datetime
from typing import Literal, Optional, Union, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Credential Models
# =============================================================================


class TokenCredentials(BaseModel):
    """
    Configuration for internal integration token authentication.

    Internal integration tokens are used for single-workspace integrations
    where the token is generated directly from the Notion integrations page.
    """

    auth_type: Literal["token"] = Field(
        default="token",
        description="Authentication type identifier",
    )
    token: str = Field(
        ...,
        description="Internal Integration Token from Notion",
        min_length=1,
    )

    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        """Validate that the token has the expected format."""
        v = v.strip()
        if not v.startswith(("secret_", "ntn_")):
            # Log warning but don't fail - Notion may change token format
            pass
        return v


class OAuth2Credentials(BaseModel):
    """
    Configuration for OAuth 2.0 authentication.

    OAuth 2.0 is used for public integrations that need to access
    multiple users' workspaces.
    """

    auth_type: Literal["oauth2"] = Field(
        default="oauth2",
        description="Authentication type identifier",
    )
    client_id: str = Field(
        ...,
        description="OAuth 2.0 Client ID from Notion",
        min_length=1,
    )
    client_secret: str = Field(
        ...,
        description="OAuth 2.0 Client Secret from Notion",
        min_length=1,
    )
    access_token: str = Field(
        ...,
        description="OAuth 2.0 Access Token obtained after authorization",
        min_length=1,
    )
    refresh_token: Optional[str] = Field(
        default=None,
        description="OAuth 2.0 Refresh Token (if available)",
    )
    token_expiry: Optional[datetime] = Field(
        default=None,
        description="Token expiration timestamp",
    )

    @field_validator("access_token")
    @classmethod
    def validate_access_token(cls, v: str) -> str:
        """Validate and clean the access token."""
        return v.strip()


# Union type for credentials with discriminator
CredentialsType = Union[TokenCredentials, OAuth2Credentials]


# =============================================================================
# Stream Configuration
# =============================================================================


class StreamConfig(BaseModel):
    """Configuration for a specific data stream."""

    name: str = Field(
        ...,
        description="Name of the stream",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this stream is enabled for syncing",
    )
    sync_mode: Literal["full_refresh", "incremental"] = Field(
        default="full_refresh",
        description="Sync mode for this stream",
    )
    cursor_field: Optional[str] = Field(
        default=None,
        description="Field to use for incremental sync cursor",
    )


# =============================================================================
# Main Configuration Model
# =============================================================================


class NotionConfig(BaseModel):
    """
    Main configuration model for the Notion source connector.

    This model validates all configuration options and provides
    sensible defaults for optional parameters.
    """

    credentials: CredentialsType = Field(
        ...,
        description="Authentication credentials for the Notion API",
        discriminator="auth_type",
    )

    # Optional configuration
    start_date: Optional[datetime] = Field(
        default=None,
        description="Only sync data modified after this date (ISO 8601 format)",
    )

    # API configuration
    api_version: str = Field(
        default="2022-06-28",
        description="Notion API version to use",
    )

    # Rate limiting configuration
    requests_per_second: float = Field(
        default=3.0,
        ge=0.1,
        le=10.0,
        description="Maximum requests per second (Notion default is 3)",
    )

    max_retries: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of retry attempts for failed requests",
    )

    retry_base_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Base delay in seconds for exponential backoff",
    )

    # Pagination configuration
    page_size: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Number of items to fetch per page (max 100)",
    )

    # Timeout configuration
    request_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Request timeout in seconds",
    )

    # Stream configuration
    streams: Optional[List[StreamConfig]] = Field(
        default=None,
        description="Configuration for specific streams",
    )

    # Block fetching configuration
    fetch_page_blocks: bool = Field(
        default=True,
        description="Whether to fetch block content for pages",
    )

    max_block_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum depth for nested block fetching",
    )

    # Database-specific configuration
    database_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific database IDs to sync (None for all)",
    )

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_start_date(cls, v: Any) -> Optional[datetime]:
        """Parse start_date from string if necessary."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                # Handle various ISO 8601 formats
                v = v.strip()
                if v.endswith("Z"):
                    v = v[:-1] + "+00:00"
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError(f"Invalid datetime format: {v}")
        return v

    @field_validator("database_ids")
    @classmethod
    def validate_database_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize database IDs."""
        if v is None:
            return v
        # Normalize IDs by removing dashes
        return [db_id.replace("-", "") for db_id in v]

    @model_validator(mode="after")
    def validate_config(self) -> "NotionConfig":
        """Perform cross-field validation."""
        # Ensure incremental streams have a cursor field defined
        if self.streams:
            for stream in self.streams:
                if stream.sync_mode == "incremental" and not stream.cursor_field:
                    stream.cursor_field = "last_edited_time"
        return self

    def get_token(self) -> str:
        """
        Get the authentication token from credentials.

        Returns:
            The API token to use for authentication
        """
        if isinstance(self.credentials, TokenCredentials):
            return self.credentials.token
        elif isinstance(self.credentials, OAuth2Credentials):
            return self.credentials.access_token
        else:
            raise ValueError("Unknown credential type")

    def is_stream_enabled(self, stream_name: str) -> bool:
        """
        Check if a specific stream is enabled.

        Args:
            stream_name: Name of the stream to check

        Returns:
            True if the stream is enabled, False otherwise
        """
        if self.streams is None:
            return True  # All streams enabled by default

        for stream in self.streams:
            if stream.name == stream_name:
                return stream.enabled

        return True  # Default to enabled if not specified

    def get_stream_config(self, stream_name: str) -> Optional[StreamConfig]:
        """
        Get configuration for a specific stream.

        Args:
            stream_name: Name of the stream

        Returns:
            StreamConfig if found, None otherwise
        """
        if self.streams is None:
            return None

        for stream in self.streams:
            if stream.name == stream_name:
                return stream

        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as a dictionary
        """
        return self.model_dump()

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "credentials": {
                    "auth_type": "token",
                    "token": "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                },
                "start_date": "2024-01-01T00:00:00Z",
                "page_size": 100,
                "fetch_page_blocks": True,
            }
        }


# =============================================================================
# State Management
# =============================================================================


class StreamState(BaseModel):
    """State for a single stream (for incremental sync)."""

    cursor_value: Optional[str] = Field(
        default=None,
        description="Current cursor value (e.g., last_edited_time)",
    )
    last_sync_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last successful sync",
    )
    records_synced: int = Field(
        default=0,
        description="Total number of records synced",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


class ConnectorState(BaseModel):
    """Overall connector state for resumable syncs."""

    streams: Dict[str, StreamState] = Field(
        default_factory=dict,
        description="State for each stream",
    )

    def get_stream_state(self, stream_name: str) -> StreamState:
        """
        Get state for a specific stream.

        Args:
            stream_name: Name of the stream

        Returns:
            StreamState for the stream (creates new if doesn't exist)
        """
        if stream_name not in self.streams:
            self.streams[stream_name] = StreamState()
        return self.streams[stream_name]

    def update_stream_state(
        self,
        stream_name: str,
        cursor_value: Optional[str] = None,
        records_synced: int = 0,
    ) -> None:
        """
        Update state for a specific stream.

        Args:
            stream_name: Name of the stream
            cursor_value: New cursor value
            records_synced: Number of records synced in this batch
        """
        state = self.get_stream_state(stream_name)
        if cursor_value:
            state.cursor_value = cursor_value
        state.records_synced += records_synced
        state.last_sync_time = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectorState":
        """
        Create from dictionary.

        Args:
            data: State dictionary

        Returns:
            ConnectorState instance
        """
        return cls(**data)
