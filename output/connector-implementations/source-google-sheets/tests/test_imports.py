"""Import validation tests for Google Sheets connector."""

import sys
import os
import pytest

# Add parent directory to path to import from src package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestImports:
    """Test that all modules can be imported without errors."""

    def test_import_utils(self):
        """Test utils module can be imported."""
        try:
            from src.utils import (
                normalize_header,
                parse_spreadsheet_id,
                build_range_notation,
                infer_json_schema_type,
                infer_schema_from_values,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import utils: {e}")

    def test_import_config(self):
        """Test config module can be imported."""
        try:
            from src.config import (
                GoogleSheetsConfig,
                ServiceAccountCredentials,
                OAuth2Credentials,
                StreamConfig,
                RateLimitSettings,
                Catalog,
                CatalogEntry,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import config: {e}")

    def test_import_auth(self):
        """Test auth module can be imported."""
        try:
            from src.auth import (
                AuthenticationError,
                GoogleSheetsAuthenticator,
                ServiceAccountAuthenticator,
                OAuth2Authenticator,
                create_authenticator,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import auth: {e}")

    def test_import_client(self):
        """Test client module can be imported."""
        try:
            from src.client import (
                GoogleSheetsClient,
                RateLimitConfig,
                APIError,
                RateLimitError,
                NotFoundError,
                PermissionDeniedError,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import client: {e}")

    def test_import_streams(self):
        """Test streams module can be imported."""
        try:
            from src.streams import (
                SheetStream,
                StreamMetadata,
                StreamSchema,
                MultiSheetReader,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import streams: {e}")

    def test_import_connector(self):
        """Test connector module can be imported."""
        try:
            from src.connector import (
                GoogleSheetsConnector,
                ConnectionTestResult,
                create_connector,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import connector: {e}")

    def test_import_package_init(self):
        """Test the package __init__.py can be imported."""
        try:
            from src import (
                GoogleSheetsConnector,
                GoogleSheetsConfig,
                ServiceAccountCredentials,
                OAuth2Credentials,
                AuthenticationError,
                APIError,
                RateLimitError,
            )
        except ImportError as e:
            pytest.fail(f"Failed to import from package: {e}")

    def test_pydantic_models_are_valid(self):
        """Test that Pydantic models are properly defined."""
        try:
            from src.config import (
                GoogleSheetsConfig,
                ServiceAccountCredentials,
                OAuth2Credentials,
            )

            # Try to access model fields
            assert hasattr(ServiceAccountCredentials, 'model_fields')
            assert hasattr(OAuth2Credentials, 'model_fields')
            assert hasattr(GoogleSheetsConfig, 'model_fields')

            # Check auth_type field exists for discriminator
            assert 'auth_type' in ServiceAccountCredentials.model_fields
            assert 'auth_type' in OAuth2Credentials.model_fields

        except Exception as e:
            pytest.fail(f"Pydantic models validation failed: {e}")

    def test_all_exports_accessible(self):
        """Test that all __all__ exports are accessible."""
        try:
            import src

            for name in src.__all__:
                assert hasattr(src, name), f"Export '{name}' not accessible from package"
        except Exception as e:
            pytest.fail(f"Package exports check failed: {e}")
