"""
Schema discovery tests for Google Sheets connector.

These tests verify that the connector can discover available streams
and their schemas using mocked Google API.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.config import GoogleSheetsConfig
from src.connector import GoogleSheetsConnector, Catalog, CatalogEntry
from src.streams import StreamSchema, SheetStream, SpreadsheetStreamFactory
from src.client import GoogleSheetsClient


class TestSchemaDiscovery:
    """Test schema discovery functionality."""

    def test_discover_returns_catalog(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture,
        sheet_values_fixture
    ):
        """Test that discover returns a Catalog object."""
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

                            catalog = connector.discover()

                            assert isinstance(catalog, Catalog)
                            assert len(catalog.streams) > 0

    def test_discover_finds_all_sheets(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture,
        sheet_values_fixture
    ):
        """Test that all sheets are discovered."""
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

                            catalog = connector.discover()

                            # Based on spreadsheet_metadata_fixture, we expect 3 sheets
                            expected_sheets = ["Sheet1", "Orders", "Customers"]
                            discovered_names = [entry.stream_name for entry in catalog.streams]

                            for expected in expected_sheets:
                                assert expected in discovered_names

    def test_catalog_entry_has_required_fields(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture,
        sheet_values_fixture
    ):
        """Test that CatalogEntry has all required fields."""
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

                            catalog = connector.discover()

                            for entry in catalog.streams:
                                assert isinstance(entry, CatalogEntry)
                                assert entry.stream_name is not None
                                assert entry.stream_schema is not None
                                assert entry.supported_sync_modes is not None
                                assert "full_refresh" in entry.supported_sync_modes


class TestStreamSchema:
    """Test StreamSchema class."""

    def test_stream_schema_from_headers(self):
        """Test creating schema from headers."""
        headers = ["ID", "Name", "Email", "Status"]
        schema = StreamSchema.from_headers(headers)

        assert schema.type == "object"
        assert len(schema.properties) > 0

        # Check headers are in properties (sanitized)
        assert "id" in schema.properties
        assert "name" in schema.properties
        assert "email" in schema.properties
        assert "status" in schema.properties

        # Check _row_number is added
        assert "_row_number" in schema.properties

    def test_stream_schema_from_headers_with_sample_data(self):
        """Test creating schema with sample data for type inference."""
        headers = ["ID", "Name", "Amount", "Active"]
        sample_data = [
            ["1", "John", "100.50", "true"],
            ["2", "Jane", "200.75", "false"],
        ]
        schema = StreamSchema.from_headers(headers, sample_data)

        assert "id" in schema.properties
        assert "amount" in schema.properties

    def test_stream_schema_to_dict(self):
        """Test schema to_dict conversion."""
        headers = ["Name", "Value"]
        schema = StreamSchema.from_headers(headers)
        schema_dict = schema.to_dict()

        assert "type" in schema_dict
        assert schema_dict["type"] == "object"
        assert "properties" in schema_dict
        assert "additionalProperties" in schema_dict


class TestSheetStream:
    """Test SheetStream class."""

    def test_sheet_stream_primary_key(self):
        """Test that SheetStream has _row_number as primary key."""
        mock_client = MagicMock()
        stream = SheetStream(
            name="TestSheet",
            client=mock_client,
            sheet_id=0,
            include_row_numbers=True
        )

        assert stream.primary_key == ["_row_number"]

    def test_sheet_stream_replication_method(self):
        """Test that SheetStream uses FULL_REFRESH."""
        mock_client = MagicMock()
        stream = SheetStream(
            name="TestSheet",
            client=mock_client,
            sheet_id=0
        )

        assert stream.replication_method == "FULL_REFRESH"


class TestCatalog:
    """Test Catalog class."""

    def test_catalog_get_stream(self):
        """Test Catalog.get_stream method."""
        entry1 = CatalogEntry(
            stream_name="Sheet1",
            stream_schema={"type": "object"},
            metadata={},
            supported_sync_modes=["full_refresh"]
        )
        entry2 = CatalogEntry(
            stream_name="Sheet2",
            stream_schema={"type": "object"},
            metadata={},
            supported_sync_modes=["full_refresh"]
        )

        catalog = Catalog(streams=[entry1, entry2])

        assert catalog.get_stream("Sheet1") == entry1
        assert catalog.get_stream("Sheet2") == entry2
        assert catalog.get_stream("NonExistent") is None

    def test_catalog_to_dict(self):
        """Test Catalog.to_dict method."""
        entry = CatalogEntry(
            stream_name="Sheet1",
            stream_schema={"type": "object"},
            metadata={"test": "value"},
            supported_sync_modes=["full_refresh"]
        )
        catalog = Catalog(streams=[entry])
        catalog_dict = catalog.to_dict()

        assert "streams" in catalog_dict
        assert len(catalog_dict["streams"]) == 1
        assert catalog_dict["streams"][0]["stream"]["name"] == "Sheet1"


class TestSpreadsheetStreamFactory:
    """Test SpreadsheetStreamFactory class."""

    def test_factory_discover_streams(self, spreadsheet_metadata_fixture):
        """Test that factory discovers streams correctly."""
        mock_client = MagicMock()
        mock_client.get_spreadsheet_metadata.return_value = spreadsheet_metadata_fixture

        factory = SpreadsheetStreamFactory(
            client=mock_client,
            sanitize_names=True,
            include_row_numbers=True
        )

        streams = factory.discover_streams()

        assert len(streams) == 3
        stream_names = [s.name for s in streams]
        assert "Sheet1" in stream_names
        assert "Orders" in stream_names
        assert "Customers" in stream_names

    def test_factory_get_stream(self, spreadsheet_metadata_fixture):
        """Test that factory can get a specific stream."""
        mock_client = MagicMock()
        mock_client.get_spreadsheet_metadata.return_value = spreadsheet_metadata_fixture

        factory = SpreadsheetStreamFactory(client=mock_client)

        stream = factory.get_stream("Sheet1")
        assert stream is not None
        assert stream.name == "Sheet1"

        # Non-existent stream returns None
        assert factory.get_stream("NonExistent") is None
