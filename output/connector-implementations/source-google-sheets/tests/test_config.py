"""Configuration validation tests for Google Sheets connector."""

import sys
import os
import pytest
from pydantic import ValidationError

# Add parent directory to path to import from src package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import (
    GoogleSheetsConfig,
    ServiceAccountCredentials,
    OAuth2Credentials,
    StreamConfig,
    RateLimitSettings,
    Catalog,
    CatalogEntry,
)


class TestServiceAccountCredentials:
    """Test ServiceAccountCredentials validation."""

    def test_valid_service_account_credentials(self, valid_private_key):
        """Test valid service account credentials are accepted."""
        creds = ServiceAccountCredentials(
            project_id="test-project",
            private_key=valid_private_key,
            client_email="test@test-project.iam.gserviceaccount.com",
        )
        assert creds.auth_type == "service_account"
        assert creds.project_id == "test-project"

    def test_missing_project_id_raises_error(self, valid_private_key):
        """Test missing project_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                private_key=valid_private_key,
                client_email="test@test-project.iam.gserviceaccount.com",
            )
        assert "project_id" in str(exc_info.value)

    def test_missing_private_key_raises_error(self):
        """Test missing private_key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                project_id="test-project",
                client_email="test@test-project.iam.gserviceaccount.com",
            )
        assert "private_key" in str(exc_info.value)

    def test_missing_client_email_raises_error(self, valid_private_key):
        """Test missing client_email raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                project_id="test-project",
                private_key=valid_private_key,
            )
        assert "client_email" in str(exc_info.value)

    def test_invalid_private_key_format(self):
        """Test invalid private key format raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceAccountCredentials(
                project_id="test-project",
                private_key="not-a-valid-key",
                client_email="test@test-project.iam.gserviceaccount.com",
            )
        assert "PEM format" in str(exc_info.value)

    def test_to_google_credentials_dict(self, valid_private_key):
        """Test conversion to Google credentials dictionary."""
        creds = ServiceAccountCredentials(
            project_id="test-project",
            private_key=valid_private_key,
            client_email="test@test-project.iam.gserviceaccount.com",
        )
        creds_dict = creds.to_google_credentials_dict()

        assert creds_dict["type"] == "service_account"
        assert creds_dict["project_id"] == "test-project"
        assert creds_dict["private_key"] == valid_private_key
        assert creds_dict["client_email"] == "test@test-project.iam.gserviceaccount.com"


class TestOAuth2Credentials:
    """Test OAuth2Credentials validation."""

    def test_valid_oauth2_credentials(self):
        """Test valid OAuth2 credentials are accepted."""
        creds = OAuth2Credentials(
            client_id="test-client-id.apps.googleusercontent.com",
            client_secret="test-client-secret",
            refresh_token="test-refresh-token",
        )
        assert creds.auth_type == "oauth2"
        assert creds.client_id == "test-client-id.apps.googleusercontent.com"

    def test_missing_client_id_raises_error(self):
        """Test missing client_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OAuth2Credentials(
                client_secret="test-client-secret",
                refresh_token="test-refresh-token",
            )
        assert "client_id" in str(exc_info.value)

    def test_missing_client_secret_raises_error(self):
        """Test missing client_secret raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OAuth2Credentials(
                client_id="test-client-id",
                refresh_token="test-refresh-token",
            )
        assert "client_secret" in str(exc_info.value)

    def test_missing_refresh_token_raises_error(self):
        """Test missing refresh_token raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OAuth2Credentials(
                client_id="test-client-id",
                client_secret="test-client-secret",
            )
        assert "refresh_token" in str(exc_info.value)


class TestGoogleSheetsConfig:
    """Test GoogleSheetsConfig validation."""

    def test_valid_config_with_service_account(self, service_account_config):
        """Test valid configuration with service account credentials."""
        config = GoogleSheetsConfig(**service_account_config)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert isinstance(config.credentials, ServiceAccountCredentials)

    def test_valid_config_with_oauth2(self, oauth2_config):
        """Test valid configuration with OAuth2 credentials."""
        config = GoogleSheetsConfig(**oauth2_config)
        assert config.spreadsheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert isinstance(config.credentials, OAuth2Credentials)

    def test_missing_spreadsheet_id_raises_error(self, valid_private_key):
        """Test missing spreadsheet_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GoogleSheetsConfig(
                credentials=ServiceAccountCredentials(
                    project_id="test-project",
                    private_key=valid_private_key,
                    client_email="test@test.iam.gserviceaccount.com",
                )
            )
        assert "spreadsheet_id" in str(exc_info.value)

    def test_invalid_spreadsheet_id_format(self, valid_private_key):
        """Test invalid spreadsheet_id format raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GoogleSheetsConfig(
                spreadsheet_id="abc",  # Too short
                credentials=ServiceAccountCredentials(
                    project_id="test-project",
                    private_key=valid_private_key,
                    client_email="test@test.iam.gserviceaccount.com",
                )
            )
        assert "spreadsheet_id" in str(exc_info.value).lower() or "too short" in str(exc_info.value).lower()

    def test_discriminator_works_for_auth_type(self, service_account_config, oauth2_config):
        """Test that Pydantic discriminator correctly identifies credential type."""
        # Service account
        config1 = GoogleSheetsConfig(**service_account_config)
        assert config1.credentials.auth_type == "service_account"

        # OAuth2
        config2 = GoogleSheetsConfig(**oauth2_config)
        assert config2.credentials.auth_type == "oauth2"

    def test_default_rate_limit_settings(self, service_account_config):
        """Test default rate limit settings are applied."""
        config = GoogleSheetsConfig(**service_account_config)
        assert config.rate_limit.requests_per_minute == 60
        assert config.rate_limit.max_retries == 5
        assert config.rate_limit.base_delay == 1.0
        assert config.rate_limit.max_delay == 60.0

    def test_custom_rate_limit_settings(self, service_account_config):
        """Test custom rate limit settings are accepted."""
        service_account_config["rate_limit"] = {
            "requests_per_minute": 100,
            "max_retries": 3,
            "base_delay": 2.0,
            "max_delay": 30.0,
        }
        config = GoogleSheetsConfig(**service_account_config)
        assert config.rate_limit.requests_per_minute == 100
        assert config.rate_limit.max_retries == 3

    def test_invalid_rate_limit_raises_error(self, service_account_config):
        """Test invalid rate limit settings raise validation error."""
        service_account_config["rate_limit"] = {
            "requests_per_minute": 500,  # Over the limit of 300
        }
        with pytest.raises(ValidationError):
            GoogleSheetsConfig(**service_account_config)

    def test_from_dict_auto_detects_service_account(self, valid_private_key):
        """Test from_dict auto-detects service account credentials."""
        config_dict = {
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "project_id": "test-project",
                "private_key": valid_private_key,
                "client_email": "test@test.iam.gserviceaccount.com",
            }
        }
        config = GoogleSheetsConfig.from_dict(config_dict)
        assert isinstance(config.credentials, ServiceAccountCredentials)

    def test_from_dict_auto_detects_oauth2(self):
        """Test from_dict auto-detects OAuth2 credentials."""
        config_dict = {
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "refresh_token": "test-refresh-token",
            }
        }
        config = GoogleSheetsConfig.from_dict(config_dict)
        assert isinstance(config.credentials, OAuth2Credentials)


class TestStreamConfig:
    """Test StreamConfig validation."""

    def test_valid_stream_config(self):
        """Test valid stream configuration."""
        stream = StreamConfig(name="Sheet1")
        assert stream.name == "Sheet1"
        assert stream.header_row == 1
        assert stream.batch_size == 1000
        assert stream.enabled is True

    def test_custom_stream_config(self):
        """Test custom stream configuration."""
        stream = StreamConfig(
            name="Data",
            header_row=2,
            batch_size=500,
            enabled=False,
        )
        assert stream.header_row == 2
        assert stream.batch_size == 500
        assert stream.enabled is False

    def test_invalid_header_row(self):
        """Test invalid header row raises error."""
        with pytest.raises(ValidationError):
            StreamConfig(name="Sheet1", header_row=0)  # Must be >= 1

    def test_invalid_batch_size(self):
        """Test invalid batch size raises error."""
        with pytest.raises(ValidationError):
            StreamConfig(name="Sheet1", batch_size=20000)  # Over limit


class TestCatalog:
    """Test Catalog and CatalogEntry."""

    def test_catalog_entry_creation(self):
        """Test creating a catalog entry."""
        entry = CatalogEntry(
            stream_name="Sheet1",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": ["null", "string"]},
                    "email": {"type": ["null", "string"]},
                }
            }
        )
        assert entry.stream_name == "Sheet1"
        assert entry.supported_sync_modes == ["full_refresh"]

    def test_catalog_get_stream(self):
        """Test getting a stream from catalog by name."""
        entry1 = CatalogEntry(
            stream_name="Sheet1",
            schema={"type": "object", "properties": {}}
        )
        entry2 = CatalogEntry(
            stream_name="Sheet2",
            schema={"type": "object", "properties": {}}
        )
        catalog = Catalog(streams=[entry1, entry2])

        found = catalog.get_stream("Sheet1")
        assert found is not None
        assert found.stream_name == "Sheet1"

        not_found = catalog.get_stream("NonExistent")
        assert not_found is None

    def test_catalog_get_stream_names(self):
        """Test getting all stream names from catalog."""
        entry1 = CatalogEntry(
            stream_name="Sheet1",
            schema={"type": "object", "properties": {}}
        )
        entry2 = CatalogEntry(
            stream_name="Data",
            schema={"type": "object", "properties": {}}
        )
        catalog = Catalog(streams=[entry1, entry2])

        names = catalog.get_stream_names()
        assert names == ["Sheet1", "Data"]
