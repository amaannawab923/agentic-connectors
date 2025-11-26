"""
Configuration management for Google Sheets connector.

Uses Pydantic for validation and type safety.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ServiceAccountCredentials(BaseModel):
    """Service account credentials configuration."""

    auth_type: Literal["service_account"] = Field(
        default="service_account",
        description="Authentication type identifier",
    )

    type: str = Field(
        default="service_account",
        description="Google credential type",
    )

    project_id: str = Field(
        ...,
        description="Google Cloud project ID",
    )

    private_key_id: Optional[str] = Field(
        default=None,
        description="Private key ID",
    )

    private_key: str = Field(
        ...,
        description="Private key in PEM format",
    )

    client_email: str = Field(
        ...,
        description="Service account email address",
    )

    client_id: Optional[str] = Field(
        default=None,
        description="Client ID",
    )

    auth_uri: str = Field(
        default="https://accounts.google.com/o/oauth2/auth",
        description="OAuth2 authorization URI",
    )

    token_uri: str = Field(
        default="https://oauth2.googleapis.com/token",
        description="Token URI",
    )

    auth_provider_x509_cert_url: str = Field(
        default="https://www.googleapis.com/oauth2/v1/certs",
        description="Auth provider certificate URL",
    )

    client_x509_cert_url: Optional[str] = Field(
        default=None,
        description="Client certificate URL",
    )

    @field_validator("private_key")
    @classmethod
    def validate_private_key(cls, v: str) -> str:
        """Ensure private key is in PEM format."""
        if not v.strip().startswith("-----BEGIN"):
            raise ValueError("Private key must be in PEM format")
        return v

    def to_google_credentials_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by Google libraries."""
        return {
            "type": "service_account",
            "project_id": self.project_id,
            "private_key_id": self.private_key_id,
            "private_key": self.private_key,
            "client_email": self.client_email,
            "client_id": self.client_id,
            "auth_uri": self.auth_uri,
            "token_uri": self.token_uri,
            "auth_provider_x509_cert_url": self.auth_provider_x509_cert_url,
            "client_x509_cert_url": self.client_x509_cert_url,
        }


class OAuth2Credentials(BaseModel):
    """OAuth2 credentials configuration."""

    auth_type: Literal["oauth2"] = Field(
        default="oauth2",
        description="Authentication type identifier",
    )

    client_id: str = Field(
        ...,
        description="OAuth2 client ID",
    )

    client_secret: str = Field(
        ...,
        description="OAuth2 client secret",
    )

    refresh_token: str = Field(
        ...,
        description="OAuth2 refresh token",
    )


class StreamConfig(BaseModel):
    """Configuration for a single sheet stream."""

    name: str = Field(
        ...,
        description="Name of the sheet to read",
    )

    header_row: int = Field(
        default=1,
        ge=1,
        description="Row number containing column headers (1-indexed)",
    )

    batch_size: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Number of rows to fetch per API call",
    )

    enabled: bool = Field(
        default=True,
        description="Whether this stream is enabled for extraction",
    )


class RateLimitSettings(BaseModel):
    """Rate limiting settings."""

    requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Maximum requests per minute (Google limit: 300/project, 60/user)",
    )

    max_retries: int = Field(
        default=5,
        ge=0,
        le=10,
        description="Maximum retry attempts on transient errors",
    )

    base_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Base delay in seconds for exponential backoff",
    )

    max_delay: float = Field(
        default=60.0,
        ge=1.0,
        le=300.0,
        description="Maximum delay in seconds between retries",
    )


class GoogleSheetsConfig(BaseModel):
    """
    Main configuration for the Google Sheets connector.

    Example configuration:
    ```python
    config = GoogleSheetsConfig(
        spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        credentials=ServiceAccountCredentials(
            project_id="my-project",
            private_key="-----BEGIN PRIVATE KEY-----...",
            client_email="connector@my-project.iam.gserviceaccount.com",
        ),
    )
    ```
    """

    spreadsheet_id: str = Field(
        ...,
        description="The ID of the Google Spreadsheet (from the URL)",
        pattern=r"^[a-zA-Z0-9-_]+$",
    )

    credentials: Union[ServiceAccountCredentials, OAuth2Credentials] = Field(
        ...,
        discriminator="auth_type",
        description="Authentication credentials",
    )

    streams: Optional[List[StreamConfig]] = Field(
        default=None,
        description="Specific sheets to extract. If None, all sheets are extracted.",
    )

    row_batch_size: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Default number of rows to fetch per API call",
    )

    header_row: int = Field(
        default=1,
        ge=1,
        description="Default row number containing column headers (1-indexed)",
    )

    rate_limit: RateLimitSettings = Field(
        default_factory=RateLimitSettings,
        description="Rate limiting settings",
    )

    include_row_number: bool = Field(
        default=True,
        description="Include a '_row_number' field in output records",
    )

    @field_validator("spreadsheet_id")
    @classmethod
    def validate_spreadsheet_id(cls, v: str) -> str:
        """Validate spreadsheet ID format."""
        if len(v) < 10:
            raise ValueError("Spreadsheet ID appears too short")
        return v

    @model_validator(mode="after")
    def validate_config(self) -> "GoogleSheetsConfig":
        """Validate the complete configuration."""
        # Ensure rate limit max_delay is greater than base_delay
        if self.rate_limit.max_delay < self.rate_limit.base_delay:
            raise ValueError("max_delay must be greater than or equal to base_delay")
        return self

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoogleSheetsConfig":
        """
        Create configuration from a dictionary.

        Handles various input formats for flexibility.
        """
        # Handle nested credentials format
        if "credentials" in data and isinstance(data["credentials"], dict):
            creds = data["credentials"]
            # Determine auth type if not specified
            if "auth_type" not in creds:
                if "private_key" in creds:
                    creds["auth_type"] = "service_account"
                elif "refresh_token" in creds:
                    creds["auth_type"] = "oauth2"

        return cls(**data)

    def get_auth_dict(self) -> Dict[str, Any]:
        """Get credentials as dictionary for authentication."""
        if isinstance(self.credentials, ServiceAccountCredentials):
            return self.credentials.to_google_credentials_dict()
        else:
            return {
                "auth_type": "oauth2",
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "refresh_token": self.credentials.refresh_token,
            }


class CatalogEntry(BaseModel):
    """Entry in the connector catalog describing a stream."""

    stream_name: str = Field(
        ...,
        description="Name of the stream (sheet name)",
    )

    schema: Dict[str, Any] = Field(
        ...,
        description="JSON Schema for the stream",
    )

    supported_sync_modes: List[str] = Field(
        default_factory=lambda: ["full_refresh"],
        description="Supported synchronization modes",
    )

    source_defined_cursor: bool = Field(
        default=False,
        description="Whether the source defines a cursor field",
    )

    default_cursor_field: Optional[List[str]] = Field(
        default=None,
        description="Default cursor field path",
    )

    source_defined_primary_key: Optional[List[List[str]]] = Field(
        default=None,
        description="Primary key defined by the source",
    )


class Catalog(BaseModel):
    """Catalog of available streams in the connector."""

    streams: List[CatalogEntry] = Field(
        default_factory=list,
        description="List of available streams",
    )

    def get_stream(self, stream_name: str) -> Optional[CatalogEntry]:
        """Get a specific stream by name."""
        for stream in self.streams:
            if stream.stream_name == stream_name:
                return stream
        return None

    def get_stream_names(self) -> List[str]:
        """Get list of all stream names."""
        return [stream.stream_name for stream in self.streams]
