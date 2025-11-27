"""
Configuration models for Google Sheets connector.

This module defines Pydantic models for validating connector configuration,
including authentication credentials and connection settings.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import json
import re


class ServiceAccountCredentials(BaseModel):
    """Service account authentication credentials."""

    auth_type: Literal["service_account"] = Field(
        default="service_account",
        description="Authentication type identifier"
    )

    service_account_info: str = Field(
        ...,
        description="Service account JSON credentials as a string"
    )

    @field_validator("service_account_info")
    @classmethod
    def validate_service_account_info(cls, v: str) -> str:
        """Validate that service account info is valid JSON with required fields."""
        try:
            data = json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in service_account_info: {e}")

        required_fields = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
        ]

        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields in service account: {missing_fields}")

        if data.get("type") != "service_account":
            raise ValueError("service_account_info must have type 'service_account'")

        return v

    def get_credentials_dict(self) -> Dict[str, Any]:
        """Parse and return credentials as a dictionary."""
        return json.loads(self.service_account_info)


class OAuth2Credentials(BaseModel):
    """OAuth 2.0 authentication credentials."""

    auth_type: Literal["oauth2"] = Field(
        default="oauth2",
        description="Authentication type identifier"
    )

    client_id: str = Field(
        ...,
        description="OAuth2 client ID"
    )

    client_secret: str = Field(
        ...,
        description="OAuth2 client secret"
    )

    refresh_token: str = Field(
        ...,
        description="OAuth2 refresh token"
    )

    access_token: Optional[str] = Field(
        default=None,
        description="OAuth2 access token (optional, will be refreshed)"
    )

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate client ID format."""
        if not v or len(v) < 10:
            raise ValueError("Invalid client_id format")
        return v

    @field_validator("client_secret")
    @classmethod
    def validate_client_secret(cls, v: str) -> str:
        """Validate client secret format."""
        if not v or len(v) < 10:
            raise ValueError("Invalid client_secret format")
        return v


class APIKeyCredentials(BaseModel):
    """API Key authentication credentials (for public sheets only)."""

    auth_type: Literal["api_key"] = Field(
        default="api_key",
        description="Authentication type identifier"
    )

    api_key: str = Field(
        ...,
        description="Google API key for accessing public spreadsheets"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format."""
        if not v or len(v) < 20:
            raise ValueError("Invalid API key format")
        return v


# Union type for credentials
CredentialsUnion = Union[ServiceAccountCredentials, OAuth2Credentials, APIKeyCredentials]


class SheetConfig(BaseModel):
    """Configuration for a specific sheet to extract."""

    name: str = Field(
        ...,
        description="Name of the sheet to extract"
    )

    range: Optional[str] = Field(
        default=None,
        description="Optional A1 notation range (e.g., 'A1:Z1000')"
    )

    headers_row: int = Field(
        default=1,
        ge=1,
        description="Row number containing headers (1-indexed)"
    )

    skip_rows: int = Field(
        default=0,
        ge=0,
        description="Number of rows to skip after headers"
    )


class GoogleSheetsConfig(BaseModel):
    """Main configuration for Google Sheets connector."""

    spreadsheet_id: str = Field(
        ...,
        description="The ID of the Google Spreadsheet (from URL)"
    )

    credentials: CredentialsUnion = Field(
        ...,
        discriminator="auth_type",
        description="Authentication credentials"
    )

    batch_size: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Number of rows to fetch per API call"
    )

    sheets: Optional[List[SheetConfig]] = Field(
        default=None,
        description="Specific sheets to extract (None = all sheets)"
    )

    value_render_option: Literal[
        "FORMATTED_VALUE",
        "UNFORMATTED_VALUE",
        "FORMULA"
    ] = Field(
        default="UNFORMATTED_VALUE",
        description="How to render cell values"
    )

    date_time_render_option: Literal[
        "SERIAL_NUMBER",
        "FORMATTED_STRING"
    ] = Field(
        default="FORMATTED_STRING",
        description="How to render date/time values"
    )

    include_row_numbers: bool = Field(
        default=True,
        description="Include _row_number field in output"
    )

    sanitize_column_names: bool = Field(
        default=True,
        description="Sanitize column names for JSON compatibility"
    )

    max_retries: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of retry attempts"
    )

    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Base delay between retries in seconds"
    )

    request_timeout: int = Field(
        default=180,
        ge=10,
        le=600,
        description="Request timeout in seconds"
    )

    @field_validator("spreadsheet_id")
    @classmethod
    def validate_spreadsheet_id(cls, v: str) -> str:
        """Validate and extract spreadsheet ID."""
        # If it looks like a URL, extract the ID
        if "docs.google.com" in v or "spreadsheets" in v:
            patterns = [
                r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
                r'key=([a-zA-Z0-9-_]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, v)
                if match:
                    return match.group(1)
            raise ValueError(f"Could not extract spreadsheet ID from URL: {v}")

        # Validate as a raw ID
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError(f"Invalid spreadsheet ID format: {v}")

        return v

    @model_validator(mode="after")
    def validate_config(self) -> "GoogleSheetsConfig":
        """Validate the complete configuration."""
        # Additional cross-field validation can be added here
        return self

    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Disallow extra fields
        json_schema_extra = {
            "example": {
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": "{...}"
                },
                "batch_size": 200,
                "value_render_option": "UNFORMATTED_VALUE"
            }
        }


class ConnectionStatus(BaseModel):
    """Status of a connection check."""

    connected: bool = Field(
        ...,
        description="Whether the connection was successful"
    )

    message: str = Field(
        ...,
        description="Status message"
    )

    spreadsheet_title: Optional[str] = Field(
        default=None,
        description="Title of the spreadsheet if connected"
    )

    sheet_count: Optional[int] = Field(
        default=None,
        description="Number of sheets if connected"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if connection failed"
    )


class SyncResult(BaseModel):
    """Result of a sync operation."""

    stream_name: str = Field(
        ...,
        description="Name of the synced stream"
    )

    records_count: int = Field(
        ...,
        description="Number of records synced"
    )

    success: bool = Field(
        ...,
        description="Whether the sync was successful"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if sync failed"
    )

    started_at: str = Field(
        ...,
        description="ISO timestamp when sync started"
    )

    completed_at: str = Field(
        ...,
        description="ISO timestamp when sync completed"
    )
