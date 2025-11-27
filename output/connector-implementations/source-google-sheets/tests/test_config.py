"""
Configuration validation tests for Google Sheets connector.

These tests verify that the Pydantic configuration models work correctly.
"""

import json
import pytest
from pydantic import ValidationError

from src.config import (
    GoogleSheetsConfig,
    ServiceAccountCredentials,
    OAuth2Credentials,
    APIKeyCredentials,
    SheetConfig,
    ConnectionStatus,
    SyncResult,
)


class TestServiceAccountCredentials:
    """Test ServiceAccountCredentials validation."""

    def test_valid_service_account(self, service_account_fixture):
        """Test that valid service account credentials are accepted."""
        creds = ServiceAccountCredentials(
            service_account_info=json.dumps(service_account_fixture)
        )
        assert creds.auth_type == "service_account"
        assert creds.service_account_info is not None

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises a validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                service_account_info="not valid json"
            )
        assert "Invalid JSON" in str(exc_info.value)

    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raise a validation error."""
        incomplete_service_account = {
            "type": "service_account",
            "project_id": "test-project"
            # Missing: private_key_id, private_key, client_email, client_id
        }
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                service_account_info=json.dumps(incomplete_service_account)
            )
        assert "Missing required fields" in str(exc_info.value)

    def test_wrong_type_raises_error(self):
        """Test that wrong type value raises a validation error."""
        wrong_type = {
            "type": "user_account",  # Should be "service_account"
            "project_id": "test-project",
            "private_key_id": "key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "client_email": "test@test.iam.gserviceaccount.com",
            "client_id": "123456789"
        }
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                service_account_info=json.dumps(wrong_type)
            )
        assert "type 'service_account'" in str(exc_info.value)


class TestOAuth2Credentials:
    """Test OAuth2Credentials validation."""

    def test_valid_oauth2(self, oauth2_fixture):
        """Test that valid OAuth2 credentials are accepted."""
        creds = OAuth2Credentials(
            client_id=oauth2_fixture["client_id"],
            client_secret=oauth2_fixture["client_secret"],
            refresh_token=oauth2_fixture["refresh_token"]
        )
        assert creds.auth_type == "oauth2"
        assert creds.client_id == oauth2_fixture["client_id"]

    def test_short_client_id_raises_error(self):
        """Test that too short client_id raises a validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OAuth2Credentials(
                client_id="short",  # Less than 10 chars
                client_secret="valid-secret-123456",
                refresh_token="valid-refresh-token-123456"
            )
        assert "Invalid client_id format" in str(exc_info.value)

    def test_short_client_secret_raises_error(self):
        """Test that too short client_secret raises a validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OAuth2Credentials(
                client_id="valid-client-id-123456",
                client_secret="short",  # Less than 10 chars
                refresh_token="valid-refresh-token-123456"
            )
        assert "Invalid client_secret format" in str(exc_info.value)


class TestAPIKeyCredentials:
    """Test APIKeyCredentials validation."""

    def test_valid_api_key(self, api_key_fixture):
        """Test that valid API key credentials are accepted."""
        creds = APIKeyCredentials(
            api_key=api_key_fixture["api_key"]
        )
        assert creds.auth_type == "api_key"
        assert creds.api_key == api_key_fixture["api_key"]

    def test_short_api_key_raises_error(self):
        """Test that too short API key raises a validation error."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCredentials(
                api_key="short"  # Less than 20 chars
            )
        assert "Invalid API key format" in str(exc_info.value)


class TestGoogleSheetsConfig:
    """Test GoogleSheetsConfig validation."""

    def test_valid_config_with_service_account(self, valid_service_account_config):
        """Test that valid config with service account is accepted."""
        config = GoogleSheetsConfig(**valid_service_account_config)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert hasattr(config.credentials, 'auth_type')
        assert config.credentials.auth_type == "service_account"

    def test_valid_config_with_oauth2(self, valid_oauth2_config):
        """Test that valid config with OAuth2 is accepted."""
        config = GoogleSheetsConfig(**valid_oauth2_config)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert config.credentials.auth_type == "oauth2"

    def test_valid_config_with_api_key(self, valid_api_key_config):
        """Test that valid config with API key is accepted."""
        config = GoogleSheetsConfig(**valid_api_key_config)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert config.credentials.auth_type == "api_key"

    def test_spreadsheet_id_from_url(self):
        """Test that spreadsheet ID can be extracted from URL."""
        config_dict = {
            "spreadsheet_id": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
            "credentials": {
                "auth_type": "api_key",
                "api_key": "AIzaSyTest_API_Key_1234567890_abcdefghijklmnop"
            }
        }
        config = GoogleSheetsConfig(**config_dict)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    def test_invalid_spreadsheet_id_url_raises_error(self):
        """Test that invalid URL raises a validation error."""
        config_dict = {
            "spreadsheet_id": "https://docs.google.com/invalid/url",
            "credentials": {
                "auth_type": "api_key",
                "api_key": "AIzaSyTest_API_Key_1234567890_abcdefghijklmnop"
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            GoogleSheetsConfig(**config_dict)
        assert "Could not extract spreadsheet ID" in str(exc_info.value)

    def test_invalid_spreadsheet_id_format_raises_error(self):
        """Test that invalid spreadsheet ID format raises error."""
        config_dict = {
            "spreadsheet_id": "invalid id with spaces!@#",
            "credentials": {
                "auth_type": "api_key",
                "api_key": "AIzaSyTest_API_Key_1234567890_abcdefghijklmnop"
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            GoogleSheetsConfig(**config_dict)
        assert "Invalid spreadsheet ID format" in str(exc_info.value)

    def test_batch_size_bounds(self):
        """Test that batch_size must be within valid range."""
        base_config = {
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "auth_type": "api_key",
                "api_key": "AIzaSyTest_API_Key_1234567890_abcdefghijklmnop"
            }
        }

        # Too small
        with pytest.raises(ValidationError):
            GoogleSheetsConfig(**{**base_config, "batch_size": 0})

        # Too large
        with pytest.raises(ValidationError):
            GoogleSheetsConfig(**{**base_config, "batch_size": 1001})

        # Valid range
        config = GoogleSheetsConfig(**{**base_config, "batch_size": 500})
        assert config.batch_size == 500

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        config_dict = {
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "auth_type": "api_key",
                "api_key": "AIzaSyTest_API_Key_1234567890_abcdefghijklmnop"
            },
            "unknown_field": "should not be allowed"
        }
        with pytest.raises(ValidationError) as exc_info:
            GoogleSheetsConfig(**config_dict)
        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(exc_info.value)


class TestSheetConfig:
    """Test SheetConfig validation."""

    def test_valid_sheet_config(self):
        """Test that valid sheet config is accepted."""
        config = SheetConfig(
            name="Sheet1",
            range="A1:Z100",
            headers_row=1,
            skip_rows=0
        )
        assert config.name == "Sheet1"
        assert config.range == "A1:Z100"

    def test_headers_row_minimum(self):
        """Test that headers_row must be >= 1."""
        with pytest.raises(ValidationError):
            SheetConfig(name="Sheet1", headers_row=0)

    def test_skip_rows_minimum(self):
        """Test that skip_rows must be >= 0."""
        with pytest.raises(ValidationError):
            SheetConfig(name="Sheet1", skip_rows=-1)


class TestConnectionStatus:
    """Test ConnectionStatus model."""

    def test_successful_connection(self):
        """Test ConnectionStatus for successful connection."""
        status = ConnectionStatus(
            connected=True,
            message="Successfully connected",
            spreadsheet_title="Test Sheet",
            sheet_count=3
        )
        assert status.connected is True
        assert status.spreadsheet_title == "Test Sheet"
        assert status.error is None

    def test_failed_connection(self):
        """Test ConnectionStatus for failed connection."""
        status = ConnectionStatus(
            connected=False,
            message="Connection failed",
            error="Authentication error"
        )
        assert status.connected is False
        assert status.error == "Authentication error"


class TestSyncResult:
    """Test SyncResult model."""

    def test_successful_sync(self):
        """Test SyncResult for successful sync."""
        result = SyncResult(
            stream_name="Sheet1",
            records_count=100,
            success=True,
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:01:00Z"
        )
        assert result.stream_name == "Sheet1"
        assert result.records_count == 100
        assert result.success is True
        assert result.error is None

    def test_failed_sync(self):
        """Test SyncResult for failed sync."""
        result = SyncResult(
            stream_name="Sheet1",
            records_count=50,
            success=False,
            error="Rate limit exceeded",
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:00:30Z"
        )
        assert result.success is False
        assert result.error == "Rate limit exceeded"
