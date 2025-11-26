"""
Google Sheets Source Connector

A production-ready connector for extracting data from Google Sheets.
Supports OAuth2 and Service Account authentication methods.
"""

from src.auth import (
    GoogleSheetsAuthenticator,
    ServiceAccountAuth,
    OAuth2Auth,
    AuthenticationError,
)
from src.client import GoogleSheetsClient, GoogleSheetsAPIError
from src.config import (
    GoogleSheetsConfig,
    ServiceAccountCredentials,
    OAuth2Credentials,
)
from src.connector import GoogleSheetsConnector
from src.streams import (
    SheetStream,
    StreamConfig,
    SyncMode,
)
from src.utils import (
    extract_spreadsheet_id,
    sanitize_sheet_name,
    normalize_header,
)

__version__ = "1.0.0"
__all__ = [
    # Auth
    "GoogleSheetsAuthenticator",
    "ServiceAccountAuth",
    "OAuth2Auth",
    "AuthenticationError",
    # Client
    "GoogleSheetsClient",
    "GoogleSheetsAPIError",
    # Config
    "GoogleSheetsConfig",
    "ServiceAccountCredentials",
    "OAuth2Credentials",
    # Connector
    "GoogleSheetsConnector",
    # Streams
    "SheetStream",
    "StreamConfig",
    "SyncMode",
    # Utils
    "extract_spreadsheet_id",
    "sanitize_sheet_name",
    "normalize_header",
]
