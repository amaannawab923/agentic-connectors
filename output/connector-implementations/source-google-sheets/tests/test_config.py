"""
Configuration validation tests for Google Sheets connector.
"""
import json
import os
import sys

import pytest
from pydantic import ValidationError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import (
    AuthType,
    ServiceAccountCredentials,
    OAuth2Credentials,
    StreamSelection,
    GoogleSheetsConfig,
    ConfigSchema,
)


class TestServiceAccountCredentials:
    """Test ServiceAccountCredentials validation."""

    def test_valid_service_account_info(self, valid_service_account_info):
        """Test valid service account info is accepted."""
        creds = ServiceAccountCredentials(
            service_account_info=valid_service_account_info
        )
        assert creds.auth_type == "service_account"
        assert creds.service_account_info is not None

    def test_valid_service_account_file(self, tmp_path, valid_service_account_info):
        """Test valid service account file path is accepted."""
        # Write test credentials to a temp file
        creds_file = tmp_path / "service_account.json"
        creds_file.write_text(json.dumps(valid_service_account_info))
        
        creds = ServiceAccountCredentials(
            service_account_file=str(creds_file)
        )
        assert creds.auth_type == "service_account"
        assert creds.service_account_file == str(creds_file)

    def test_service_account_info_as_json_string(self, valid_service_account_info):
        """Test service account info provided as JSON string is parsed."""
        json_str = json.dumps(valid_service_account_info)
        creds = ServiceAccountCredentials(
            service_account_info=json_str
        )
        assert isinstance(creds.service_account_info, dict)
        assert creds.service_account_info.get("type") == "service_account"

    def test_missing_credentials_source_fails(self):
        """Test that missing both credential sources raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials()
        assert "Must provide either service_account_info or service_account_file" in str(exc_info.value)

    def test_invalid_json_string_fails(self):
        """Test that invalid JSON string raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                service_account_info="not valid json"
            )
        assert "Invalid JSON" in str(exc_info.value)

    def test_auth_type_is_literal(self):
        """Test that auth_type has the correct literal value."""
        creds = ServiceAccountCredentials(
            service_account_file="/path/to/creds.json"
        )
        assert creds.auth_type == "service_account"


class TestOAuth2Credentials:
    """Test OAuth2Credentials validation."""

    def test_valid_oauth2_credentials(self):
        """Test valid OAuth2 credentials are accepted."""
        creds = OAuth2Credentials(
            client_id="test-client-id.apps.googleusercontent.com",
            client_secret="test-client-secret",
            refresh_token="test-refresh-token"
        )
        assert creds.auth_type == "oauth2"
        assert creds.client_id == "test-client-id.apps.googleusercontent.com"
        assert creds.client_secret == "test-client-secret"
        assert creds.refresh_token == "test-refresh-token"

    def test_oauth2_with_access_token(self):
        """Test OAuth2 credentials with optional access token."""
        creds = OAuth2Credentials(
            client_id="test-client-id.apps.googleusercontent.com",
            client_secret="test-client-secret",
            refresh_token="test-refresh-token",
            access_token="existing-access-token"
        )
        assert creds.access_token == "existing-access-token"

    def test_missing_client_id_fails(self):
        """Test missing client_id raises error."""
        with pytest.raises(ValidationError):
            OAuth2Credentials(
                client_secret="test-client-secret",
                refresh_token="test-refresh-token"
            )

    def test_missing_client_secret_fails(self):
        """Test missing client_secret raises error."""
        with pytest.raises(ValidationError):
            OAuth2Credentials(
                client_id="test-client-id.apps.googleusercontent.com",
                refresh_token="test-refresh-token"
            )

    def test_missing_refresh_token_fails(self):
        """Test missing refresh_token raises error."""
        with pytest.raises(ValidationError):
            OAuth2Credentials(
                client_id="test-client-id.apps.googleusercontent.com",
                client_secret="test-client-secret"
            )

    def test_empty_client_id_fails(self):
        """Test empty client_id raises error."""
        with pytest.raises(ValidationError):
            OAuth2Credentials(
                client_id="",
                client_secret="test-client-secret",
                refresh_token="test-refresh-token"
            )


class TestGoogleSheetsConfig:
    """Test GoogleSheetsConfig validation."""

    def test_valid_config_with_service_account(self, valid_service_account_config):
        """Test valid config with service account credentials."""
        config = GoogleSheetsConfig.from_dict(valid_service_account_config)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert config.get_auth_type() == "service_account"

    def test_valid_config_with_oauth2(self, valid_oauth2_config):
        """Test valid config with OAuth2 credentials."""
        config = GoogleSheetsConfig.from_dict(valid_oauth2_config)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert config.get_auth_type() == "oauth2"

    def test_spreadsheet_id_from_url(self, valid_service_account_info):
        """Test spreadsheet ID extraction from full URL."""
        config_data = {
            "spreadsheet_id": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
            "credentials": {
                "auth_type": "service_account",
                "service_account_info": valid_service_account_info
            }
        }
        config = GoogleSheetsConfig.from_dict(config_data)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    def test_missing_spreadsheet_id_fails(self, valid_service_account_info):
        """Test missing spreadsheet_id raises error."""
        with pytest.raises(ValidationError):
            GoogleSheetsConfig.from_dict({
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": valid_service_account_info
                }
            })

    def test_empty_spreadsheet_id_fails(self, valid_service_account_info):
        """Test empty spreadsheet_id raises error."""
        with pytest.raises((ValidationError, ValueError)):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "",
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": valid_service_account_info
                }
            })

    def test_invalid_spreadsheet_id_format_fails(self, valid_service_account_info):
        """Test invalid spreadsheet ID format raises error."""
        with pytest.raises((ValidationError, ValueError)):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "invalid id with spaces!",
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": valid_service_account_info
                }
            })

    def test_missing_credentials_fails(self):
        """Test missing credentials raises error."""
        with pytest.raises(ValidationError):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
            })

    def test_default_values(self, valid_service_account_config):
        """Test default configuration values."""
        config = GoogleSheetsConfig.from_dict(valid_service_account_config)
        assert config.row_batch_size == 200
        assert config.requests_per_minute == 60
        assert config.include_row_number is False
        assert config.value_render_option == "FORMATTED_VALUE"
        assert config.date_time_render_option == "FORMATTED_STRING"

    def test_custom_batch_size(self, valid_service_account_info):
        """Test custom batch size configuration."""
        config = GoogleSheetsConfig.from_dict({
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "auth_type": "service_account",
                "service_account_info": valid_service_account_info
            },
            "row_batch_size": 500
        })
        assert config.row_batch_size == 500

    def test_batch_size_min_validation(self, valid_service_account_info):
        """Test batch size minimum value validation."""
        with pytest.raises(ValidationError):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": valid_service_account_info
                },
                "row_batch_size": 0
            })

    def test_batch_size_max_validation(self, valid_service_account_info):
        """Test batch size maximum value validation."""
        with pytest.raises(ValidationError):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": valid_service_account_info
                },
                "row_batch_size": 1001
            })

    def test_invalid_value_render_option_fails(self, valid_service_account_info):
        """Test invalid value_render_option raises error."""
        with pytest.raises(ValidationError):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": valid_service_account_info
                },
                "value_render_option": "INVALID_OPTION"
            })

    def test_invalid_datetime_render_option_fails(self, valid_service_account_info):
        """Test invalid date_time_render_option raises error."""
        with pytest.raises(ValidationError):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials": {
                    "auth_type": "service_account",
                    "service_account_info": valid_service_account_info
                },
                "date_time_render_option": "INVALID_OPTION"
            })

    def test_get_credentials_dict_service_account(self, valid_service_account_config):
        """Test get_credentials_dict returns correct data for service account."""
        config = GoogleSheetsConfig.from_dict(valid_service_account_config)
        creds_dict = config.get_credentials_dict()
        assert "service_account_info" in creds_dict
        assert "service_account_file" in creds_dict

    def test_get_credentials_dict_oauth2(self, valid_oauth2_config):
        """Test get_credentials_dict returns correct data for OAuth2."""
        config = GoogleSheetsConfig.from_dict(valid_oauth2_config)
        creds_dict = config.get_credentials_dict()
        assert creds_dict["client_id"] == "test-client-id.apps.googleusercontent.com"
        assert creds_dict["client_secret"] == "test-client-secret"
        assert creds_dict["refresh_token"] == "test-refresh-token"

    def test_should_sync_sheet_default(self, valid_service_account_config):
        """Test should_sync_sheet returns True by default."""
        config = GoogleSheetsConfig.from_dict(valid_service_account_config)
        assert config.should_sync_sheet("Sheet1") is True
        assert config.should_sync_sheet("AnySheet") is True

    def test_should_sync_sheet_with_selection(self, valid_service_account_info):
        """Test should_sync_sheet with stream selection."""
        config = GoogleSheetsConfig.from_dict({
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "auth_type": "service_account",
                "service_account_info": valid_service_account_info
            },
            "stream_selection": {
                "sheet_names": ["Sheet1", "Sheet2"]
            }
        })
        assert config.should_sync_sheet("Sheet1") is True
        assert config.should_sync_sheet("Sheet2") is True
        assert config.should_sync_sheet("Sheet3") is False

    def test_should_sync_sheet_with_exclusion(self, valid_service_account_info):
        """Test should_sync_sheet with exclusion list."""
        config = GoogleSheetsConfig.from_dict({
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "auth_type": "service_account",
                "service_account_info": valid_service_account_info
            },
            "stream_selection": {
                "exclude_sheets": ["Hidden", "Draft"]
            }
        })
        assert config.should_sync_sheet("Sheet1") is True
        assert config.should_sync_sheet("Hidden") is False
        assert config.should_sync_sheet("Draft") is False

    def test_from_json(self, valid_service_account_config):
        """Test creating config from JSON string."""
        json_str = json.dumps(valid_service_account_config)
        config = GoogleSheetsConfig.from_json(json_str)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"


class TestConfigSchema:
    """Test ConfigSchema JSON schema generation."""

    def test_schema_has_required_properties(self):
        """Test that schema has required properties."""
        schema = ConfigSchema.get_schema()
        assert "properties" in schema
        assert "required" in schema
        assert "spreadsheet_id" in schema["required"]
        assert "credentials" in schema["required"]

    def test_schema_properties_structure(self):
        """Test schema properties structure."""
        schema = ConfigSchema.get_schema()
        props = schema["properties"]
        assert "spreadsheet_id" in props
        assert "credentials" in props
        assert "row_batch_size" in props
        assert "requests_per_minute" in props


class TestDiscriminatorValidation:
    """Test Pydantic discriminator functionality for credentials union."""

    def test_discriminator_service_account(self, valid_service_account_info):
        """Test discriminator correctly identifies service account type."""
        config = GoogleSheetsConfig.from_dict({
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "auth_type": "service_account",
                "service_account_info": valid_service_account_info
            }
        })
        assert isinstance(config.credentials, ServiceAccountCredentials)

    def test_discriminator_oauth2(self):
        """Test discriminator correctly identifies OAuth2 type."""
        config = GoogleSheetsConfig.from_dict({
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "auth_type": "oauth2",
                "client_id": "test-client-id.apps.googleusercontent.com",
                "client_secret": "test-client-secret",
                "refresh_token": "test-refresh-token"
            }
        })
        assert isinstance(config.credentials, OAuth2Credentials)

    def test_unknown_auth_type_fails(self):
        """Test unknown auth_type raises error."""
        with pytest.raises((ValidationError, ValueError)):
            GoogleSheetsConfig.from_dict({
                "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                "credentials": {
                    "auth_type": "unknown_type",
                    "some_field": "value"
                }
            })
