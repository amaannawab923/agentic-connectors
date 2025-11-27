"""
Import validation tests for the Notion connector.

These tests verify that all modules can be imported successfully.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestImportValidation:
    """Test class for import validation."""

    def test_import_connector_module(self):
        """Test that connector module can be imported."""
        try:
            from src.connector import NotionSourceConnector
            assert NotionSourceConnector is not None
        except ImportError as e:
            pytest.fail(f"Failed to import NotionSourceConnector: {e}")

    def test_import_config_module(self):
        """Test that config module can be imported."""
        try:
            from src.config import NotionConfig, InternalTokenCredentials, OAuth2Credentials
            assert NotionConfig is not None
            assert InternalTokenCredentials is not None
            assert OAuth2Credentials is not None
        except ImportError as e:
            pytest.fail(f"Failed to import config classes: {e}")

    def test_import_auth_module(self):
        """Test that auth module can be imported."""
        try:
            from src.auth import (
                NotionAuthenticator,
                InternalTokenAuth,
                OAuth2Auth,
                create_authenticator
            )
            assert NotionAuthenticator is not None
            assert InternalTokenAuth is not None
            assert OAuth2Auth is not None
            assert create_authenticator is not None
        except ImportError as e:
            pytest.fail(f"Failed to import auth classes: {e}")

    def test_import_client_module(self):
        """Test that client module can be imported."""
        try:
            from src.client import NotionClient, RateLimiter
            assert NotionClient is not None
            assert RateLimiter is not None
        except ImportError as e:
            pytest.fail(f"Failed to import client classes: {e}")

    def test_import_streams_module(self):
        """Test that streams module can be imported."""
        try:
            from src.streams import (
                BaseStream,
                UsersStream,
                DatabasesStream,
                PagesStream,
                BlocksStream,
                CommentsStream,
                DatabasePagesStream,
                get_all_streams,
                get_stream_by_name
            )
            assert BaseStream is not None
            assert UsersStream is not None
            assert DatabasesStream is not None
            assert PagesStream is not None
            assert BlocksStream is not None
            assert CommentsStream is not None
            assert DatabasePagesStream is not None
            assert get_all_streams is not None
            assert get_stream_by_name is not None
        except ImportError as e:
            pytest.fail(f"Failed to import streams classes: {e}")

    def test_import_utils_module(self):
        """Test that utils module can be imported."""
        try:
            from src.utils import (
                NotionError,
                RateLimitError,
                AuthenticationError,
                NotFoundError,
                ValidationError,
                ConfigurationError,
                extract_plain_text,
                extract_title,
                parse_notion_datetime,
                format_datetime_for_notion,
                format_property_value,
                flatten_properties,
                extract_block_content,
                normalize_notion_id,
                format_notion_id,
                setup_logging,
                log_api_call
            )
            assert NotionError is not None
            assert RateLimitError is not None
            assert AuthenticationError is not None
            assert NotFoundError is not None
            assert ValidationError is not None
            assert ConfigurationError is not None
            assert extract_plain_text is not None
            assert extract_title is not None
            assert parse_notion_datetime is not None
        except ImportError as e:
            pytest.fail(f"Failed to import utils: {e}")

    def test_import_package_exports(self):
        """Test that the main package exports are available."""
        try:
            from src import (
                NotionSourceConnector,
                NotionConfig,
                InternalTokenCredentials,
                OAuth2Credentials,
                NotionClient,
                NotionError,
                RateLimitError,
                AuthenticationError,
                NotFoundError,
                ValidationError,
            )
            assert NotionSourceConnector is not None
            assert NotionConfig is not None
            assert NotionClient is not None
        except ImportError as e:
            pytest.fail(f"Failed to import from package: {e}")

    def test_connector_class_attributes(self):
        """Test that NotionSourceConnector has expected attributes."""
        from src.connector import NotionSourceConnector

        # Check methods exist
        assert hasattr(NotionSourceConnector, '__init__')
        assert hasattr(NotionSourceConnector, 'check')
        assert hasattr(NotionSourceConnector, 'discover')
        assert hasattr(NotionSourceConnector, 'read')
        assert hasattr(NotionSourceConnector, 'from_config_dict')
        assert hasattr(NotionSourceConnector, 'from_config_file')
        assert hasattr(NotionSourceConnector, 'get_state')
        assert hasattr(NotionSourceConnector, 'set_state')
        assert hasattr(NotionSourceConnector, 'read_users')
        assert hasattr(NotionSourceConnector, 'read_databases')
        assert hasattr(NotionSourceConnector, 'read_pages')
        assert hasattr(NotionSourceConnector, 'read_blocks')
        assert hasattr(NotionSourceConnector, 'read_comments')

    def test_notion_config_class_attributes(self):
        """Test that NotionConfig has expected attributes."""
        from src.config import NotionConfig

        # Check field names
        assert hasattr(NotionConfig, 'model_fields')
        fields = NotionConfig.model_fields

        assert 'credentials' in fields
        assert 'start_date' in fields
        assert 'api_version' in fields
        assert 'requests_per_second' in fields
        assert 'max_retries' in fields
        assert 'page_size' in fields
        assert 'fetch_page_blocks' in fields
        assert 'max_block_depth' in fields
