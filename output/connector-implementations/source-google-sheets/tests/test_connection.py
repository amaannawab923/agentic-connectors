"""
Connection check tests for Google Sheets connector.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auth import AuthenticationError, ServiceAccountAuth, OAuth2Auth, create_authenticator
from client import GoogleSheetsClient, GoogleSheetsAPIError, SpreadsheetNotFoundError, AccessDeniedError
from connector import GoogleSheetsConnector, ConnectorStatus


class TestServiceAccountAuth:
    """Test ServiceAccountAuth authentication handler."""

    def test_service_account_auth_init_with_info(self, valid_service_account_info):
        """Test ServiceAccountAuth initialization with info dict."""
        auth = ServiceAccountAuth(service_account_info=valid_service_account_info)
        assert auth._service_account_info == valid_service_account_info

    def test_service_account_auth_init_with_file(self, tmp_path, valid_service_account_info):
        """Test ServiceAccountAuth initialization with file path."""
        import json
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(valid_service_account_info))
        
        auth = ServiceAccountAuth(service_account_file=str(creds_file))
        assert auth._service_account_file == str(creds_file)

    def test_service_account_auth_missing_credentials_fails(self):
        """Test ServiceAccountAuth fails without credentials."""
        with pytest.raises(AuthenticationError) as exc_info:
            ServiceAccountAuth()
        assert "Must provide either service_account_info or service_account_file" in str(exc_info.value)

    @patch('auth.service_account.Credentials')
    def test_service_account_get_credentials(self, mock_creds_class, valid_service_account_info, mock_credentials):
        """Test ServiceAccountAuth.get_credentials() method."""
        mock_creds_class.from_service_account_info.return_value = mock_credentials
        
        auth = ServiceAccountAuth(service_account_info=valid_service_account_info)
        creds = auth.get_credentials()
        
        mock_creds_class.from_service_account_info.assert_called_once()
        assert creds == mock_credentials


class TestOAuth2Auth:
    """Test OAuth2Auth authentication handler."""

    def test_oauth2_auth_init(self):
        """Test OAuth2Auth initialization."""
        auth = OAuth2Auth(
            client_id="test-client-id",
            client_secret="test-secret",
            refresh_token="test-refresh-token"
        )
        assert auth._client_id == "test-client-id"
        assert auth._client_secret == "test-secret"
        assert auth._refresh_token == "test-refresh-token"

    @patch('auth.Credentials')
    @patch('auth.Request')
    def test_oauth2_get_credentials(self, mock_request, mock_creds_class, mock_credentials):
        """Test OAuth2Auth.get_credentials() method."""
        mock_creds_class.from_authorized_user_info.return_value = mock_credentials
        mock_credentials.expired = False
        mock_credentials.token = "mock-token"
        
        auth = OAuth2Auth(
            client_id="test-client-id",
            client_secret="test-secret",
            refresh_token="test-refresh-token"
        )
        creds = auth.get_credentials()
        
        mock_creds_class.from_authorized_user_info.assert_called_once()


class TestCreateAuthenticator:
    """Test create_authenticator factory function."""

    def test_create_service_account_authenticator(self, valid_service_account_info):
        """Test creating service account authenticator."""
        auth = create_authenticator("service_account", {
            "service_account_info": valid_service_account_info
        })
        assert isinstance(auth, ServiceAccountAuth)

    def test_create_oauth2_authenticator(self):
        """Test creating OAuth2 authenticator."""
        auth = create_authenticator("oauth2", {
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "refresh_token": "test-refresh-token"
        })
        assert isinstance(auth, OAuth2Auth)

    def test_create_unknown_type_fails(self):
        """Test creating unknown auth type fails."""
        with pytest.raises(AuthenticationError) as exc_info:
            create_authenticator("unknown", {})
        assert "Unknown authentication type" in str(exc_info.value)


class TestGoogleSheetsClient:
    """Test GoogleSheetsClient operations."""

    @patch('client.build')
    def test_client_get_spreadsheet_metadata(self, mock_build, mock_credentials, mock_spreadsheet_metadata):
        """Test getting spreadsheet metadata."""
        # Setup mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = mock_spreadsheet_metadata
        
        # Create mock authenticator
        mock_auth = MagicMock()
        mock_auth.get_credentials.return_value = mock_credentials
        
        # Test
        client = GoogleSheetsClient(authenticator=mock_auth)
        metadata = client.get_spreadsheet_metadata("test-spreadsheet-id")
        
        assert metadata == mock_spreadsheet_metadata
        mock_service.spreadsheets.return_value.get.assert_called_once_with(spreadsheetId="test-spreadsheet-id")

    @patch('client.build')
    def test_client_get_sheet_names(self, mock_build, mock_credentials, mock_spreadsheet_metadata):
        """Test getting sheet names."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = mock_spreadsheet_metadata
        
        mock_auth = MagicMock()
        mock_auth.get_credentials.return_value = mock_credentials
        
        client = GoogleSheetsClient(authenticator=mock_auth)
        names = client.get_sheet_names("test-spreadsheet-id")
        
        assert "Sheet1" in names
        assert "Data & Analysis" in names

    @patch('client.build')
    def test_client_get_values(self, mock_build, mock_credentials, mock_sheet_values):
        """Test getting sheet values."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = mock_sheet_values
        
        mock_auth = MagicMock()
        mock_auth.get_credentials.return_value = mock_credentials
        
        client = GoogleSheetsClient(authenticator=mock_auth)
        values = client.get_values("test-id", "Sheet1!A1:Z100")
        
        assert len(values) == 4  # Header + 3 data rows
        assert values[0] == ["Name", "Email", "Age"]


class TestConnectionCheck:
    """Test connector connection checking."""

    @patch('connector.GoogleSheetsClient')
    @patch('connector.create_authenticator')
    def test_check_connection_success(self, mock_create_auth, mock_client_class, 
                                       valid_service_account_config, mock_spreadsheet_metadata):
        """Test successful connection check."""
        # Setup mocks
        mock_auth = MagicMock()
        mock_create_auth.return_value = mock_auth
        
        mock_client = MagicMock()
        mock_client.get_spreadsheet_metadata.return_value = mock_spreadsheet_metadata
        mock_client_class.return_value = mock_client
        
        # Test
        connector = GoogleSheetsConnector(valid_service_account_config)
        result = connector.check_connection()
        
        assert result.status == ConnectorStatus.SUCCEEDED
        assert "Test Spreadsheet" in result.message
        assert result.details["sheet_count"] == 2

    @patch('connector.GoogleSheetsClient')
    @patch('connector.create_authenticator')
    def test_check_connection_auth_failure(self, mock_create_auth, mock_client_class,
                                            valid_service_account_config):
        """Test connection check with authentication failure."""
        mock_auth = MagicMock()
        mock_create_auth.return_value = mock_auth
        
        mock_client = MagicMock()
        mock_client.get_spreadsheet_metadata.side_effect = AuthenticationError(
            "Invalid credentials",
            details={"error": "test"}
        )
        mock_client_class.return_value = mock_client
        
        connector = GoogleSheetsConnector(valid_service_account_config)
        result = connector.check_connection()
        
        assert result.status == ConnectorStatus.FAILED
        assert "Authentication failed" in result.message

    @patch('connector.GoogleSheetsClient')
    @patch('connector.create_authenticator')
    def test_check_connection_spreadsheet_not_found(self, mock_create_auth, mock_client_class,
                                                     valid_service_account_config):
        """Test connection check with spreadsheet not found error."""
        mock_auth = MagicMock()
        mock_create_auth.return_value = mock_auth
        
        mock_client = MagicMock()
        mock_client.get_spreadsheet_metadata.side_effect = SpreadsheetNotFoundError(
            "Spreadsheet not found",
            status_code=404
        )
        mock_client_class.return_value = mock_client
        
        connector = GoogleSheetsConnector(valid_service_account_config)
        result = connector.check_connection()
        
        assert result.status == ConnectorStatus.FAILED
        assert "Spreadsheet not found" in result.message

    @patch('connector.GoogleSheetsClient')
    @patch('connector.create_authenticator')
    def test_check_connection_access_denied(self, mock_create_auth, mock_client_class,
                                            valid_service_account_config):
        """Test connection check with access denied error."""
        mock_auth = MagicMock()
        mock_create_auth.return_value = mock_auth
        
        mock_client = MagicMock()
        mock_client.get_spreadsheet_metadata.side_effect = AccessDeniedError(
            "Access denied",
            status_code=403
        )
        mock_client_class.return_value = mock_client
        
        connector = GoogleSheetsConnector(valid_service_account_config)
        result = connector.check_connection()
        
        assert result.status == ConnectorStatus.FAILED
        assert "Access denied" in result.message
