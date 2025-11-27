"""
Data reading tests for the Notion connector.

These tests verify that the connector can properly read data from
the Notion API.
"""

import pytest
import responses
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.connector import NotionSourceConnector, Record, StateMessage
from src.config import NotionConfig
from src.streams import (
    UsersStream,
    DatabasesStream,
    PagesStream,
    BlocksStream,
    CommentsStream,
)
from src.client import NotionClient


class TestRecordClass:
    """Test Record class."""

    def test_record_creation(self):
        """Test creating a record."""
        record = Record(
            stream="users",
            data={"id": "test-id", "name": "Test User"},
            emitted_at=1704067200000
        )
        assert record.stream == "users"
        assert record.data["id"] == "test-id"
        assert record.emitted_at == 1704067200000

    def test_record_to_dict(self):
        """Test Record to_dict method."""
        record = Record(
            stream="users",
            data={"id": "test-id"},
            emitted_at=1704067200000
        )
        result = record.to_dict()

        assert result["type"] == "RECORD"
        assert result["record"]["stream"] == "users"
        assert result["record"]["data"]["id"] == "test-id"
        assert result["record"]["emitted_at"] == 1704067200000


class TestStateMessage:
    """Test StateMessage class."""

    def test_state_message_creation(self):
        """Test creating a state message."""
        state = StateMessage(data={"streams": {"users": {"cursor_value": "123"}}})
        assert state.data["streams"]["users"]["cursor_value"] == "123"

    def test_state_message_to_dict(self):
        """Test StateMessage to_dict method."""
        state = StateMessage(data={"streams": {}})
        result = state.to_dict()

        assert result["type"] == "STATE"
        assert "state" in result
        assert "data" in result["state"]


class TestReadUsers:
    """Test reading users stream."""

    @responses.activate
    def test_read_users_returns_records(self, valid_token_config, mock_users_list_response):
        """Test that read_users returns user records."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=mock_users_list_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        users = list(connector.read_users())

        assert len(users) == 2
        # First user is a person
        assert users[0]["type"] == "person"
        assert users[0]["name"] == "John Doe"
        assert users[0]["is_bot"] is False
        # Second user is a bot
        assert users[1]["type"] == "bot"
        assert users[1]["is_bot"] is True

    @responses.activate
    def test_read_users_extracts_person_email(self, valid_token_config, mock_users_list_response):
        """Test that user email is extracted for person type."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=mock_users_list_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        users = list(connector.read_users())
        person_user = users[0]

        assert person_user["email"] == "john.doe@example.com"

    @responses.activate
    def test_read_users_extracts_bot_workspace(self, valid_token_config, mock_users_list_response):
        """Test that workspace name is extracted for bot type."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=mock_users_list_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        users = list(connector.read_users())
        bot_user = users[1]

        assert bot_user["bot_workspace_name"] == "Test Workspace"
        assert bot_user["bot_owner_type"] == "workspace"


class TestReadDatabases:
    """Test reading databases stream."""

    @responses.activate
    def test_read_databases_returns_records(self, valid_token_config, mock_search_databases_response):
        """Test that read_databases returns database records."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_databases_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        databases = list(connector.read_databases())

        assert len(databases) == 1
        assert databases[0]["object"] == "database"
        assert databases[0]["title"] == "Test Database"

    @responses.activate
    def test_read_databases_extracts_properties(self, valid_token_config, mock_search_databases_response):
        """Test that database properties are extracted."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_databases_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        databases = list(connector.read_databases())
        db = databases[0]

        assert "properties" in db
        assert "property_names" in db
        assert "Name" in db["property_names"]
        assert "Status" in db["property_names"]

    @responses.activate
    def test_read_databases_extracts_icon(self, valid_token_config, mock_search_databases_response):
        """Test that database icon is extracted."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_databases_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        databases = list(connector.read_databases())
        db = databases[0]

        assert db["icon_type"] == "emoji"
        assert db["icon_value"] == "📚"


class TestReadPages:
    """Test reading pages stream."""

    @responses.activate
    def test_read_pages_returns_records(self, valid_token_config, mock_search_pages_response):
        """Test that read_pages returns page records."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        pages = list(connector.read_pages())

        assert len(pages) == 1
        assert pages[0]["object"] == "page"
        assert pages[0]["title"] == "Test Page"

    @responses.activate
    def test_read_pages_extracts_parent_info(self, valid_token_config, mock_search_pages_response):
        """Test that page parent info is extracted."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        pages = list(connector.read_pages())
        page = pages[0]

        assert page["parent_type"] == "workspace"
        assert page["parent_id"] == "workspace"

    @responses.activate
    def test_read_pages_flattens_properties(self, valid_token_config, mock_search_pages_response):
        """Test that page properties are flattened."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        pages = list(connector.read_pages())
        page = pages[0]

        # Should have both raw and flattened properties
        assert "properties" in page
        assert "properties_flat" in page


class TestReadBlocks:
    """Test reading blocks stream."""

    @responses.activate
    def test_read_blocks_returns_records(self, valid_token_config, mock_search_pages_response, mock_block_children_response):
        """Test that read_blocks returns block records."""
        # First mock search for pages
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )
        # Then mock block children
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page-id-12345678-1234-1234-1234-123456789abc/children",
            json=mock_block_children_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        blocks = list(connector.read_blocks())

        assert len(blocks) == 2
        assert blocks[0]["type"] == "paragraph"
        assert blocks[1]["type"] == "heading_1"

    @responses.activate
    def test_read_blocks_extracts_content(self, valid_token_config, mock_search_pages_response, mock_block_children_response):
        """Test that block content is extracted."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page-id-12345678-1234-1234-1234-123456789abc/children",
            json=mock_block_children_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        blocks = list(connector.read_blocks())
        paragraph_block = blocks[0]

        assert paragraph_block["content"] == "This is a test paragraph."

    @responses.activate
    def test_read_blocks_with_specific_pages(self, valid_token_config, mock_block_children_response):
        """Test reading blocks from specific pages."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/specific-page-id/children",
            json=mock_block_children_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        blocks = list(connector.read_blocks(page_ids=["specific-page-id"]))

        assert len(blocks) == 2


class TestReadComments:
    """Test reading comments stream."""

    @responses.activate
    def test_read_comments_returns_records(self, valid_token_config, mock_search_pages_response, mock_comments_response):
        """Test that read_comments returns comment records."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/comments",
            json=mock_comments_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        comments = list(connector.read_comments())

        assert len(comments) == 1
        assert comments[0]["object"] == "comment"

    @responses.activate
    def test_read_comments_extracts_content(self, valid_token_config, mock_search_pages_response, mock_comments_response):
        """Test that comment content is extracted."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/comments",
            json=mock_comments_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        comments = list(connector.read_comments())
        comment = comments[0]

        assert comment["content"] == "This is a test comment."
        assert comment["discussion_id"] == "discussion-id-123"


class TestRead:
    """Test the main read method."""

    @responses.activate
    def test_read_all_streams(self, valid_token_config, mock_users_list_response,
                              mock_search_databases_response, mock_search_pages_response,
                              mock_block_children_response, mock_comments_response):
        """Test reading all streams."""
        # Mock users
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=mock_users_list_response,
            status=200
        )
        # Mock databases search
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_databases_response,
            status=200
        )
        # Mock pages search
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )
        # Mock blocks
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page-id-12345678-1234-1234-1234-123456789abc/children",
            json=mock_block_children_response,
            status=200
        )
        # Mock pages search for blocks
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )
        # Mock pages search for comments
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )
        # Mock comments
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/comments",
            json=mock_comments_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        messages = list(connector.read())

        # Should have records and at least one state message
        record_messages = [m for m in messages if m.get("type") == "RECORD"]
        state_messages = [m for m in messages if m.get("type") == "STATE"]

        assert len(record_messages) > 0
        assert len(state_messages) >= 1  # Final state message

    @responses.activate
    def test_read_specific_streams(self, valid_token_config, mock_users_list_response):
        """Test reading specific streams only."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=mock_users_list_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        messages = list(connector.read(stream_names=["users"]))

        record_messages = [m for m in messages if m.get("type") == "RECORD"]

        # Should only have user records
        for msg in record_messages:
            assert msg["record"]["stream"] == "users"

    @responses.activate
    def test_read_emits_state_checkpoints(self, valid_token_config):
        """Test that read emits state checkpoints periodically."""
        # Create a response with many users to trigger state checkpoints
        many_users = {
            "object": "list",
            "results": [
                {
                    "object": "user",
                    "id": f"user-{i}",
                    "type": "person",
                    "name": f"User {i}",
                    "avatar_url": None,
                    "person": {"email": f"user{i}@example.com"}
                }
                for i in range(150)  # 150 users to trigger checkpoints
            ],
            "next_cursor": None,
            "has_more": False
        }

        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=many_users,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        messages = list(connector.read(stream_names=["users"]))
        state_messages = [m for m in messages if m.get("type") == "STATE"]

        # Should have at least 2 state messages (one per 100 records + final)
        assert len(state_messages) >= 2


class TestPagination:
    """Test pagination handling."""

    @responses.activate
    def test_pagination_follows_next_cursor(self, valid_token_config):
        """Test that pagination follows next_cursor."""
        # First page
        first_page = {
            "object": "list",
            "results": [
                {"object": "user", "id": "user-1", "type": "person", "name": "User 1", "person": {}}
            ],
            "next_cursor": "cursor-123",
            "has_more": True
        }
        # Second page
        second_page = {
            "object": "list",
            "results": [
                {"object": "user", "id": "user-2", "type": "person", "name": "User 2", "person": {}}
            ],
            "next_cursor": None,
            "has_more": False
        }

        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=first_page,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=second_page,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        users = list(connector.read_users())

        assert len(users) == 2
        assert users[0]["id"] == "user-1"
        assert users[1]["id"] == "user-2"


class TestIncrementalSync:
    """Test incremental sync functionality."""

    @responses.activate
    def test_read_with_state(self, valid_token_config, mock_search_pages_response):
        """Test that read respects state for incremental sync."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )

        config = NotionConfig(**valid_token_config)
        connector = NotionSourceConnector(config)

        # Set initial state
        state = {
            "streams": {
                "pages": {
                    "cursor_value": "2024-01-01T00:00:00.000Z",
                    "last_sync_time": None,
                    "records_synced": 50
                }
            }
        }

        messages = list(connector.read(stream_names=["pages"], state=state))

        # Should complete without error
        assert len(messages) > 0
