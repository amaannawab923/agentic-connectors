"""
Schema discovery tests for Google Sheets connector.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from streams import SyncMode, StreamSchema, StreamConfig, SheetStream, StreamCatalog
from utils import normalize_header, sanitize_sheet_name


class TestStreamSchema:
    """Test StreamSchema class."""

    def test_schema_from_headers(self):
        """Test creating schema from headers."""
        schema = StreamSchema.from_headers(
            stream_name="test_stream",
            headers=["Name", "Email", "Age"]
        )
        
        assert schema.name == "test_stream"
        assert "name" in schema.properties
        assert "email" in schema.properties
        assert "age" in schema.properties

    def test_schema_to_dict(self):
        """Test schema to dictionary conversion."""
        schema = StreamSchema.from_headers(
            stream_name="test_stream",
            headers=["Name", "Email"]
        )
        
        dict_schema = schema.to_dict()
        assert dict_schema["type"] == "object"
        assert "properties" in dict_schema

    def test_schema_with_primary_key(self):
        """Test schema with primary key."""
        schema = StreamSchema.from_headers(
            stream_name="test_stream",
            headers=["id", "Name"],
            primary_key=["id"]
        )
        
        assert schema.primary_key == ["id"]

    def test_schema_property_types(self):
        """Test that schema properties have correct types."""
        schema = StreamSchema.from_headers(
            stream_name="test_stream",
            headers=["Column1"]
        )
        
        # All columns should be string|null since Sheets doesn't provide types
        assert schema.properties["column1"]["type"] == ["string", "null"]


class TestSheetStream:
    """Test SheetStream class."""

    def test_stream_name_sanitization(self):
        """Test stream name is sanitized."""
        mock_client = MagicMock()
        mock_client.get_headers.return_value = ["Col1", "Col2"]
        
        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="My Sheet 2024"
        )
        
        assert stream.name == "my_sheet_2024"
        assert stream.raw_name == "My Sheet 2024"

    def test_stream_headers(self):
        """Test getting stream headers."""
        mock_client = MagicMock()
        mock_client.get_headers.return_value = ["Name", "Email", "Age"]
        
        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1"
        )
        
        headers = stream.headers
        assert headers == ["Name", "Email", "Age"]

    def test_stream_normalized_headers(self):
        """Test normalized headers."""
        mock_client = MagicMock()
        mock_client.get_headers.return_value = ["First Name", "Email Address", "DOB"]
        
        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1"
        )
        
        normalized = stream.normalized_headers
        assert "first_name" in normalized
        assert "email_address" in normalized
        assert "dob" in normalized

    def test_stream_schema_generation(self):
        """Test schema generation from headers."""
        mock_client = MagicMock()
        mock_client.get_headers.return_value = ["Name", "Email"]
        
        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1"
        )
        
        schema = stream.schema
        assert "name" in schema.properties
        assert "email" in schema.properties

    def test_stream_schema_with_row_number(self):
        """Test schema includes row number when configured."""
        mock_client = MagicMock()
        mock_client.get_headers.return_value = ["Name"]
        
        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1",
            include_row_number=True
        )
        
        schema = stream.schema
        assert "_row_number" in schema.properties
        assert schema.properties["_row_number"]["type"] == "integer"

    def test_stream_json_schema(self):
        """Test get_json_schema output format."""
        mock_client = MagicMock()
        mock_client.get_headers.return_value = ["Col1"]
        
        stream = SheetStream(
            client=mock_client,
            spreadsheet_id="test-id",
            sheet_name="Sheet1"
        )
        
        json_schema = stream.get_json_schema()
        assert "name" in json_schema
        assert "json_schema" in json_schema
        assert "supported_sync_modes" in json_schema
        assert SyncMode.FULL_REFRESH.value in json_schema["supported_sync_modes"]


class TestStreamCatalog:
    """Test StreamCatalog class."""

    def test_catalog_discovers_streams(self, mock_spreadsheet_metadata):
        """Test catalog discovers all sheets as streams."""
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1", "Data & Analysis"]
        mock_client.get_headers.return_value = ["Col1", "Col2"]
        
        catalog = StreamCatalog(
            client=mock_client,
            spreadsheet_id="test-id"
        )
        
        streams = catalog.streams
        assert "Sheet1" in streams
        assert "Data & Analysis" in streams

    def test_catalog_get_stream(self, mock_spreadsheet_metadata):
        """Test getting a specific stream from catalog."""
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1"]
        mock_client.get_headers.return_value = ["Col1"]
        
        catalog = StreamCatalog(
            client=mock_client,
            spreadsheet_id="test-id"
        )
        
        stream = catalog.get_stream("Sheet1")
        assert stream is not None
        assert stream.raw_name == "Sheet1"

    def test_catalog_get_nonexistent_stream(self):
        """Test getting a nonexistent stream returns None."""
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1"]
        
        catalog = StreamCatalog(
            client=mock_client,
            spreadsheet_id="test-id"
        )
        
        stream = catalog.get_stream("NonExistent")
        assert stream is None

    def test_catalog_get_stream_names(self):
        """Test getting list of stream names."""
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1", "Sheet2", "Sheet3"]
        
        catalog = StreamCatalog(
            client=mock_client,
            spreadsheet_id="test-id"
        )
        
        names = catalog.get_stream_names()
        assert len(names) == 3
        assert "Sheet1" in names

    def test_catalog_get_catalog_format(self):
        """Test get_catalog returns correct format."""
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1"]
        mock_client.get_headers.return_value = ["Col1"]
        
        catalog = StreamCatalog(
            client=mock_client,
            spreadsheet_id="test-id"
        )
        
        catalog_data = catalog.get_catalog()
        assert "streams" in catalog_data
        assert isinstance(catalog_data["streams"], list)
        assert len(catalog_data["streams"]) == 1

    def test_catalog_select_streams_include(self):
        """Test selecting streams by inclusion list."""
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1", "Sheet2", "Sheet3"]
        mock_client.get_headers.return_value = ["Col1"]
        
        catalog = StreamCatalog(
            client=mock_client,
            spreadsheet_id="test-id"
        )
        
        selected = catalog.select_streams(sheet_names=["Sheet1", "Sheet3"])
        assert len(selected) == 2

    def test_catalog_select_streams_exclude(self):
        """Test selecting streams by exclusion list."""
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1", "Sheet2", "Sheet3"]
        mock_client.get_headers.return_value = ["Col1"]
        
        catalog = StreamCatalog(
            client=mock_client,
            spreadsheet_id="test-id"
        )
        
        selected = catalog.select_streams(exclude_sheets=["Sheet2"])
        assert len(selected) == 2
        for s in selected:
            assert s.raw_name != "Sheet2"


class TestConnectorDiscovery:
    """Test connector discover() operation."""

    @patch('connector.GoogleSheetsClient')
    @patch('connector.create_authenticator')
    def test_discover_returns_catalog(self, mock_create_auth, mock_client_class,
                                       valid_service_account_config):
        """Test discover returns proper catalog structure."""
        mock_auth = MagicMock()
        mock_create_auth.return_value = mock_auth
        
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1", "Sheet2"]
        mock_client.get_headers.return_value = ["Name", "Email"]
        mock_client_class.return_value = mock_client
        
        from connector import GoogleSheetsConnector
        connector = GoogleSheetsConnector(valid_service_account_config)
        catalog = connector.discover()
        
        assert "streams" in catalog
        assert len(catalog["streams"]) == 2

    @patch('connector.GoogleSheetsClient')
    @patch('connector.create_authenticator')
    def test_discover_stream_schemas(self, mock_create_auth, mock_client_class,
                                      valid_service_account_config):
        """Test discovered streams have proper schemas."""
        mock_auth = MagicMock()
        mock_create_auth.return_value = mock_auth
        
        mock_client = MagicMock()
        mock_client.get_sheet_names.return_value = ["Sheet1"]
        mock_client.get_headers.return_value = ["ID", "Name", "Value"]
        mock_client_class.return_value = mock_client
        
        from connector import GoogleSheetsConnector
        connector = GoogleSheetsConnector(valid_service_account_config)
        catalog = connector.discover()
        
        stream = catalog["streams"][0]
        assert "json_schema" in stream
        assert "properties" in stream["json_schema"]
        assert "id" in stream["json_schema"]["properties"]
        assert "name" in stream["json_schema"]["properties"]
        assert "value" in stream["json_schema"]["properties"]


class TestHeaderNormalization:
    """Test header normalization utilities."""

    def test_normalize_header_simple(self):
        """Test simple header normalization."""
        assert normalize_header("Name") == "name"
        assert normalize_header("Email") == "email"

    def test_normalize_header_with_spaces(self):
        """Test normalizing headers with spaces."""
        assert normalize_header("First Name") == "first_name"
        assert normalize_header("  Padded  ") == "padded"

    def test_normalize_header_special_chars(self):
        """Test normalizing headers with special characters."""
        assert normalize_header("Data/Value") == "data_value"
        assert normalize_header("Data-Value") == "data_value"
        assert normalize_header("Data.Value") == "data_value"

    def test_normalize_header_empty(self):
        """Test normalizing empty header."""
        assert normalize_header("") == "unnamed_column"
        assert normalize_header("   ") == "unnamed_column"

    def test_normalize_header_numeric_start(self):
        """Test normalizing headers starting with numbers."""
        assert normalize_header("123abc") == "col_123abc"

    def test_sanitize_sheet_name(self):
        """Test sheet name sanitization."""
        assert sanitize_sheet_name("My Sheet") == "my_sheet"
        assert sanitize_sheet_name("Data & Analysis") == "data_analysis"
        assert sanitize_sheet_name("2024 Data") == "sheet_2024_data"
