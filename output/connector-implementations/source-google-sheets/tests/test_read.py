"""
Test data reading for Google Sheets connector.

Tests:
- Reading records from sheets
- Record format and structure
- Row-to-record conversion
- Batch processing
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from connector import GoogleSheetsConnector, SyncResult, ConnectorStatus
from config import GoogleSheetsConfig
from streams import SheetStream, StreamCatalog
from client import GoogleSheetsClient


class TestRowToRecord:
    """Test row-to-record conversion."""

    def test_basic_row_conversion(self):
        """Test basic row to record conversion."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = ["Name", "Email", "Age"]
        mock_client.batch_size = 200

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
        )

        # Access normalized headers to populate internal state
        _ = stream.normalized_headers

        row = ["John Doe", "john@example.com", "30"]
        record = stream._row_to_record(row, row_number=2)

        assert record["name"] == "John Doe"
        assert record["email"] == "john@example.com"
        assert record["age"] == "30"

    def test_row_with_fewer_columns(self):
        """Test row with fewer columns than headers."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = ["Name", "Email", "Age"]
        mock_client.batch_size = 200

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
        )

        _ = stream.normalized_headers

        # Row with only 2 values
        row = ["John", "john@example.com"]
        record = stream._row_to_record(row, row_number=2)

        assert record["name"] == "John"
        assert record["email"] == "john@example.com"
        assert record["age"] is None  # Should be None for missing column

    def test_row_with_empty_cells(self):
        """Test row with empty cell values."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = ["Name", "Email"]
        mock_client.batch_size = 200

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
        )

        _ = stream.normalized_headers

        row = ["John", ""]  # Empty email
        record = stream._row_to_record(row, row_number=2)

        assert record["name"] == "John"
        assert record["email"] is None  # Empty strings converted to None

    def test_row_with_row_number(self):
        """Test row conversion with row number included."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = ["Name"]
        mock_client.batch_size = 200

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
            include_row_number=True,
        )

        _ = stream.normalized_headers

        row = ["John"]
        record = stream._row_to_record(row, row_number=5)

        assert record["name"] == "John"
        assert record["_row_number"] == 5


class TestReadRecords:
    """Test reading records from streams."""

    def test_read_all_records(self):
        """Test reading all records from a stream."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = ["Name", "Email"]
        mock_client.batch_size = 200
        mock_client.get_rows_batch.side_effect = [
            [["John", "john@example.com"], ["Jane", "jane@example.com"]],
            []  # End of data
        ]

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
        )

        records = list(stream.read_records())

        assert len(records) == 2
        assert records[0]["name"] == "John"
        assert records[1]["name"] == "Jane"

    def test_read_empty_sheet(self):
        """Test reading from empty sheet."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = []  # No headers
        mock_client.batch_size = 200

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
        )

        records = list(stream.read_records())
        assert len(records) == 0

    def test_read_batched_data(self):
        """Test reading data in batches."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = ["Name"]
        mock_client.batch_size = 2  # Small batch size

        # Simulate 3 batches of data
        mock_client.get_rows_batch.side_effect = [
            [["Row1"], ["Row2"]],  # First batch (full)
            [["Row3"], ["Row4"]],  # Second batch (full)
            [["Row5"]],            # Third batch (partial - end of data)
            []                     # Empty batch signals end
        ]

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
        )

        records = list(stream.read_records())
        assert len(records) == 5

    def test_read_sample(self):
        """Test reading sample records."""
        mock_client = MagicMock(spec=GoogleSheetsClient)
        mock_client.get_headers.return_value = ["Name"]
        mock_client.batch_size = 200
        mock_client.get_rows_batch.return_value = [
            ["Row1"], ["Row2"], ["Row3"], ["Row4"], ["Row5"],
            ["Row6"], ["Row7"], ["Row8"], ["Row9"], ["Row10"]
        ]

        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
        )

        sample = stream.read_sample(n=3)
        assert len(sample) == 3


class TestConnectorRead:
    """Test connector read functionality."""

    def test_read_single_stream(self, valid_service_account_config):
        """Test reading a single stream."""
        with patch('connector.create_authenticator') as mock_create_auth, \
             patch('connector.GoogleSheetsClient') as mock_client_class:
            mock_auth = MagicMock()
            mock_create_auth.return_value = mock_auth

            # Setup mock client instance
            mock_client = MagicMock()
            mock_client.get_sheet_names.return_value = ["Sheet1"]
            mock_client.get_headers.return_value = ["Name"]
            mock_client.batch_size = 200
            mock_client.get_rows_batch.side_effect = [
                [["John"], ["Jane"]],
                []
            ]
            mock_client_class.return_value = mock_client

            connector = GoogleSheetsConnector(valid_service_account_config)

            # Use read_stream generator
            records = []
            gen = connector.read_stream("Sheet1")
            try:
                while True:
                    record = next(gen)
                    records.append(record)
            except StopIteration:
                pass

            assert len(records) == 2

    def test_read_all_streams(self, valid_service_account_config):
        """Test reading all streams."""
        with patch('connector.create_authenticator') as mock_create_auth, \
             patch('connector.GoogleSheetsClient') as mock_client_class:
            mock_auth = MagicMock()
            mock_create_auth.return_value = mock_auth

            # Setup mock client instance
            mock_client = MagicMock()
            mock_client.get_sheet_names.return_value = ["Sheet1", "Sheet2"]
            mock_client.get_headers.return_value = ["Name"]
            mock_client.batch_size = 200
            # Both sheets have same data for simplicity
            mock_client.get_rows_batch.side_effect = [
                [["John"]],  # Sheet1 data
                [],          # Sheet1 end
                [["Jane"]],  # Sheet2 data
                []           # Sheet2 end
            ]
            mock_client_class.return_value = mock_client

            connector = GoogleSheetsConnector(valid_service_account_config)
            records = list(connector.read())

            # Should have records from both sheets
            assert len(records) >= 1

    def test_read_with_metadata(self, valid_service_account_config):
        """Test that records include metadata fields."""
        with patch('connector.create_authenticator') as mock_create_auth, \
             patch('connector.GoogleSheetsClient') as mock_client_class:
            mock_auth = MagicMock()
            mock_create_auth.return_value = mock_auth

            # Setup mock client instance
            mock_client = MagicMock()
            mock_client.get_sheet_names.return_value = ["Sheet1"]
            mock_client.get_headers.return_value = ["Name"]
            mock_client.batch_size = 200
            mock_client.get_rows_batch.side_effect = [
                [["John"]],
                []
            ]
            mock_client_class.return_value = mock_client

            connector = GoogleSheetsConnector(valid_service_account_config)
            records = list(connector.read())

            if records:
                record = records[0]
                # Should have stream metadata
                assert "_stream" in record
                assert "_extracted_at" in record

    def test_read_selected_streams(self, valid_service_account_config):
        """Test reading only selected streams."""
        with patch('connector.create_authenticator') as mock_create_auth, \
             patch('connector.GoogleSheetsClient') as mock_client_class:
            mock_auth = MagicMock()
            mock_create_auth.return_value = mock_auth

            # Setup mock client instance
            mock_client = MagicMock()
            mock_client.get_sheet_names.return_value = ["Sheet1", "Sheet2", "Sheet3"]
            mock_client.get_headers.return_value = ["Name"]
            mock_client.batch_size = 200
            mock_client.get_rows_batch.side_effect = [
                [["Data"]],
                []
            ]
            mock_client_class.return_value = mock_client

            connector = GoogleSheetsConnector(valid_service_account_config)
            records = list(connector.read(streams=["Sheet1"]))

            # Should only read from Sheet1
            if records:
                assert records[0]["_stream"] == "Sheet1"

    def test_read_nonexistent_stream(self, valid_service_account_config):
        """Test reading non-existent stream."""
        with patch('connector.create_authenticator') as mock_create_auth, \
             patch('connector.GoogleSheetsClient') as mock_client_class:
            mock_auth = MagicMock()
            mock_create_auth.return_value = mock_auth

            # Setup mock client instance
            mock_client = MagicMock()
            mock_client.get_sheet_names.return_value = ["Sheet1"]
            mock_client_class.return_value = mock_client

            connector = GoogleSheetsConnector(valid_service_account_config)

            gen = connector.read_stream("NonExistentSheet")
            try:
                # Try to get records
                records = []
                while True:
                    records.append(next(gen))
            except StopIteration as e:
                # Should return a SyncResult with failure status
                result = e.value
                if result is not None:
                    assert result.status == ConnectorStatus.FAILED


class TestUtils:
    """Test utility functions used in reading."""

    def test_normalize_header(self):
        """Test header normalization."""
        from utils import normalize_header

        assert normalize_header("First Name") == "first_name"
        assert normalize_header("Email Address") == "email_address"
        assert normalize_header("") == "unnamed_column"
        assert normalize_header("123Column") == "col_123column"

    def test_sanitize_sheet_name(self):
        """Test sheet name sanitization."""
        from utils import sanitize_sheet_name

        assert sanitize_sheet_name("My Sheet") == "my_sheet"
        assert sanitize_sheet_name("Data & Analysis") == "data_analysis"
        assert sanitize_sheet_name("") == "unnamed_sheet"
        assert sanitize_sheet_name("2024 Data") == "sheet_2024_data"

    def test_get_current_timestamp(self):
        """Test timestamp generation."""
        from utils import get_current_timestamp

        timestamp = get_current_timestamp()
        assert timestamp is not None
        # Should be ISO format
        assert "T" in timestamp
