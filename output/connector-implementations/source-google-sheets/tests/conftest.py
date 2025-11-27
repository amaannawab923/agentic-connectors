"""
Pytest configuration and shared fixtures for Google Sheets connector tests.
"""

import sys
import os
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


def load_fixture(path: str) -> dict:
    """Load a JSON fixture file."""
    fixture_path = FIXTURES_DIR / path
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def valid_rsa_private_key():
    """Load or generate a valid RSA private key."""
    key_path = '/tmp/test_private_key.pem'
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read()
    # Fallback to a test key format
    return """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj
MzEfYyjiWA4R4/M2bS1GB/BOl8Qu2yXNQ7nrwFNh/D8n9Wf8z5wdp5Dm0Y9P5h2w
yKH7H3vEkFCfYR7eFZJ5XwHl+TLYaKqN3Y9M5FnzOlk+hL0PzDLz5p7xKPF6Y7M7
jF8v8cENh7C8cLw7b8y3Q8BfF9X3gI0Fxj5i8m3nLH3nKF8h3cP8mN5dA4d3E7rF
jF8v8cENh7C8cLw7b8y3Q8BfF9X3gI0Fxj5i8m3nLH3nKF8h3cP8mN5dA4d3E7rF
jF8v8cENh7C8cLw7b8y3Q8BfF9X3gI0Fxj5i8m3nLH3nKF8h3cP8mN5dA4d3E7rF
jF8v8cENh7C8cLw7b8y3Q8BfF9X3gI0Fxj5i8m3nLH3nKF8h3cP8mN5dA4d3E7rF
AgMBAAECggEADH0qhZ3kLbBdXxLq3m4xCTKMPK1sZWxGTJ/F6nCmwR9r+W1JZKwC
zRqXzLw3OQmBb2lx1RL7e2qKzRxqXw0h7H3vC9nZqXKPRqXw0h7H3vC9nZqXKPRq
Xw0h7H3vC9nZqXKPRqXw0h7H3vC9nZqXKPRqXw0h7H3vC9nZqXKPRqXw0h7H3vC9
nZqXKPRqXw0h7H3vC9nZqXKPRqXw0h7H3vC9nZqXKPRqXw0h7H3vC9nZqXKPRqXw
0h7H3vC9nZqXKPRqXw0h7H3vC9nZqXKPRqXw0h7H3vC9nZqXKPRqXw0h7H3vC9nZ
qXKPRqXw0h7H3vC9nZqXKPQKBgQDp+z3c7qLKxB3kQwKBgQDp+z3c7qLKxB3kQw==
-----END PRIVATE KEY-----"""


@pytest.fixture
def service_account_fixture(valid_rsa_private_key):
    """Load service account fixture with valid RSA key."""
    fixture = load_fixture('auth/service_account_valid.json')
    fixture['private_key'] = valid_rsa_private_key
    return fixture


@pytest.fixture
def oauth2_fixture():
    """Load OAuth2 credentials fixture."""
    return load_fixture('auth/oauth2_valid.json')


@pytest.fixture
def api_key_fixture():
    """Load API key fixture."""
    return load_fixture('auth/api_key_valid.json')


@pytest.fixture
def spreadsheet_metadata_fixture():
    """Load spreadsheet metadata fixture."""
    return load_fixture('responses/success/spreadsheet_metadata.json')


@pytest.fixture
def sheet_values_fixture():
    """Load sheet values fixture."""
    return load_fixture('responses/success/sheet_values.json')


@pytest.fixture
def header_row_fixture():
    """Load header row fixture."""
    return load_fixture('responses/success/header_row.json')


@pytest.fixture
def error_401_fixture():
    """Load 401 error fixture."""
    return load_fixture('responses/errors/401_unauthorized.json')


@pytest.fixture
def error_404_fixture():
    """Load 404 error fixture."""
    return load_fixture('responses/errors/404_not_found.json')


@pytest.fixture
def valid_service_account_config(service_account_fixture):
    """Create a valid service account config dictionary."""
    return {
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "service_account",
            "service_account_info": json.dumps(service_account_fixture)
        }
    }


@pytest.fixture
def valid_oauth2_config(oauth2_fixture):
    """Create a valid OAuth2 config dictionary."""
    return {
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "oauth2",
            "client_id": oauth2_fixture["client_id"],
            "client_secret": oauth2_fixture["client_secret"],
            "refresh_token": oauth2_fixture["refresh_token"]
        }
    }


@pytest.fixture
def valid_api_key_config(api_key_fixture):
    """Create a valid API key config dictionary."""
    return {
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "api_key",
            "api_key": api_key_fixture["api_key"]
        }
    }


@pytest.fixture
def mock_google_credentials():
    """
    Mock Google credentials at the correct level.

    This mocks:
    - google.oauth2.service_account.Credentials.from_service_account_info
    - googleapiclient.discovery.build
    """
    with patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_creds:
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.expired = False
        mock_credentials.token = "mock-access-token"
        mock_credentials.universe_domain = "googleapis.com"
        mock_credentials.refresh = Mock()
        mock_creds.return_value = mock_credentials

        yield {
            'credentials': mock_creds,
            'credentials_instance': mock_credentials
        }


@pytest.fixture
def mock_sheets_service(spreadsheet_metadata_fixture, sheet_values_fixture, header_row_fixture):
    """
    Mock Google Sheets API service with complete method chains.

    This properly mocks:
    - service.spreadsheets().get().execute()
    - service.spreadsheets().values().get().execute()
    """
    mock_service = MagicMock()

    # Mock spreadsheets() chain
    mock_spreadsheets = MagicMock()
    mock_service.spreadsheets.return_value = mock_spreadsheets

    # Mock spreadsheets().get().execute()
    mock_get_request = MagicMock()
    mock_get_request.execute.return_value = spreadsheet_metadata_fixture
    mock_spreadsheets.get.return_value = mock_get_request

    # Mock spreadsheets().values().get().execute()
    mock_values = MagicMock()
    mock_spreadsheets.values.return_value = mock_values

    mock_values_request = MagicMock()
    mock_values_request.execute.return_value = sheet_values_fixture
    mock_values.get.return_value = mock_values_request

    # Mock spreadsheets().values().batchGet().execute()
    mock_batch_get_request = MagicMock()
    mock_batch_get_request.execute.return_value = {
        "valueRanges": [sheet_values_fixture]
    }
    mock_values.batchGet.return_value = mock_batch_get_request

    return mock_service


@pytest.fixture
def mock_build_service(mock_google_credentials, mock_sheets_service):
    """
    Mock googleapiclient.discovery.build to return a mock service.
    """
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_build.return_value = mock_sheets_service
        yield {
            'build': mock_build,
            'service': mock_sheets_service,
            **mock_google_credentials
        }


@pytest.fixture
def mock_client_class(spreadsheet_metadata_fixture, sheet_values_fixture):
    """
    Mock the GoogleSheetsClient class directly (Level 3 mocking).

    This is a fallback when SDK-level mocking becomes too complex.
    """
    with patch('src.client.GoogleSheetsClient') as MockClientClass:
        mock_client = MagicMock()
        MockClientClass.return_value = mock_client

        # Mock check_connection
        mock_client.check_connection.return_value = (
            True,
            "Successfully connected to spreadsheet 'Test Spreadsheet'",
            {
                "spreadsheet_id": spreadsheet_metadata_fixture["spreadsheetId"],
                "title": spreadsheet_metadata_fixture["properties"]["title"],
                "sheet_count": len(spreadsheet_metadata_fixture["sheets"])
            }
        )

        # Mock get_spreadsheet_metadata
        mock_client.get_spreadsheet_metadata.return_value = spreadsheet_metadata_fixture

        # Mock get_sheet_names
        mock_client.get_sheet_names.return_value = [
            sheet["properties"]["title"]
            for sheet in spreadsheet_metadata_fixture["sheets"]
        ]

        # Mock get_values
        mock_client.get_values.return_value = sheet_values_fixture["values"]

        # Mock get_headers
        mock_client.get_headers.return_value = sheet_values_fixture["values"][0]

        # Mock get_row_count
        mock_client.get_row_count.return_value = 1000

        # Mock get_column_count
        mock_client.get_column_count.return_value = 26

        # Mock read_sheet_data
        mock_client.read_sheet_data.return_value = sheet_values_fixture["values"][1:]

        # Mock read_sheet_in_batches - returns iterator
        def mock_batch_reader(sheet_name, start_row=2, batch_size=200):
            yield sheet_values_fixture["values"][1:]
        mock_client.read_sheet_in_batches = mock_batch_reader

        yield {
            'client_class': MockClientClass,
            'client_instance': mock_client
        }
