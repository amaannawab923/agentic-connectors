"""
Data reading tests for Google Sheets connector.

These tests verify that the connector can read data from sheets
using mocked Google API responses.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.config import GoogleSheetsConfig
from src.connector import GoogleSheetsConnector, Record, StateMessage
from src.streams import SheetStream
from src.client import GoogleSheetsClient


class TestDataReading:
    """Test data reading functionality."""

    def test_read_returns_records(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture,
        sheet_values_fixture
    ):
        """Test that read returns Record objects."""
        with patch.object(GoogleSheetsClient, 'get_spreadsheet_metadata') as mock_metadata:
            mock_metadata.return_value = spreadsheet_metadata_fixture

            with patch.object(GoogleSheetsClient, 'get_headers') as mock_headers:
                mock_headers.return_value = sheet_values_fixture["values"][0]

                with patch.object(GoogleSheetsClient, 'get_row_count') as mock_row_count:
                    mock_row_count.return_value = 1000

                    with patch.object(GoogleSheetsClient, 'get_column_count') as mock_col_count:
                        mock_col_count.return_value = 26

                        with patch.object(GoogleSheetsClient, 'read_sheet_in_batches') as mock_batches:
                            mock_batches.return_value = iter([sheet_values_fixture["values"][1:]])

                            config = GoogleSheetsConfig(**valid_service_account_config)
                            connector = GoogleSheetsConnector(config)

                            records = list(connector.read())

                            # Should have some records
                            assert len(records) > 0

                            # Should contain Record and StateMessage objects
                            record_types = set(type(r) for r in records)
                            assert Record in record_types or StateMessage in record_types

    def test_read_with_selected_streams(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture,
        sheet_values_fixture
    ):
        """Test reading from specific selected streams."""
        with patch.object(GoogleSheetsClient, 'get_spreadsheet_metadata') as mock_metadata:
            mock_metadata.return_value = spreadsheet_metadata_fixture

            with patch.object(GoogleSheetsClient, 'get_headers') as mock_headers:
                mock_headers.return_value = sheet_values_fixture["values"][0]

                with patch.object(GoogleSheetsClient, 'get_row_count') as mock_row_count:
                    mock_row_count.return_value = 1000

                    with patch.object(GoogleSheetsClient, 'get_column_count') as mock_col_count:
                        mock_col_count.return_value = 26

                        with patch.object(GoogleSheetsClient, 'read_sheet_in_batches') as mock_batches:
                            mock_batches.return_value = iter([sheet_values_fixture["values"][1:]])

                            config = GoogleSheetsConfig(**valid_service_account_config)
                            connector = GoogleSheetsConnector(config)

                            # Read only Sheet1
                            records = list(connector.read(selected_streams=["Sheet1"]))

                            # Should have some records
                            for record in records:
                                if isinstance(record, Record):
                                    assert record.stream == "Sheet1"


class TestRecord:
    """Test Record class."""

    def test_record_to_dict(self):
        """Test Record.to_dict method."""
        record = Record(
            stream="Sheet1",
            data={"id": 1, "name": "Test"},
            emitted_at="2024-01-01T00:00:00Z"
        )
        record_dict = record.to_dict()

        assert record_dict["type"] == "RECORD"
        assert record_dict["stream"] == "Sheet1"
        assert record_dict["data"]["id"] == 1
        assert record_dict["emitted_at"] == "2024-01-01T00:00:00Z"

    def test_record_to_json(self):
        """Test Record.to_json method."""
        record = Record(
            stream="Sheet1",
            data={"id": 1},
            emitted_at="2024-01-01T00:00:00Z"
        )
        json_str = record.to_json()

        assert isinstance(json_str, str)
        assert "RECORD" in json_str
        assert "Sheet1" in json_str


class TestStateMessage:
    """Test StateMessage class."""

    def test_state_message_to_dict(self):
        """Test StateMessage.to_dict method."""
        state = StateMessage(
            data={"stream": "Sheet1", "completed": True}
        )
        state_dict = state.to_dict()

        assert state_dict["type"] == "STATE"
        assert state_dict["data"]["stream"] == "Sheet1"
        assert state_dict["data"]["completed"] is True

    def test_state_message_to_json(self):
        """Test StateMessage.to_json method."""
        state = StateMessage(
            data={"stream": "Sheet1", "records_read": 100}
        )
        json_str = state.to_json()

        assert isinstance(json_str, str)
        assert "STATE" in json_str


class TestRowTransformation:
    """Test row transformation functionality."""

    def test_transform_row_includes_row_number(self):
        """Test that transformed rows include _row_number."""
        mock_client = MagicMock()
        stream = SheetStream(
            name="TestSheet",
            client=mock_client,
            sheet_id=0,
            include_row_numbers=True
        )

        row = ["Alice", "alice@example.com", "active"]
        headers = ["Name", "Email", "Status"]

        record = stream._transform_row(row, headers, row_number=2)

        assert "_row_number" in record
        assert record["_row_number"] == 2

    def test_transform_row_sanitizes_column_names(self):
        """Test that column names are sanitized."""
        mock_client = MagicMock()
        stream = SheetStream(
            name="TestSheet",
            client=mock_client,
            sheet_id=0,
            sanitize_names=True
        )

        row = ["value1", "value2"]
        headers = ["Column Name With Spaces", "Special@Characters!"]

        record = stream._transform_row(row, headers, row_number=2)

        # Check that headers are sanitized
        assert "column_name_with_spaces" in record
        assert "special_characters" in record

    def test_transform_row_handles_missing_values(self):
        """Test that missing values are handled correctly."""
        mock_client = MagicMock()
        stream = SheetStream(
            name="TestSheet",
            client=mock_client,
            sheet_id=0
        )

        # Row has fewer values than headers
        row = ["Alice"]
        headers = ["Name", "Email", "Status"]

        record = stream._transform_row(row, headers, row_number=2)

        assert record["name"] == "Alice"
        assert record["email"] is None
        assert record["status"] is None

    def test_transform_row_converts_empty_to_none(self):
        """Test that empty strings are converted to None."""
        mock_client = MagicMock()
        stream = SheetStream(
            name="TestSheet",
            client=mock_client,
            sheet_id=0
        )

        row = ["Alice", "", "active"]
        headers = ["Name", "Email", "Status"]

        record = stream._transform_row(row, headers, row_number=2)

        assert record["name"] == "Alice"
        assert record["email"] is None  # Empty string -> None
        assert record["status"] == "active"


class TestReadStream:
    """Test read_stream method."""

    def test_read_stream_raises_for_unknown_stream(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture
    ):
        """Test that reading unknown stream raises error."""
        from src.utils import GoogleSheetsError

        with patch.object(GoogleSheetsClient, 'get_spreadsheet_metadata') as mock_metadata:
            mock_metadata.return_value = spreadsheet_metadata_fixture

            config = GoogleSheetsConfig(**valid_service_account_config)
            connector = GoogleSheetsConnector(config)

            with pytest.raises(GoogleSheetsError) as exc_info:
                list(connector.read_stream("NonExistentSheet"))

            assert "not found" in str(exc_info.value).lower()


class TestSync:
    """Test sync functionality."""

    def test_sync_returns_results(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture,
        sheet_values_fixture
    ):
        """Test that sync returns SyncResult objects."""
        with patch.object(GoogleSheetsClient, 'get_spreadsheet_metadata') as mock_metadata:
            mock_metadata.return_value = spreadsheet_metadata_fixture

            with patch.object(GoogleSheetsClient, 'get_headers') as mock_headers:
                mock_headers.return_value = sheet_values_fixture["values"][0]

                with patch.object(GoogleSheetsClient, 'get_row_count') as mock_row_count:
                    mock_row_count.return_value = 1000

                    with patch.object(GoogleSheetsClient, 'get_column_count') as mock_col_count:
                        mock_col_count.return_value = 26

                        with patch.object(GoogleSheetsClient, 'read_sheet_in_batches') as mock_batches:
                            mock_batches.return_value = iter([sheet_values_fixture["values"][1:]])

                            config = GoogleSheetsConfig(**valid_service_account_config)
                            connector = GoogleSheetsConnector(config)

                            results = connector.sync()

                            assert isinstance(results, list)
                            for result in results:
                                assert hasattr(result, 'stream_name')
                                assert hasattr(result, 'records_count')
                                assert hasattr(result, 'success')
