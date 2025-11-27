"""
Schema discovery tests for the Notion connector.

These tests verify that the connector properly discovers available streams
and their schemas.
"""

import pytest
import responses
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.connector import NotionSourceConnector, Catalog, StreamSchema
from src.config import NotionConfig


class TestStreamSchema:
    """Test StreamSchema class."""

    def test_stream_schema_creation(self):
        """Test creating a stream schema."""
        schema = StreamSchema(
            name="users",
            json_schema={"type": "object", "properties": {}},
            supported_sync_modes=["full_refresh"],
            source_defined_cursor=False,
            default_cursor_field=None,
            source_defined_primary_key=[["id"]]
        )
        assert schema.name == "users"
        assert schema.supported_sync_modes == ["full_refresh"]
        assert schema.source_defined_primary_key == [["id"]]

    def test_stream_schema_to_dict(self):
        """Test StreamSchema to_dict method."""
        schema = StreamSchema(
            name="pages",
            json_schema={"type": "object"},
            supported_sync_modes=["full_refresh", "incremental"],
            source_defined_cursor=True,
            default_cursor_field=["last_edited_time"],
            source_defined_primary_key=[["id"]]
        )
        result = schema.to_dict()

        assert result["name"] == "pages"
        assert result["json_schema"] == {"type": "object"}
        assert "incremental" in result["supported_sync_modes"]
        assert result["source_defined_cursor"] is True
        assert result["default_cursor_field"] == ["last_edited_time"]


class TestCatalog:
    """Test Catalog class."""

    def test_catalog_creation(self):
        """Test creating a catalog."""
        streams = [
            StreamSchema(
                name="users",
                json_schema={"type": "object"},
                supported_sync_modes=["full_refresh"]
            ),
            StreamSchema(
                name="pages",
                json_schema={"type": "object"},
                supported_sync_modes=["full_refresh", "incremental"]
            )
        ]
        catalog = Catalog(streams=streams)
        assert len(catalog.streams) == 2

    def test_catalog_to_dict(self):
        """Test Catalog to_dict method."""
        streams = [
            StreamSchema(
                name="users",
                json_schema={"type": "object"},
                supported_sync_modes=["full_refresh"]
            )
        ]
        catalog = Catalog(streams=streams)
        result = catalog.to_dict()

        assert "streams" in result
        assert len(result["streams"]) == 1
        assert result["streams"][0]["name"] == "users"


class TestDiscovery:
    """Test schema discovery functionality."""

    @responses.activate
    def test_discover_returns_catalog(self, valid_token_config, mock_bot_user_response):
        """Test that discover returns a Catalog object."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()

        assert isinstance(catalog, Catalog)
        assert hasattr(catalog, "streams")
        assert len(catalog.streams) > 0

    @responses.activate
    def test_discover_has_users_stream(self, valid_token_config, mock_bot_user_response):
        """Test that discover includes users stream."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        stream_names = [s.name for s in catalog.streams]

        assert "users" in stream_names

    @responses.activate
    def test_discover_has_databases_stream(self, valid_token_config, mock_bot_user_response):
        """Test that discover includes databases stream."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        stream_names = [s.name for s in catalog.streams]

        assert "databases" in stream_names

    @responses.activate
    def test_discover_has_pages_stream(self, valid_token_config, mock_bot_user_response):
        """Test that discover includes pages stream."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        stream_names = [s.name for s in catalog.streams]

        assert "pages" in stream_names

    @responses.activate
    def test_discover_has_blocks_stream(self, valid_token_config, mock_bot_user_response):
        """Test that discover includes blocks stream when fetch_page_blocks is True."""
        config_dict = valid_token_config.copy()
        config_dict["fetch_page_blocks"] = True

        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**config_dict)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        stream_names = [s.name for s in catalog.streams]

        assert "blocks" in stream_names

    @responses.activate
    def test_discover_excludes_blocks_when_disabled(self, valid_token_config, mock_bot_user_response):
        """Test that blocks stream is excluded when fetch_page_blocks is False."""
        config_dict = valid_token_config.copy()
        config_dict["fetch_page_blocks"] = False

        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**config_dict)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        stream_names = [s.name for s in catalog.streams]

        assert "blocks" not in stream_names

    @responses.activate
    def test_discover_has_comments_stream(self, valid_token_config, mock_bot_user_response):
        """Test that discover includes comments stream."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        stream_names = [s.name for s in catalog.streams]

        assert "comments" in stream_names

    @responses.activate
    def test_users_stream_is_full_refresh_only(self, valid_token_config, mock_bot_user_response):
        """Test that users stream supports only full_refresh."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        users_stream = next((s for s in catalog.streams if s.name == "users"), None)

        assert users_stream is not None
        assert "full_refresh" in users_stream.supported_sync_modes
        assert "incremental" not in users_stream.supported_sync_modes
        assert users_stream.source_defined_cursor is False

    @responses.activate
    def test_pages_stream_supports_incremental(self, valid_token_config, mock_bot_user_response):
        """Test that pages stream supports incremental sync."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        pages_stream = next((s for s in catalog.streams if s.name == "pages"), None)

        assert pages_stream is not None
        assert "incremental" in pages_stream.supported_sync_modes
        assert pages_stream.source_defined_cursor is True
        assert pages_stream.default_cursor_field == ["last_edited_time"]

    @responses.activate
    def test_databases_stream_supports_incremental(self, valid_token_config, mock_bot_user_response):
        """Test that databases stream supports incremental sync."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()
        db_stream = next((s for s in catalog.streams if s.name == "databases"), None)

        assert db_stream is not None
        assert "incremental" in db_stream.supported_sync_modes

    @responses.activate
    def test_all_streams_have_primary_key(self, valid_token_config, mock_bot_user_response):
        """Test that all streams have a primary key defined."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()

        for stream in catalog.streams:
            assert stream.source_defined_primary_key is not None
            assert stream.source_defined_primary_key == [["id"]]

    @responses.activate
    def test_stream_schemas_have_required_fields(self, valid_token_config, mock_bot_user_response):
        """Test that all stream schemas have required fields."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        catalog = connector.discover()

        for stream in catalog.streams:
            schema = stream.json_schema
            assert "$schema" in schema
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            # All streams should have 'id' and 'object' properties
            assert "id" in schema["properties"]
            assert "object" in schema["properties"]
