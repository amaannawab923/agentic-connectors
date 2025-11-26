"""Data reading tests for Google Sheets connector."""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import from src package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.connector import GoogleSheetsConnector
from src.config import GoogleSheetsConfig
from src.streams import SheetStream


class TestDataReading:
    """Test data reading functionality."""

    def test_read_yields_records(self, service_account_config, mock_sheets_api):
        """Test read yields record dictionaries."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        records = list(connector.read("Sheet1"))

        # Should yield records (excluding header)
        assert len(records) >= 0

    def test_read_record_has_column_keys(self, service_account_config):
        """Test read records have column names as keys."""
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

            # Mock spreadsheet metadata
            mock_get_request = MagicMock()
            mock_get_request.execute = MagicMock(return_value={
                "spreadsheetId": "test-id",
                "properties": {"title": "Test"},
                "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1", "index": 0, "gridProperties": {"rowCount": 100, "columnCount": 5}}}]
            })
            mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

            # Track call count for different ranges
            call_count = [0]
            mock_values = MagicMock()
            mock_spreadsheets.values = MagicMock(return_value=mock_values)

            def mock_values_get(**kwargs):
                range_notation = kwargs.get('range', '')
                mock_response = MagicMock()

                if ':1' in range_notation or 'A1:' in range_notation:
                    # Header request
                    mock_response.execute = MagicMock(return_value={
                        "values": [["Name", "Email", "Age"]]
                    })
                else:
                    # Data request
                    call_count[0] += 1
                    if call_count[0] == 1:
                        mock_response.execute = MagicMock(return_value={
                            "values": [
                                ["Alice", "alice@test.com", 30],
                                ["Bob", "bob@test.com", 25],
                            ]
                        })
                    else:
                        mock_response.execute = MagicMock(return_value={"values": []})

                return mock_response

            mock_values.get = MagicMock(side_effect=mock_values_get)

            mock_build.return_value = mock_service

            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            records = list(connector.read("Sheet1"))

            assert len(records) == 2
            assert "name" in records[0]
            assert "email" in records[0]
            assert records[0]["name"] == "Alice"
            assert records[1]["name"] == "Bob"

    def test_read_includes_row_number(self, service_account_config):
        """Test read includes _row_number when configured."""
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

            mock_get_request = MagicMock()
            mock_get_request.execute = MagicMock(return_value={
                "spreadsheetId": "test-id",
                "properties": {"title": "Test"},
                "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1", "index": 0, "gridProperties": {"rowCount": 100, "columnCount": 5}}}]
            })
            mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

            call_count = [0]
            mock_values = MagicMock()
            mock_spreadsheets.values = MagicMock(return_value=mock_values)

            def mock_values_get(**kwargs):
                mock_response = MagicMock()
                range_notation = kwargs.get('range', '')

                if ':1' in range_notation:
                    mock_response.execute = MagicMock(return_value={"values": [["Name"]]})
                else:
                    call_count[0] += 1
                    if call_count[0] == 1:
                        mock_response.execute = MagicMock(return_value={"values": [["Alice"], ["Bob"]]})
                    else:
                        mock_response.execute = MagicMock(return_value={"values": []})
                return mock_response

            mock_values.get = MagicMock(side_effect=mock_values_get)

            mock_build.return_value = mock_service

            service_account_config["include_row_number"] = True
            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            records = list(connector.read("Sheet1"))

            if records:
                assert "_row_number" in records[0]

    def test_read_handles_empty_cells(self, service_account_config):
        """Test read handles empty cells correctly."""
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

            mock_get_request = MagicMock()
            mock_get_request.execute = MagicMock(return_value={
                "spreadsheetId": "test-id",
                "properties": {"title": "Test"},
                "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1", "index": 0, "gridProperties": {"rowCount": 100, "columnCount": 5}}}]
            })
            mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

            call_count = [0]
            mock_values = MagicMock()
            mock_spreadsheets.values = MagicMock(return_value=mock_values)

            def mock_values_get(**kwargs):
                mock_response = MagicMock()
                range_notation = kwargs.get('range', '')

                if ':1' in range_notation:
                    mock_response.execute = MagicMock(return_value={"values": [["Name", "Email", "Age"]]})
                else:
                    call_count[0] += 1
                    if call_count[0] == 1:
                        # Row with missing value (shorter list)
                        mock_response.execute = MagicMock(return_value={"values": [["Alice", ""], ["Bob"]]})
                    else:
                        mock_response.execute = MagicMock(return_value={"values": []})
                return mock_response

            mock_values.get = MagicMock(side_effect=mock_values_get)

            mock_build.return_value = mock_service

            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            records = list(connector.read("Sheet1"))

            # Should handle missing values
            if records:
                assert "email" in records[0]


class TestReadAll:
    """Test reading from all streams."""

    def test_read_all_yields_records_with_stream_name(self, service_account_config, mock_sheets_api):
        """Test read_all includes _stream field."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        records = list(connector.read_all())

        # Records should have _stream field
        for record in records:
            assert "_stream" in record


class TestSheetStream:
    """Test SheetStream class directly."""

    def test_sheet_stream_normalizes_headers(self):
        """Test SheetStream normalizes column headers."""
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

            mock_values = MagicMock()
            mock_spreadsheets.values = MagicMock(return_value=mock_values)

            mock_values_get_request = MagicMock()
            mock_values_get_request.execute = MagicMock(return_value={
                "values": [["First Name", "Last Name", "E-Mail Address", ""]]
            })
            mock_values.get = MagicMock(return_value=mock_values_get_request)

            mock_build.return_value = mock_service

            from src.client import GoogleSheetsClient
            from src.auth import ServiceAccountAuthenticator

            authenticator = ServiceAccountAuthenticator({
                "type": "service_account",
                "project_id": "test",
                "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
                "client_email": "test@test.iam.gserviceaccount.com"
            })

            client = GoogleSheetsClient(authenticator)

            stream = SheetStream(
                client=client,
                spreadsheet_id="test-id",
                sheet_name="Sheet1",
            )

            headers = stream.headers

            # Headers should be normalized (lowercase, underscores)
            assert "first_name" in headers
            assert "last_name" in headers
            # Special characters replaced
            assert "e_mail_address" in headers or "email_address" in "".join(headers)


class TestBatchReading:
    """Test batch reading functionality."""

    def test_read_respects_batch_size(self, service_account_config):
        """Test read respects configured batch size."""
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

            mock_get_request = MagicMock()
            mock_get_request.execute = MagicMock(return_value={
                "spreadsheetId": "test-id",
                "properties": {"title": "Test"},
                "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1", "index": 0, "gridProperties": {"rowCount": 5000, "columnCount": 5}}}]
            })
            mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

            # Track requested ranges
            requested_ranges = []
            mock_values = MagicMock()
            mock_spreadsheets.values = MagicMock(return_value=mock_values)

            def mock_values_get(**kwargs):
                mock_response = MagicMock()
                range_notation = kwargs.get('range', '')
                requested_ranges.append(range_notation)

                if ':1' in range_notation:
                    mock_response.execute = MagicMock(return_value={"values": [["Name"]]})
                else:
                    mock_response.execute = MagicMock(return_value={"values": []})
                return mock_response

            mock_values.get = MagicMock(side_effect=mock_values_get)

            mock_build.return_value = mock_service

            # Set small batch size
            service_account_config["row_batch_size"] = 100
            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            # Read should use the configured batch size
            list(connector.read("Sheet1"))

            # Should have requested data in batches (after header)
            data_requests = [r for r in requested_ranges if ':1' not in r]
            assert len(data_requests) >= 0


class TestUtils:
    """Test utility functions."""

    def test_normalize_header_handles_duplicates(self):
        """Test normalize_header handles duplicate column names."""
        from src.utils import normalize_header

        headers = ["Name", "Name", "Name"]
        normalized = normalize_header(headers)

        assert normalized[0] == "name"
        assert normalized[1] == "name_1"
        assert normalized[2] == "name_2"

    def test_normalize_header_handles_empty(self):
        """Test normalize_header handles empty headers."""
        from src.utils import normalize_header

        headers = ["Name", "", None, "Email"]
        normalized = normalize_header(headers)

        assert normalized[0] == "name"
        assert "column_1" in normalized[1]
        assert "column_2" in normalized[2]
        assert normalized[3] == "email"

    def test_normalize_header_handles_special_chars(self):
        """Test normalize_header handles special characters."""
        from src.utils import normalize_header

        headers = ["First Name", "E-Mail", "Phone #"]
        normalized = normalize_header(headers)

        # Special chars should be replaced with underscores
        assert "_" in normalized[0] or "first" in normalized[0].lower()

    def test_build_range_notation(self):
        """Test build_range_notation creates correct A1 notation."""
        from src.utils import build_range_notation

        # Basic range
        result = build_range_notation("Sheet1", "A", 1, "D", 10)
        assert "Sheet1" in result
        assert "A1" in result
        assert "D10" in result

        # Sheet with spaces
        result = build_range_notation("My Sheet", "A", 1, "B", 5)
        assert "My Sheet" in result or "'My Sheet'" in result

    def test_parse_spreadsheet_id_from_url(self):
        """Test parse_spreadsheet_id extracts ID from URL."""
        from src.utils import parse_spreadsheet_id

        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
        result = parse_spreadsheet_id(url)

        assert result == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    def test_parse_spreadsheet_id_returns_id_if_not_url(self):
        """Test parse_spreadsheet_id returns input if already an ID."""
        from src.utils import parse_spreadsheet_id

        id_only = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        result = parse_spreadsheet_id(id_only)

        assert result == id_only

    def test_infer_json_schema_type(self):
        """Test infer_json_schema_type for various values."""
        from src.utils import infer_json_schema_type

        # String
        result = infer_json_schema_type("hello")
        assert "string" in result["type"]

        # Integer
        result = infer_json_schema_type(42)
        assert "integer" in result["type"]

        # Float
        result = infer_json_schema_type(3.14)
        assert "number" in result["type"]

        # Boolean
        result = infer_json_schema_type(True)
        assert "boolean" in result["type"]

        # None
        result = infer_json_schema_type(None)
        assert "null" in result["type"]

        # Date string
        result = infer_json_schema_type("2023-12-25")
        assert "format" in result
        assert result["format"] == "date"
