"""
Import tests for Google Sheets connector.

These tests verify that all modules can be imported without errors.
"""

import sys
import pytest
from pathlib import Path


class TestImports:
    """Test that all modules can be imported."""

    def test_import_config(self):
        """Test that config module can be imported."""
        from src.config import (
            GoogleSheetsConfig,
            ServiceAccountCredentials,
            OAuth2Credentials,
            APIKeyCredentials,
            SheetConfig,
            ConnectionStatus,
            SyncResult,
        )
        assert GoogleSheetsConfig is not None
        assert ServiceAccountCredentials is not None
        assert OAuth2Credentials is not None

    def test_import_utils(self):
        """Test that utils module can be imported."""
        from src.utils import (
            GoogleSheetsError,
            AuthenticationError,
            RateLimitError,
            NotFoundError,
            InvalidRequestError,
            ServerError,
            sanitize_column_name,
            build_range_notation,
        )
        assert GoogleSheetsError is not None
        assert sanitize_column_name is not None

    def test_import_auth(self):
        """Test that auth module can be imported."""
        from src.auth import (
            BaseAuthenticator,
            ServiceAccountAuthenticator,
            OAuth2Authenticator,
            APIKeyAuthenticator,
            GoogleSheetsAuthenticator,
        )
        assert GoogleSheetsAuthenticator is not None

    def test_import_client(self):
        """Test that client module can be imported."""
        from src.client import (
            GoogleSheetsClient,
            RateLimiter,
            RetryHandler,
        )
        assert GoogleSheetsClient is not None
        assert RateLimiter is not None

    def test_import_streams(self):
        """Test that streams module can be imported."""
        from src.streams import (
            BaseStream,
            SheetStream,
            StreamSchema,
            StreamMetadata,
            SpreadsheetStreamFactory,
        )
        assert SheetStream is not None
        assert StreamSchema is not None

    def test_import_connector(self):
        """Test that connector module can be imported."""
        from src.connector import (
            GoogleSheetsConnector,
            Catalog,
            CatalogEntry,
            Record,
            StateMessage,
            create_connector,
        )
        assert GoogleSheetsConnector is not None
        assert create_connector is not None

    def test_import_package_init(self):
        """Test that package __init__ exports are available."""
        from src import (
            GoogleSheetsConfig,
            GoogleSheetsConnector,
            GoogleSheetsClient,
            GoogleSheetsAuthenticator,
            GoogleSheetsError,
            AuthenticationError,
        )
        assert GoogleSheetsConfig is not None
        assert GoogleSheetsConnector is not None
