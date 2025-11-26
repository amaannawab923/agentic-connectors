"""
Shared fixtures and mocks for Google Sheets connector tests.
"""
import json
import os
import re
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session")
def valid_private_key():
    """Load or generate a valid RSA private key for testing."""
    key_path = '/tmp/test_private_key.pem'
    try:
        with open(key_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Generate key if not exists
        import subprocess
        subprocess.run([
            'openssl', 'genpkey', '-algorithm', 'RSA',
            '-out', key_path, '-pkeyopt', 'rsa_keygen_bits:2048'
        ], capture_output=True)
        with open(key_path, 'r') as f:
            return f.read()


@pytest.fixture
def valid_service_account_info(valid_private_key):
    """Create a valid service account info dict for testing."""
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key123",
        "private_key": valid_private_key,
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com"
    }


@pytest.fixture
def valid_service_account_config(valid_service_account_info):
    """Create a valid service account configuration."""
    return {
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "service_account",
            "service_account_info": valid_service_account_info
        },
        "row_batch_size": 200,
        "requests_per_minute": 60
    }


@pytest.fixture
def valid_oauth2_config():
    """Create a valid OAuth2 configuration."""
    return {
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "oauth2",
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "test-client-secret",
            "refresh_token": "test-refresh-token"
        }
    }


@pytest.fixture
def mock_spreadsheet_metadata():
    """Create mock spreadsheet metadata response."""
    return {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "properties": {
            "title": "Test Spreadsheet",
            "locale": "en_US"
        },
        "sheets": [
            {
                "properties": {
                    "sheetId": 0,
                    "title": "Sheet1",
                    "index": 0,
                    "gridProperties": {
                        "rowCount": 1000,
                        "columnCount": 26
                    }
                }
            },
            {
                "properties": {
                    "sheetId": 1,
                    "title": "Data & Analysis",
                    "index": 1,
                    "gridProperties": {
                        "rowCount": 500,
                        "columnCount": 10
                    }
                }
            }
        ]
    }


@pytest.fixture
def mock_sheet_values():
    """Create mock sheet values response."""
    return {
        "range": "Sheet1!A1:Z1000",
        "majorDimension": "ROWS",
        "values": [
            ["Name", "Email", "Age"],
            ["John Doe", "john@example.com", "30"],
            ["Jane Smith", "jane@example.com", "25"],
            ["Bob Wilson", "bob@example.com", "35"]
        ]
    }


@pytest.fixture
def mock_header_values():
    """Create mock header row response."""
    return {
        "range": "Sheet1!1:1",
        "majorDimension": "ROWS",
        "values": [
            ["Name", "Email", "Age"]
        ]
    }


@pytest.fixture
def mock_credentials():
    """Create mock Google credentials."""
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False
    mock_creds.token = "mock-access-token"
    mock_creds.service_account_email = "test@test-project.iam.gserviceaccount.com"
    # Required by Google API client to match universe domain
    mock_creds.universe_domain = "googleapis.com"
    return mock_creds


@pytest.fixture
def mock_google_sheets_service(mock_spreadsheet_metadata, mock_sheet_values, mock_header_values):
    """Create mock Google Sheets API service."""
    mock_service = MagicMock()
    
    # Mock spreadsheets().get()
    mock_service.spreadsheets.return_value.get.return_value.execute.return_value = mock_spreadsheet_metadata
    
    # Mock spreadsheets().values().get()
    def mock_values_get(**kwargs):
        mock_execute = MagicMock()
        range_name = kwargs.get('range', '')
        if '!1:1' in range_name:
            mock_execute.execute.return_value = mock_header_values
        else:
            mock_execute.execute.return_value = mock_sheet_values
        return mock_execute
    
    mock_service.spreadsheets.return_value.values.return_value.get.side_effect = mock_values_get
    
    # Mock spreadsheets().values().batchGet()
    mock_service.spreadsheets.return_value.values.return_value.batchGet.return_value.execute.return_value = {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "valueRanges": [mock_sheet_values]
    }
    
    return mock_service
