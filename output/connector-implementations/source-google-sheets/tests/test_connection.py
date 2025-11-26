"""Connection check tests for Google Sheets connector."""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import from src package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.connector import GoogleSheetsConnector, ConnectionTestResult, create_connector
from src.config import GoogleSheetsConfig, ServiceAccountCredentials
from src.client import APIError, NotFoundError, PermissionDeniedError
from src.auth import AuthenticationError


class TestConnectionCheck:
    """Test connection checking functionality."""

    def test_check_connection_success(self, service_account_config, mock_sheets_api):
        """Test successful connection check."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        result = connector.check_connection()

        assert result.success is True
        assert result.spreadsheet_title == "Test Spreadsheet"
        assert result.sheet_count == 2
        assert result.error is None

    def test_check_connection_returns_connection_test_result(self, service_account_config, mock_sheets_api):
        """Test that check_connection returns a ConnectionTestResult."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        result = connector.check_connection()

        assert isinstance(result, ConnectionTestResult)

    def test_check_connection_authentication_error(self, service_account_config):
        """Test connection check handles authentication errors."""
        with patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_creds, \
             patch('googleapiclient.discovery.build') as mock_build:

            mock_creds.side_effect = ValueError("Invalid credentials")

            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            result = connector.check_connection()

            # Should return failure, not raise an exception
            assert result.success is False
            assert result.error is not None

    def test_check_connection_not_found_error(self, service_account_config):
        """Test connection check handles spreadsheet not found."""
        # Patch at the module level where these are imported
        with patch('src.auth.service_account.Credentials.from_service_account_info') as mock_creds, \
             patch('src.client.build') as mock_build:

            mock_credentials = MagicMock()
            mock_credentials.valid = True
            mock_credentials.expired = False
            mock_credentials.universe_domain = "googleapis.com"
            mock_creds.return_value = mock_credentials

            mock_service = MagicMock()
            mock_spreadsheets = MagicMock()
            mock_service.spreadsheets = MagicMock(return_value=mock_spreadsheets)

            # Simulate NotFoundError
            from googleapiclient.errors import HttpError
            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.reason = "Not Found"
            mock_get_request = MagicMock()
            mock_get_request.execute = MagicMock(side_effect=HttpError(
                mock_response, b'{"error": {"message": "Spreadsheet not found"}}'
            ))
            mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

            mock_build.return_value = mock_service

            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            result = connector.check_connection()

            assert result.success is False
            assert "not found" in result.message.lower()

    def test_check_connection_permission_denied(self, service_account_config):
        """Test connection check handles permission denied."""
        # Patch at the module level where these are imported
        with patch('src.auth.service_account.Credentials.from_service_account_info') as mock_creds, \
             patch('src.client.build') as mock_build:

            mock_credentials = MagicMock()
            mock_credentials.valid = True
            mock_credentials.expired = False
            mock_credentials.universe_domain = "googleapis.com"
            mock_creds.return_value = mock_credentials

            mock_service = MagicMock()
            mock_spreadsheets = MagicMock()
            mock_service.spreadsheets = MagicMock(return_value=mock_spreadsheets)

            # Simulate PermissionDeniedError
            from googleapiclient.errors import HttpError
            mock_response = MagicMock()
            mock_response.status = 403
            mock_response.reason = "Forbidden"
            mock_get_request = MagicMock()
            mock_get_request.execute = MagicMock(side_effect=HttpError(
                mock_response, b'{"error": {"message": "Permission denied"}}'
            ))
            mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

            mock_build.return_value = mock_service

            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            result = connector.check_connection()

            assert result.success is False
            assert "permission" in result.message.lower()

    def test_connection_test_result_string_representation(self):
        """Test ConnectionTestResult string representation."""
        # Success case
        result_success = ConnectionTestResult(
            success=True,
            message="Connection successful",
            spreadsheet_title="My Spreadsheet",
            sheet_count=3,
        )
        assert "successful" in str(result_success).lower()
        assert "My Spreadsheet" in str(result_success)

        # Failure case
        result_failure = ConnectionTestResult(
            success=False,
            message="Authentication failed",
        )
        assert "failed" in str(result_failure).lower()


class TestConnectorFactory:
    """Test the create_connector factory function."""

    def test_create_connector_with_service_account(self, service_account_config, mock_sheets_api):
        """Test creating connector with service account config dict."""
        connector = create_connector(service_account_config)

        assert isinstance(connector, GoogleSheetsConnector)
        assert connector.config.spreadsheet_id == service_account_config["spreadsheet_id"]

    def test_create_connector_with_oauth2(self, oauth2_config):
        """Test creating connector with OAuth2 config dict."""
        with patch('google.oauth2.credentials.Credentials') as mock_creds:
            connector = create_connector(oauth2_config)

            assert isinstance(connector, GoogleSheetsConnector)
            assert connector.config.spreadsheet_id == oauth2_config["spreadsheet_id"]

    def test_create_connector_auto_detects_auth_type(self, valid_private_key):
        """Test create_connector auto-detects auth type when not specified."""
        config_dict = {
            "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "credentials": {
                "project_id": "test-project",
                "private_key": valid_private_key,
                "client_email": "test@test.iam.gserviceaccount.com",
            }
        }

        with patch('google.oauth2.service_account.Credentials.from_service_account_info'):
            connector = create_connector(config_dict)
            assert isinstance(connector.config.credentials, ServiceAccountCredentials)


class TestConnectorContextManager:
    """Test connector context manager functionality."""

    def test_connector_context_manager(self, service_account_config, mock_sheets_api):
        """Test connector can be used as context manager."""
        config = GoogleSheetsConfig(**service_account_config)

        with GoogleSheetsConnector(config) as connector:
            result = connector.check_connection()
            assert result.success is True

    def test_connector_close_called_on_exit(self, service_account_config, mock_sheets_api):
        """Test connector.close() is called when exiting context."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        with patch.object(connector, 'close') as mock_close:
            with connector:
                pass
            mock_close.assert_called_once()

    def test_connector_explicit_close(self, service_account_config, mock_sheets_api):
        """Test explicit connector close."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        # Access client to create it
        _ = connector.check_connection()

        # Close should not raise
        connector.close()

        # Should be able to close multiple times
        connector.close()
