"""
Shared pytest fixtures for Notion connector tests.

This module provides mock fixtures for testing the Notion connector
without making actual API calls.
"""

import pytest
import responses
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import NotionConfig, InternalTokenCredentials, OAuth2Credentials
from src.connector import NotionSourceConnector


# =============================================================================
# API Response Fixtures
# =============================================================================


@pytest.fixture
def mock_bot_user_response():
    """Mock response for the /users/me endpoint (bot user).

    NOTE: The Notion API returns 'workspace': True (boolean) for workspace-owned bots.
    This is the actual API response structure, and it exposes a BUG in client.py:674
    where the code tries to call .get("icon") on a boolean value.
    """
    return {
        "object": "user",
        "id": "bot-user-id-12345678-1234-1234-1234-123456789abc",
        "type": "bot",
        "name": "Test Integration Bot",
        "avatar_url": None,
        "bot": {
            "owner": {
                "type": "workspace",
                "workspace": True  # This is a boolean, not an object - exposes BUG in client.py:674
            },
            "workspace_name": "Test Workspace"
        }
    }


@pytest.fixture
def mock_users_list_response():
    """Mock response for the /users endpoint."""
    return {
        "object": "list",
        "results": [
            {
                "object": "user",
                "id": "user-id-12345678-1234-1234-1234-123456789abc",
                "type": "person",
                "name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "person": {
                    "email": "john.doe@example.com"
                }
            },
            {
                "object": "user",
                "id": "bot-user-id-12345678-1234-1234-1234-123456789abc",
                "type": "bot",
                "name": "Test Integration Bot",
                "avatar_url": None,
                "bot": {
                    "owner": {
                        "type": "workspace",
                        "workspace": True
                    },
                    "workspace_name": "Test Workspace"
                }
            }
        ],
        "next_cursor": None,
        "has_more": False
    }


@pytest.fixture
def mock_search_databases_response():
    """Mock response for searching databases."""
    return {
        "object": "list",
        "results": [
            {
                "object": "database",
                "id": "db-id-12345678-1234-1234-1234-123456789abc",
                "created_time": "2024-01-01T10:00:00.000Z",
                "last_edited_time": "2024-01-15T14:30:00.000Z",
                "created_by": {"object": "user", "id": "user-id-123"},
                "last_edited_by": {"object": "user", "id": "user-id-123"},
                "title": [{"type": "text", "text": {"content": "Test Database"}, "plain_text": "Test Database"}],
                "description": [{"type": "text", "text": {"content": "A test database"}, "plain_text": "A test database"}],
                "icon": {"type": "emoji", "emoji": "📚"},
                "cover": None,
                "url": "https://www.notion.so/test-database-123",
                "public_url": None,
                "is_inline": False,
                "archived": False,
                "properties": {
                    "Name": {"id": "title", "type": "title", "name": "Name", "title": {}},
                    "Status": {"id": "status", "type": "status", "name": "Status", "status": {}},
                    "Due Date": {"id": "date", "type": "date", "name": "Due Date", "date": {}}
                }
            }
        ],
        "next_cursor": None,
        "has_more": False
    }


@pytest.fixture
def mock_search_pages_response():
    """Mock response for searching pages."""
    return {
        "object": "list",
        "results": [
            {
                "object": "page",
                "id": "page-id-12345678-1234-1234-1234-123456789abc",
                "created_time": "2024-01-05T09:00:00.000Z",
                "last_edited_time": "2024-01-20T16:45:00.000Z",
                "created_by": {"object": "user", "id": "user-id-123"},
                "last_edited_by": {"object": "user", "id": "user-id-123"},
                "parent": {"type": "workspace", "workspace": True},
                "icon": {"type": "emoji", "emoji": "📄"},
                "cover": None,
                "url": "https://www.notion.so/Test-Page-123",
                "public_url": None,
                "archived": False,
                "in_trash": False,
                "properties": {
                    "title": {
                        "id": "title",
                        "type": "title",
                        "title": [{"type": "text", "text": {"content": "Test Page"}, "plain_text": "Test Page"}]
                    }
                }
            }
        ],
        "next_cursor": None,
        "has_more": False
    }


@pytest.fixture
def mock_block_children_response():
    """Mock response for getting block children."""
    return {
        "object": "list",
        "results": [
            {
                "object": "block",
                "id": "block-id-12345678-1234-1234-1234-123456789abc",
                "parent": {"type": "page_id", "page_id": "page-id-123"},
                "type": "paragraph",
                "created_time": "2024-01-05T09:00:00.000Z",
                "last_edited_time": "2024-01-10T12:00:00.000Z",
                "created_by": {"object": "user", "id": "user-id-123"},
                "last_edited_by": {"object": "user", "id": "user-id-123"},
                "has_children": False,
                "archived": False,
                "in_trash": False,
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "This is a test paragraph."}, "plain_text": "This is a test paragraph."}
                    ],
                    "color": "default"
                }
            },
            {
                "object": "block",
                "id": "block-id-22345678-1234-1234-1234-123456789abc",
                "parent": {"type": "page_id", "page_id": "page-id-123"},
                "type": "heading_1",
                "created_time": "2024-01-05T09:01:00.000Z",
                "last_edited_time": "2024-01-10T12:00:00.000Z",
                "created_by": {"object": "user", "id": "user-id-123"},
                "last_edited_by": {"object": "user", "id": "user-id-123"},
                "has_children": False,
                "archived": False,
                "in_trash": False,
                "heading_1": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Test Heading"}, "plain_text": "Test Heading"}
                    ],
                    "is_toggleable": False,
                    "color": "default"
                }
            }
        ],
        "next_cursor": None,
        "has_more": False
    }


@pytest.fixture
def mock_comments_response():
    """Mock response for getting comments."""
    return {
        "object": "list",
        "results": [
            {
                "object": "comment",
                "id": "comment-id-12345678-1234-1234-1234-123456789abc",
                "discussion_id": "discussion-id-123",
                "created_time": "2024-01-15T10:00:00.000Z",
                "last_edited_time": "2024-01-15T10:00:00.000Z",
                "created_by": {"object": "user", "id": "user-id-123"},
                "parent": {"type": "page_id", "page_id": "page-id-123"},
                "rich_text": [
                    {"type": "text", "text": {"content": "This is a test comment."}, "plain_text": "This is a test comment."}
                ]
            }
        ],
        "next_cursor": None,
        "has_more": False
    }


@pytest.fixture
def mock_database_query_response():
    """Mock response for database query."""
    return {
        "object": "list",
        "results": [
            {
                "object": "page",
                "id": "db-page-id-12345678-1234-1234-1234-123456789abc",
                "created_time": "2024-01-10T11:00:00.000Z",
                "last_edited_time": "2024-01-18T09:30:00.000Z",
                "created_by": {"object": "user", "id": "user-id-123"},
                "last_edited_by": {"object": "user", "id": "user-id-123"},
                "parent": {"type": "database_id", "database_id": "db-id-123"},
                "icon": None,
                "cover": None,
                "url": "https://www.notion.so/Database-Page-123",
                "public_url": None,
                "archived": False,
                "in_trash": False,
                "properties": {
                    "Name": {
                        "id": "title",
                        "type": "title",
                        "title": [{"type": "text", "text": {"content": "Database Item"}, "plain_text": "Database Item"}]
                    },
                    "Status": {
                        "id": "status",
                        "type": "status",
                        "status": {"name": "In Progress", "color": "blue"}
                    }
                }
            }
        ],
        "next_cursor": None,
        "has_more": False
    }


@pytest.fixture
def mock_error_401_response():
    """Mock response for 401 Unauthorized error."""
    return {
        "object": "error",
        "status": 401,
        "code": "unauthorized",
        "message": "API token is invalid."
    }


@pytest.fixture
def mock_error_429_response():
    """Mock response for 429 Rate Limited error."""
    return {
        "object": "error",
        "status": 429,
        "code": "rate_limited",
        "message": "Rate limited. Please slow down your requests."
    }


@pytest.fixture
def mock_error_404_response():
    """Mock response for 404 Not Found error."""
    return {
        "object": "error",
        "status": 404,
        "code": "object_not_found",
        "message": "Could not find object with ID."
    }


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def valid_token_config():
    """Valid configuration with internal token authentication."""
    return {
        "credentials": {
            "auth_type": "token",
            "token": "secret_test_token_12345678901234567890123456789012345678901234"
        },
        "start_date": "2024-01-01T00:00:00Z",
        "page_size": 50,
        "fetch_page_blocks": True,
        "max_block_depth": 2
    }


@pytest.fixture
def valid_oauth_config():
    """Valid configuration with OAuth2 authentication."""
    return {
        "credentials": {
            "auth_type": "oauth2",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "access_token": "test-access-token-12345"
        },
        "start_date": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def notion_config(valid_token_config):
    """Create a NotionConfig instance."""
    return NotionConfig(**valid_token_config)


@pytest.fixture
def oauth_notion_config(valid_oauth_config):
    """Create a NotionConfig instance with OAuth2."""
    return NotionConfig(**valid_oauth_config)


# =============================================================================
# Mocked API Fixtures
# =============================================================================


@pytest.fixture
def mocked_notion_api(mock_bot_user_response, mock_users_list_response,
                      mock_search_databases_response, mock_search_pages_response,
                      mock_block_children_response, mock_comments_response):
    """Setup responses mock for Notion API."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        # Mock /users/me endpoint
        rsps.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )

        # Mock /users endpoint (list users)
        rsps.add(
            responses.GET,
            "https://api.notion.com/v1/users",
            json=mock_users_list_response,
            status=200
        )

        # Mock /search endpoint for databases
        rsps.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_databases_response,
            status=200
        )

        # Mock /search endpoint for pages (will be matched after databases)
        rsps.add(
            responses.POST,
            "https://api.notion.com/v1/search",
            json=mock_search_pages_response,
            status=200
        )

        # Mock block children endpoint
        rsps.add_callback(
            responses.GET,
            responses.matchers.urlencoded_params_matcher({}),
            callback=lambda req: (200, {}, json.dumps(mock_block_children_response)),
            content_type="application/json",
        )

        yield rsps


@pytest.fixture
def mocked_notion_api_connection_check(mock_bot_user_response):
    """Setup responses mock specifically for connection check."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )
        yield rsps


@pytest.fixture
def mocked_notion_api_auth_error(mock_error_401_response):
    """Setup responses mock for authentication error."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_error_401_response,
            status=401
        )
        yield rsps


@pytest.fixture
def mocked_notion_api_rate_limit(mock_error_429_response, mock_bot_user_response):
    """Setup responses mock for rate limit then success."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        # First call returns rate limit
        rsps.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_error_429_response,
            status=429,
            headers={"Retry-After": "1"}
        )
        # Second call succeeds
        rsps.add(
            responses.GET,
            "https://api.notion.com/v1/users/me",
            json=mock_bot_user_response,
            status=200
        )
        yield rsps


@pytest.fixture
def connector_with_mocked_api(notion_config, mocked_notion_api_connection_check):
    """Create a connector with mocked API."""
    return NotionSourceConnector(notion_config)
