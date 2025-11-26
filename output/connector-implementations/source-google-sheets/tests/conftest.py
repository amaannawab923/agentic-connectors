"""Shared test fixtures for Google Sheets connector tests."""

import pytest
import httpretty
import json
import re
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import from src package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def valid_private_key():
    """Generate or load a valid RSA private key for testing."""
    key_path = '/tmp/test_private_key.pem'
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read()
    else:
        # Fallback if key generation failed
        return """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7ld7D+5NlGiNd
Ox9h9nNQEJZ8QRd2H9T5aTHVwMbNVP+Nxk3qKJKcwNKiPGkZC7RpTmDHWHQVJBnT
Qzw1z1aKJM5uH7C4rGPYPWA1y0yVFOD9jF9qKQYN9Rf3Th6dQxQ4HgXPk7JwKVn1
L8kJKfF9x1K7P8jL4J0a5QA9D9qKqDLJNMK6mH3U8Rw1Z9kL7cXWHJD4qJ3KOJ9Y
W6L2M8nP5J4Q3C9V0R7yU5n8D2kL3J9q0M7xK6W4d5L8hN3qK9pJ2vR8bW6nP0L7
cM3qK8dL5J2xR9kN7pW4cL6nM8qK3dL5J9xR2pW7kN4cL8nM6qK5dL3J2xR9pW4k
N7cL8nM3qAgMBAAECggEABJl3ld7D+5NlGiNdOx9h9nNQEJZ8QRd2H9T5aTHVwMbN
VP+Nxk3qKJKcwNKiPGkZC7RpTmDHWHQVJBnTQzw1z1aKJM5uH7C4rGPYPWA1y0yV
FOD9jF9qKQYN9Rf3Th6dQxQ4HgXPk7JwKVn1L8kJKfF9x1K7P8jL4J0a5QA9D9qK
qDLJNMK6mH3U8Rw1Z9kL7cXWHJD4qJ3KOJ9YW6L2M8nP5J4Q3C9V0R7yU5n8D2kL
3J9q0M7xK6W4d5L8hN3qK9pJ2vR8bW6nP0L7cM3qK8dL5J2xR9kN7pW4cL6nM8qK
3dL5J9xR2pW7kN4cL8nM6qK5dL3J2xR9pW4kN7cL8nM3qQKBgQDnld7D+5NlGiNd
-----END PRIVATE KEY-----"""


@pytest.fixture
def service_account_config(valid_private_key):
    """Create a valid service account configuration."""
    return {
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "service_account",
            "type": "service_account",
            "project_id": "test-project-123",
            "private_key_id": "key-id-12345",
            "private_key": valid_private_key,
            "client_email": "test-connector@test-project-123.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test-connector%40test-project-123.iam.gserviceaccount.com"
        }
    }


@pytest.fixture
def oauth2_config():
    """Create a valid OAuth2 configuration."""
    return {
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "oauth2",
            "client_id": "123456789.apps.googleusercontent.com",
            "client_secret": "test-client-secret",
            "refresh_token": "test-refresh-token-12345"
        }
    }


@pytest.fixture
def mock_spreadsheet_metadata():
    """Mock spreadsheet metadata response."""
    return {
        "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "properties": {
            "title": "Test Spreadsheet",
            "locale": "en_US",
            "timeZone": "America/New_York"
        },
        "sheets": [
            {
                "properties": {
                    "sheetId": 0,
                    "title": "Sheet1",
                    "index": 0,
                    "gridProperties": {
                        "rowCount": 1000,
                        "columnCount": 26,
                        "frozenRowCount": 1
                    }
                }
            },
            {
                "properties": {
                    "sheetId": 123456,
                    "title": "Data Sheet",
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
def mock_values_response():
    """Mock values response from sheets API."""
    return {
        "range": "'Sheet1'!A1:D10",
        "majorDimension": "ROWS",
        "values": [
            ["Name", "Email", "Age", "City"],
            ["Alice", "alice@example.com", 30, "New York"],
            ["Bob", "bob@example.com", 25, "Los Angeles"],
            ["Charlie", "charlie@example.com", 35, "Chicago"]
        ]
    }


@pytest.fixture
def mock_header_response():
    """Mock header row response."""
    return {
        "range": "'Sheet1'!1:1",
        "majorDimension": "ROWS",
        "values": [
            ["Name", "Email", "Age", "City"]
        ]
    }


@pytest.fixture
def mock_google_auth():
    """Mock Google authentication to prevent actual API calls."""
    with patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_creds:
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.expired = False
        mock_credentials.token = "mock-access-token"
        mock_credentials.refresh = Mock()
        mock_creds.return_value = mock_credentials
        yield mock_creds


@pytest.fixture
def mock_google_build():
    """Mock googleapiclient.discovery.build."""
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        yield mock_build, mock_service


@pytest.fixture
def mock_sheets_api(mock_spreadsheet_metadata, mock_values_response, mock_header_response):
    """Setup comprehensive mocks for the Google Sheets API."""
    # Patch at the module level where these are imported, not where they're defined
    with patch('src.auth.service_account.Credentials.from_service_account_info') as mock_creds, \
         patch('src.client.build') as mock_build, \
         patch('src.auth.Request') as mock_request:

        # Mock credentials with all required attributes
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.expired = False
        mock_credentials.token = "mock-access-token"
        mock_credentials.refresh = MagicMock()
        mock_credentials.universe_domain = "googleapis.com"  # Required for universe domain validation

        # Handle the with_scopes call chain which is used internally
        mock_credentials.with_scopes = MagicMock(return_value=mock_credentials)

        mock_creds.return_value = mock_credentials

        # Mock API service - need to return MagicMock that has proper resources
        mock_service = MagicMock()

        # Configure the spreadsheets resource
        # IMPORTANT: spreadsheets() is called as a method, so we need to mock it properly
        mock_spreadsheets = MagicMock()
        mock_service.spreadsheets = MagicMock(return_value=mock_spreadsheets)

        # Mock spreadsheets().get() - returns an object with .execute()
        mock_get_request = MagicMock()
        mock_get_request.execute = MagicMock(return_value=mock_spreadsheet_metadata)
        mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

        # Mock spreadsheets().values() - returns an object with .get()
        mock_values = MagicMock()
        mock_spreadsheets.values = MagicMock(return_value=mock_values)

        def mock_values_get(**kwargs):
            mock_response = MagicMock()
            range_notation = kwargs.get('range', '')

            # Return header for row 1
            if ':1' in range_notation or range_notation.endswith(':1'):
                mock_response.execute = MagicMock(return_value=mock_header_response)
            else:
                mock_response.execute = MagicMock(return_value=mock_values_response)

            return mock_response

        mock_values.get = MagicMock(side_effect=mock_values_get)

        mock_build.return_value = mock_service

        yield {
            'credentials': mock_creds,
            'build': mock_build,
            'service': mock_service,
            'spreadsheet_metadata': mock_spreadsheet_metadata,
            'values_response': mock_values_response
        }
