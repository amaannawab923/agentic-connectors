"""
Google Sheets Source Connector

A production-ready connector for extracting data from Google Sheets.
Supports service account and OAuth2 authentication methods.
"""

from .auth import (
    AuthenticationError,
    GoogleSheetsAuthenticator,
    ServiceAccountAuthenticator,
    OAuth2Authenticator,
)
from .client import (
    GoogleSheetsClient,
    RateLimitError,
    APIError,
)
from .config import (
    GoogleSheetsConfig,
    ServiceAccountCredentials,
    OAuth2Credentials,
    StreamConfig,
)
from .connector import (
    GoogleSheetsConnector,
    ConnectionTestResult,
)
from .streams import (
    SheetStream,
    StreamSchema,
    StreamMetadata,
)
from .utils import (
    normalize_header,
    parse_spreadsheet_id,
    build_range_notation,
    infer_json_schema_type,
)

__version__ = "1.0.0"
__author__ = "Connector Platform"

__all__ = [
    # Auth
    "AuthenticationError",
    "GoogleSheetsAuthenticator",
    "ServiceAccountAuthenticator",
    "OAuth2Authenticator",
    # Client
    "GoogleSheetsClient",
    "RateLimitError",
    "APIError",
    # Config
    "GoogleSheetsConfig",
    "ServiceAccountCredentials",
    "OAuth2Credentials",
    "StreamConfig",
    # Connector
    "GoogleSheetsConnector",
    "ConnectionTestResult",
    # Streams
    "SheetStream",
    "StreamSchema",
    "StreamMetadata",
    # Utils
    "normalize_header",
    "parse_spreadsheet_id",
    "build_range_notation",
    "infer_json_schema_type",
]
