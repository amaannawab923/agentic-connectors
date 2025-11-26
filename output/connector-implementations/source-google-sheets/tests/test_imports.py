"""
Import validation tests for Google Sheets connector modules.
"""
import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestImports:
    """Test that all modules can be imported without errors."""

    def test_import_utils(self):
        """Test importing utils module."""
        try:
            from utils import (
                extract_spreadsheet_id,
                sanitize_sheet_name,
                normalize_header,
                deduplicate_headers,
                convert_value,
                infer_type,
                generate_record_id,
                chunk_list,
                format_a1_range,
                get_column_letter,
                get_current_timestamp,
                safe_get,
                flatten_dict,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from utils: {e}")

    def test_import_auth(self):
        """Test importing auth module."""
        try:
            from auth import (
                GoogleSheetsAuthenticator,
                ServiceAccountAuth,
                OAuth2Auth,
                AuthenticationError,
                create_authenticator,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from auth: {e}")

    def test_import_config(self):
        """Test importing config module."""
        try:
            from config import (
                AuthType,
                ServiceAccountCredentials,
                OAuth2Credentials,
                StreamSelection,
                GoogleSheetsConfig,
                ConfigSchema,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from config: {e}")

    def test_import_client(self):
        """Test importing client module."""
        try:
            from client import (
                GoogleSheetsClient,
                GoogleSheetsAPIError,
                RateLimitError,
                SpreadsheetNotFoundError,
                AccessDeniedError,
                InvalidRequestError,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from client: {e}")

    def test_import_streams(self):
        """Test importing streams module."""
        try:
            from streams import (
                SyncMode,
                StreamSchema,
                StreamConfig,
                SheetStream,
                StreamCatalog,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from streams: {e}")

    def test_import_connector(self):
        """Test importing connector module."""
        try:
            from connector import (
                ConnectorStatus,
                ConnectionCheckResult,
                SyncResult,
                GoogleSheetsConnector,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from connector: {e}")

    def test_import_package_init(self):
        """Test importing from package __init__."""
        try:
            import src
            from src import (
                GoogleSheetsAuthenticator,
                ServiceAccountAuth,
                OAuth2Auth,
                AuthenticationError,
                GoogleSheetsClient,
                GoogleSheetsAPIError,
                GoogleSheetsConfig,
                ServiceAccountCredentials,
                OAuth2Credentials,
                GoogleSheetsConnector,
                SheetStream,
                StreamConfig,
                SyncMode,
                extract_spreadsheet_id,
                sanitize_sheet_name,
                normalize_header,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from src package: {e}")

    def test_version_defined(self):
        """Test that version is defined in package."""
        try:
            import src
            assert hasattr(src, '__version__'), "Package should have __version__ attribute"
            assert src.__version__ is not None
            assert len(src.__version__) > 0
        except ImportError as e:
            pytest.fail(f"Failed to import src package: {e}")
