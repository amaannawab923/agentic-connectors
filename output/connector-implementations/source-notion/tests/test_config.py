"""
Configuration validation tests for the Notion connector.

These tests verify that the configuration models work correctly,
including validation of credentials and optional fields.
"""

import pytest
import sys
import os
from datetime import datetime
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import (
    NotionConfig,
    InternalTokenCredentials,
    OAuth2Credentials,
    StreamConfig,
    StreamState,
    ConnectorState,
)


class TestInternalTokenCredentials:
    """Test InternalTokenCredentials model."""

    def test_valid_token_credentials(self):
        """Test valid internal token credentials."""
        creds = InternalTokenCredentials(
            auth_type="token",
            token="secret_test_token_123456789012345678901234567890"
        )
        assert creds.auth_type == "token"
        assert creds.token == "secret_test_token_123456789012345678901234567890"

    def test_token_with_ntn_prefix(self):
        """Test token with ntn_ prefix (newer format)."""
        creds = InternalTokenCredentials(
            auth_type="token",
            token="ntn_test_token_123456789012345678901234567890"
        )
        assert creds.token.startswith("ntn_")

    def test_token_whitespace_stripped(self):
        """Test that token whitespace is stripped."""
        creds = InternalTokenCredentials(
            auth_type="token",
            token="  secret_test_token_123  "
        )
        assert creds.token == "secret_test_token_123"

    def test_missing_token_raises_error(self):
        """Test that missing token raises validation error."""
        with pytest.raises(ValidationError) as excinfo:
            InternalTokenCredentials(auth_type="token")
        assert "token" in str(excinfo.value).lower()

    def test_empty_token_raises_error(self):
        """Test that empty token raises validation error."""
        with pytest.raises(ValidationError) as excinfo:
            InternalTokenCredentials(auth_type="token", token="")
        # Should fail min_length validation
        assert "token" in str(excinfo.value).lower() or "string" in str(excinfo.value).lower()


class TestOAuth2Credentials:
    """Test OAuth2Credentials model."""

    def test_valid_oauth2_credentials(self):
        """Test valid OAuth2 credentials."""
        creds = OAuth2Credentials(
            auth_type="oauth2",
            client_id="test-client-id",
            client_secret="test-client-secret",
            access_token="test-access-token"
        )
        assert creds.auth_type == "oauth2"
        assert creds.client_id == "test-client-id"
        assert creds.client_secret == "test-client-secret"
        assert creds.access_token == "test-access-token"
        assert creds.refresh_token is None
        assert creds.token_expiry is None

    def test_oauth2_with_optional_fields(self):
        """Test OAuth2 credentials with optional fields."""
        expiry = datetime(2024, 12, 31, 23, 59, 59)
        creds = OAuth2Credentials(
            auth_type="oauth2",
            client_id="test-client-id",
            client_secret="test-client-secret",
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            token_expiry=expiry
        )
        assert creds.refresh_token == "test-refresh-token"
        assert creds.token_expiry == expiry

    def test_missing_client_id_raises_error(self):
        """Test that missing client_id raises validation error."""
        with pytest.raises(ValidationError):
            OAuth2Credentials(
                auth_type="oauth2",
                client_secret="test-client-secret",
                access_token="test-access-token"
            )

    def test_missing_access_token_raises_error(self):
        """Test that missing access_token raises validation error."""
        with pytest.raises(ValidationError):
            OAuth2Credentials(
                auth_type="oauth2",
                client_id="test-client-id",
                client_secret="test-client-secret"
            )


class TestNotionConfig:
    """Test NotionConfig model."""

    def test_valid_config_with_token(self):
        """Test valid configuration with internal token."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test_token_123"
            }
        )
        assert config.credentials.auth_type == "token"
        assert isinstance(config.credentials, InternalTokenCredentials)

    def test_valid_config_with_oauth2(self):
        """Test valid configuration with OAuth2."""
        config = NotionConfig(
            credentials={
                "auth_type": "oauth2",
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "access_token": "test-access-token"
            }
        )
        assert config.credentials.auth_type == "oauth2"
        assert isinstance(config.credentials, OAuth2Credentials)

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test"
            }
        )
        assert config.api_version == "2022-06-28"
        assert config.requests_per_second == 3.0
        assert config.max_retries == 5
        assert config.retry_base_delay == 1.0
        assert config.page_size == 100
        assert config.request_timeout == 60
        assert config.fetch_page_blocks is True
        assert config.max_block_depth == 3
        assert config.start_date is None
        assert config.streams is None
        assert config.database_ids is None

    def test_custom_values(self):
        """Test that custom values are set correctly."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test"
            },
            requests_per_second=5.0,
            max_retries=3,
            page_size=50,
            fetch_page_blocks=False,
            max_block_depth=5
        )
        assert config.requests_per_second == 5.0
        assert config.max_retries == 3
        assert config.page_size == 50
        assert config.fetch_page_blocks is False
        assert config.max_block_depth == 5

    def test_start_date_parsing_iso_format(self):
        """Test start_date parsing from ISO format string."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test"
            },
            start_date="2024-01-01T00:00:00Z"
        )
        assert config.start_date is not None
        assert config.start_date.year == 2024
        assert config.start_date.month == 1
        assert config.start_date.day == 1

    def test_start_date_parsing_datetime_object(self):
        """Test start_date with datetime object."""
        dt = datetime(2024, 6, 15, 12, 0, 0)
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test"
            },
            start_date=dt
        )
        assert config.start_date == dt

    def test_invalid_start_date_raises_error(self):
        """Test that invalid start_date format raises error."""
        with pytest.raises(ValidationError):
            NotionConfig(
                credentials={
                    "auth_type": "token",
                    "token": "secret_test"
                },
                start_date="not-a-date"
            )

    def test_page_size_validation_max(self):
        """Test that page_size above 100 raises error."""
        with pytest.raises(ValidationError):
            NotionConfig(
                credentials={
                    "auth_type": "token",
                    "token": "secret_test"
                },
                page_size=150
            )

    def test_page_size_validation_min(self):
        """Test that page_size below 1 raises error."""
        with pytest.raises(ValidationError):
            NotionConfig(
                credentials={
                    "auth_type": "token",
                    "token": "secret_test"
                },
                page_size=0
            )

    def test_requests_per_second_validation(self):
        """Test requests_per_second validation."""
        with pytest.raises(ValidationError):
            NotionConfig(
                credentials={
                    "auth_type": "token",
                    "token": "secret_test"
                },
                requests_per_second=15.0  # Max is 10
            )

    def test_database_ids_normalization(self):
        """Test that database_ids are normalized (dashes removed)."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test"
            },
            database_ids=["12345678-1234-1234-1234-123456789abc"]
        )
        # UUID has 32 hex chars: 8-4-4-4-12 = 32, so normalized is 32 chars without dashes
        assert config.database_ids == ["12345678123412341234123456789abc"]
        assert len(config.database_ids[0]) == 32

    def test_get_token_internal(self):
        """Test get_token with internal token credentials."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test_token"
            }
        )
        assert config.get_token() == "secret_test_token"

    def test_get_token_oauth2(self):
        """Test get_token with OAuth2 credentials."""
        config = NotionConfig(
            credentials={
                "auth_type": "oauth2",
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "access_token": "oauth-access-token"
            }
        )
        assert config.get_token() == "oauth-access-token"

    def test_is_stream_enabled_default(self):
        """Test is_stream_enabled returns True by default."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test"
            }
        )
        assert config.is_stream_enabled("users") is True
        assert config.is_stream_enabled("databases") is True
        assert config.is_stream_enabled("pages") is True

    def test_is_stream_enabled_with_config(self):
        """Test is_stream_enabled with stream configuration."""
        config = NotionConfig(
            credentials={
                "auth_type": "token",
                "token": "secret_test"
            },
            streams=[
                {"name": "users", "enabled": True},
                {"name": "databases", "enabled": False},
            ]
        )
        assert config.is_stream_enabled("users") is True
        assert config.is_stream_enabled("databases") is False
        assert config.is_stream_enabled("pages") is True  # Not in list, defaults to True

    def test_missing_credentials_raises_error(self):
        """Test that missing credentials raises error."""
        with pytest.raises(ValidationError):
            NotionConfig()


class TestStreamConfig:
    """Test StreamConfig model."""

    def test_valid_stream_config(self):
        """Test valid stream configuration."""
        config = StreamConfig(
            name="users",
            enabled=True,
            sync_mode="full_refresh"
        )
        assert config.name == "users"
        assert config.enabled is True
        assert config.sync_mode == "full_refresh"
        assert config.cursor_field is None

    def test_incremental_sync_mode(self):
        """Test incremental sync mode configuration."""
        config = StreamConfig(
            name="pages",
            enabled=True,
            sync_mode="incremental",
            cursor_field="last_edited_time"
        )
        assert config.sync_mode == "incremental"
        assert config.cursor_field == "last_edited_time"

    def test_invalid_sync_mode(self):
        """Test that invalid sync_mode raises error."""
        with pytest.raises(ValidationError):
            StreamConfig(
                name="users",
                sync_mode="invalid_mode"
            )


class TestConnectorState:
    """Test ConnectorState model."""

    def test_empty_state(self):
        """Test empty connector state."""
        state = ConnectorState()
        assert state.streams == {}

    def test_get_stream_state_creates_new(self):
        """Test get_stream_state creates new state if not exists."""
        state = ConnectorState()
        stream_state = state.get_stream_state("users")
        assert stream_state is not None
        assert stream_state.cursor_value is None
        assert stream_state.records_synced == 0
        assert "users" in state.streams

    def test_get_stream_state_returns_existing(self):
        """Test get_stream_state returns existing state."""
        state = ConnectorState()
        state.streams["users"] = StreamState(cursor_value="2024-01-01T00:00:00.000Z")

        stream_state = state.get_stream_state("users")
        assert stream_state.cursor_value == "2024-01-01T00:00:00.000Z"

    def test_update_stream_state(self):
        """Test update_stream_state updates correctly."""
        state = ConnectorState()
        state.update_stream_state("users", cursor_value="2024-01-15T12:00:00.000Z", records_synced=50)

        stream_state = state.get_stream_state("users")
        assert stream_state.cursor_value == "2024-01-15T12:00:00.000Z"
        assert stream_state.records_synced == 50
        assert stream_state.last_sync_time is not None

    def test_update_stream_state_accumulates_records(self):
        """Test that records_synced accumulates across updates."""
        state = ConnectorState()
        state.update_stream_state("users", records_synced=50)
        state.update_stream_state("users", records_synced=30)

        stream_state = state.get_stream_state("users")
        assert stream_state.records_synced == 80


class TestStreamState:
    """Test StreamState model."""

    def test_default_stream_state(self):
        """Test default stream state values."""
        state = StreamState()
        assert state.cursor_value is None
        assert state.last_sync_time is None
        assert state.records_synced == 0

    def test_stream_state_with_values(self):
        """Test stream state with custom values."""
        sync_time = datetime(2024, 1, 15, 12, 0, 0)
        state = StreamState(
            cursor_value="2024-01-15T12:00:00.000Z",
            last_sync_time=sync_time,
            records_synced=100
        )
        assert state.cursor_value == "2024-01-15T12:00:00.000Z"
        assert state.last_sync_time == sync_time
        assert state.records_synced == 100
