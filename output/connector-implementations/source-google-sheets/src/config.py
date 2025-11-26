"""
Configuration models for Google Sheets connector using Pydantic.

Provides validation and type safety for connector configuration.
"""

import json
import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class AuthType(str, Enum):
    """Supported authentication types."""

    SERVICE_ACCOUNT = "service_account"
    OAUTH2 = "oauth2"


class ServiceAccountCredentials(BaseModel):
    """Configuration for Service Account authentication."""

    auth_type: Literal["service_account"] = Field(
        default="service_account",
        description="Authentication type identifier",
    )
    service_account_info: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        description="Service account JSON key as string or dictionary",
    )
    service_account_file: Optional[str] = Field(
        default=None,
        description="Path to service account JSON key file",
    )

    @model_validator(mode="after")
    def validate_credentials_source(self) -> "ServiceAccountCredentials":
        """Ensure at least one credential source is provided."""
        if not self.service_account_info and not self.service_account_file:
            raise ValueError(
                "Must provide either service_account_info or service_account_file"
            )
        return self

    @field_validator("service_account_info", mode="before")
    @classmethod
    def parse_service_account_info(cls, v: Optional[Union[str, Dict]]) -> Optional[Dict]:
        """Parse service account info from string if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in service_account_info: {e}")
        return v


class OAuth2Credentials(BaseModel):
    """Configuration for OAuth2 authentication."""

    auth_type: Literal["oauth2"] = Field(
        default="oauth2",
        description="Authentication type identifier",
    )
    client_id: str = Field(
        ...,
        min_length=1,
        description="OAuth2 client ID",
    )
    client_secret: str = Field(
        ...,
        min_length=1,
        description="OAuth2 client secret",
    )
    refresh_token: str = Field(
        ...,
        min_length=1,
        description="OAuth2 refresh token",
    )
    access_token: Optional[str] = Field(
        default=None,
        description="Optional existing access token",
    )


# Union type for credentials
CredentialsConfig = Union[ServiceAccountCredentials, OAuth2Credentials]


class StreamSelection(BaseModel):
    """Configuration for selecting which streams/sheets to sync."""

    sheet_names: Optional[List[str]] = Field(
        default=None,
        description="List of sheet names to sync. If None, all sheets are synced.",
    )
    exclude_sheets: Optional[List[str]] = Field(
        default=None,
        description="List of sheet names to exclude from sync.",
    )


class GoogleSheetsConfig(BaseModel):
    """
    Main configuration for Google Sheets connector.

    This model validates all configuration options and provides
    defaults for optional settings.
    """

    spreadsheet_id: str = Field(
        ...,
        min_length=1,
        description="The ID of the Google Spreadsheet (from URL)",
        pattern=r"^[a-zA-Z0-9-_]+$",
    )
    credentials: Union[ServiceAccountCredentials, OAuth2Credentials] = Field(
        ...,
        description="Authentication credentials",
        discriminator="auth_type",
    )
    row_batch_size: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Number of rows to fetch per API request",
    )
    requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Maximum API requests per minute (rate limiting)",
    )
    stream_selection: Optional[StreamSelection] = Field(
        default=None,
        description="Optional stream/sheet selection configuration",
    )
    include_row_number: bool = Field(
        default=False,
        description="Include row number as a column in output records",
    )
    value_render_option: str = Field(
        default="FORMATTED_VALUE",
        description="How values should be rendered (FORMATTED_VALUE, UNFORMATTED_VALUE, FORMULA)",
    )
    date_time_render_option: str = Field(
        default="FORMATTED_STRING",
        description="How dates should be rendered (FORMATTED_STRING, SERIAL_NUMBER)",
    )

    @field_validator("spreadsheet_id", mode="before")
    @classmethod
    def extract_spreadsheet_id(cls, v: str) -> str:
        """Extract spreadsheet ID from URL if full URL is provided."""
        if not v:
            raise ValueError("spreadsheet_id cannot be empty")

        # Check if it's a full URL
        url_pattern = r"https?://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)"
        match = re.match(url_pattern, v)
        if match:
            return match.group(1)

        # Validate ID format
        id_pattern = r"^[a-zA-Z0-9-_]+$"
        if not re.match(id_pattern, v):
            raise ValueError(
                f"Invalid spreadsheet_id format: {v}. "
                "Expected alphanumeric characters, hyphens, and underscores."
            )

        return v

    @field_validator("value_render_option")
    @classmethod
    def validate_value_render_option(cls, v: str) -> str:
        """Validate value render option."""
        valid_options = ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"]
        if v not in valid_options:
            raise ValueError(
                f"Invalid value_render_option: {v}. Must be one of {valid_options}"
            )
        return v

    @field_validator("date_time_render_option")
    @classmethod
    def validate_date_time_render_option(cls, v: str) -> str:
        """Validate date/time render option."""
        valid_options = ["FORMATTED_STRING", "SERIAL_NUMBER"]
        if v not in valid_options:
            raise ValueError(
                f"Invalid date_time_render_option: {v}. Must be one of {valid_options}"
            )
        return v

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoogleSheetsConfig":
        """
        Create configuration from a dictionary.

        Handles credential type detection and parsing.

        Args:
            data: Configuration dictionary.

        Returns:
            GoogleSheetsConfig instance.
        """
        # Make a copy to avoid modifying input
        config_data = data.copy()

        # Parse credentials if needed
        if "credentials" in config_data:
            creds = config_data["credentials"]
            if isinstance(creds, dict):
                auth_type = creds.get("auth_type", "service_account")

                if auth_type == "service_account":
                    config_data["credentials"] = ServiceAccountCredentials(**creds)
                elif auth_type == "oauth2":
                    config_data["credentials"] = OAuth2Credentials(**creds)

        return cls(**config_data)

    @classmethod
    def from_json(cls, json_str: str) -> "GoogleSheetsConfig":
        """
        Create configuration from a JSON string.

        Args:
            json_str: JSON configuration string.

        Returns:
            GoogleSheetsConfig instance.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def get_credentials_dict(self) -> Dict[str, Any]:
        """
        Get credentials as a dictionary for use with authenticator.

        Returns:
            Dictionary containing credential data.
        """
        if isinstance(self.credentials, ServiceAccountCredentials):
            return {
                "service_account_info": self.credentials.service_account_info,
                "service_account_file": self.credentials.service_account_file,
            }
        elif isinstance(self.credentials, OAuth2Credentials):
            return {
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "refresh_token": self.credentials.refresh_token,
                "access_token": self.credentials.access_token,
            }
        return {}

    def get_auth_type(self) -> str:
        """
        Get the authentication type.

        Returns:
            Authentication type string.
        """
        return self.credentials.auth_type

    def should_sync_sheet(self, sheet_name: str) -> bool:
        """
        Check if a sheet should be synced based on selection config.

        Args:
            sheet_name: Name of the sheet to check.

        Returns:
            True if the sheet should be synced.
        """
        if self.stream_selection is None:
            return True

        # Check exclusion list first
        if self.stream_selection.exclude_sheets:
            if sheet_name in self.stream_selection.exclude_sheets:
                return False

        # Check inclusion list
        if self.stream_selection.sheet_names:
            return sheet_name in self.stream_selection.sheet_names

        return True


class ConfigSchema:
    """
    JSON Schema representation of the configuration.

    Used for documentation and validation in external systems.
    """

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """
        Get JSON schema for the configuration.

        Returns:
            JSON Schema dictionary.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["spreadsheet_id", "credentials"],
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The ID of the Google Spreadsheet (from URL)",
                    "pattern": "^[a-zA-Z0-9-_]+$",
                },
                "credentials": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Service Account",
                            "required": ["auth_type"],
                            "properties": {
                                "auth_type": {"const": "service_account"},
                                "service_account_info": {
                                    "type": ["string", "object"],
                                    "description": "Service account JSON key",
                                },
                                "service_account_file": {
                                    "type": "string",
                                    "description": "Path to service account JSON file",
                                },
                            },
                        },
                        {
                            "type": "object",
                            "title": "OAuth2",
                            "required": [
                                "auth_type",
                                "client_id",
                                "client_secret",
                                "refresh_token",
                            ],
                            "properties": {
                                "auth_type": {"const": "oauth2"},
                                "client_id": {"type": "string"},
                                "client_secret": {"type": "string"},
                                "refresh_token": {"type": "string"},
                                "access_token": {"type": "string"},
                            },
                        },
                    ]
                },
                "row_batch_size": {
                    "type": "integer",
                    "default": 200,
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Number of rows to fetch per API request",
                },
                "requests_per_minute": {
                    "type": "integer",
                    "default": 60,
                    "minimum": 1,
                    "maximum": 300,
                    "description": "Maximum API requests per minute",
                },
                "include_row_number": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include row number in output records",
                },
                "value_render_option": {
                    "type": "string",
                    "enum": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
                    "default": "FORMATTED_VALUE",
                },
                "date_time_render_option": {
                    "type": "string",
                    "enum": ["FORMATTED_STRING", "SERIAL_NUMBER"],
                    "default": "FORMATTED_STRING",
                },
            },
        }
