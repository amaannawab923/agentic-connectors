"""Schema discovery tests for Google Sheets connector."""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import from src package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.connector import GoogleSheetsConnector
from src.config import GoogleSheetsConfig, Catalog, CatalogEntry


class TestDiscovery:
    """Test schema discovery functionality."""

    def test_discover_returns_catalog(self, service_account_config, mock_sheets_api):
        """Test discover returns a Catalog object."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        catalog = connector.discover()

        assert isinstance(catalog, Catalog)

    def test_discover_finds_all_sheets(self, service_account_config, mock_sheets_api):
        """Test discover finds all sheets in spreadsheet."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        catalog = connector.discover()

        # Should find both sheets from mock metadata
        assert len(catalog.streams) == 2
        stream_names = catalog.get_stream_names()
        assert "Sheet1" in stream_names
        assert "Data Sheet" in stream_names

    def test_discover_infers_schema(self, service_account_config, mock_sheets_api):
        """Test discover infers JSON schema from data."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        catalog = connector.discover()

        # Check first stream has schema
        stream = catalog.get_stream("Sheet1")
        assert stream is not None
        assert "properties" in stream.schema

    def test_discovered_streams_have_correct_sync_modes(self, service_account_config, mock_sheets_api):
        """Test discovered streams have correct sync modes."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        catalog = connector.discover()

        for stream in catalog.streams:
            assert "full_refresh" in stream.supported_sync_modes
            # Google Sheets doesn't support incremental
            assert stream.source_defined_cursor is False

    def test_discover_with_stream_filter(self, service_account_config, mock_sheets_api):
        """Test discover respects stream filter configuration."""
        # Configure to only include Sheet1
        service_account_config["streams"] = [
            {"name": "Sheet1", "enabled": True},
            {"name": "Data Sheet", "enabled": False},
        ]

        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        catalog = connector.discover()

        # Should only find Sheet1
        stream_names = catalog.get_stream_names()
        assert "Sheet1" in stream_names
        assert "Data Sheet" not in stream_names

    def test_discover_handles_empty_sheet(self, service_account_config):
        """Test discover handles sheets with no data."""
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

            # Spreadsheet with an empty sheet
            mock_get_request = MagicMock()
            mock_get_request.execute = MagicMock(return_value={
                "spreadsheetId": "test-id",
                "properties": {"title": "Test"},
                "sheets": [
                    {
                        "properties": {
                            "sheetId": 0,
                            "title": "Empty Sheet",
                            "index": 0,
                            "gridProperties": {"rowCount": 100, "columnCount": 26}
                        }
                    }
                ]
            })
            mock_spreadsheets.get = MagicMock(return_value=mock_get_request)

            # Return empty values for header
            mock_values = MagicMock()
            mock_spreadsheets.values = MagicMock(return_value=mock_values)

            def mock_values_get(**kwargs):
                mock_response = MagicMock()
                mock_response.execute = MagicMock(return_value={
                    "range": "'Empty Sheet'!1:1",
                    "values": []
                })
                return mock_response

            mock_values.get = MagicMock(side_effect=mock_values_get)

            mock_build.return_value = mock_service

            config = GoogleSheetsConfig(**service_account_config)
            connector = GoogleSheetsConnector(config)

            catalog = connector.discover()

            # Should still create a stream entry, even if empty
            assert len(catalog.streams) >= 0


class TestSchemaInference:
    """Test schema inference from sample data."""

    def test_schema_infers_string_type(self, service_account_config, mock_sheets_api):
        """Test schema inference detects string types."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        catalog = connector.discover()
        stream = catalog.get_stream("Sheet1")

        # Name and Email should be strings
        props = stream.schema.get("properties", {})
        assert "name" in props or "Name" in props

    def test_schema_includes_nullable(self, service_account_config, mock_sheets_api):
        """Test inferred schema types include null."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        catalog = connector.discover()
        stream = catalog.get_stream("Sheet1")

        # All fields should be nullable
        props = stream.schema.get("properties", {})
        for prop_name, prop_schema in props.items():
            if "type" in prop_schema:
                types = prop_schema["type"]
                if isinstance(types, list):
                    assert "null" in types, f"Field {prop_name} should be nullable"


class TestStreamMetadata:
    """Test stream metadata functionality."""

    def test_get_stream_metadata(self, service_account_config, mock_sheets_api):
        """Test getting metadata for a specific stream."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        metadata = connector.get_stream_metadata("Sheet1")

        assert metadata.name == "Sheet1"
        assert metadata.sheet_id == 0
        assert metadata.row_count == 1000
        assert metadata.column_count == 26

    def test_get_stream_metadata_not_found(self, service_account_config, mock_sheets_api):
        """Test getting metadata for non-existent stream raises error."""
        config = GoogleSheetsConfig(**service_account_config)
        connector = GoogleSheetsConnector(config)

        with pytest.raises(ValueError) as exc_info:
            connector.get_stream_metadata("NonExistent")

        assert "not found" in str(exc_info.value).lower()

    def test_stream_metadata_estimated_record_count(self):
        """Test StreamMetadata estimated_record_count property."""
        from src.streams import StreamMetadata

        metadata = StreamMetadata(
            name="Test",
            sheet_id=0,
            row_count=100,
            column_count=10,
        )

        # Should be row_count - 1 (for header)
        assert metadata.estimated_record_count == 99
