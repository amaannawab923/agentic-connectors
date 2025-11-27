"""
Google Sheets Source Connector

A production-ready connector for extracting data from Google Sheets.
"""

from .config import (
    GoogleSheetsConfig,
    ServiceAccountCredentials,
    OAuth2Credentials,
    CredentialsUnion,
)
from .auth import GoogleSheetsAuthenticator
from .client import GoogleSheetsClient
from .connector import GoogleSheetsConnector
from .streams import (
    BaseStream,
    SheetStream,
    StreamSchema,
    StreamMetadata,
)
from .utils import (
    GoogleSheetsError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    InvalidRequestError,
    ConnectionError,
)

__all__ = [
    # Config
    "GoogleSheetsConfig",
    "ServiceAccountCredentials",
    "OAuth2Credentials",
    "CredentialsUnion",
    # Auth
    "GoogleSheetsAuthenticator",
    # Client
    "GoogleSheetsClient",
    # Connector
    "GoogleSheetsConnector",
    # Streams
    "BaseStream",
    "SheetStream",
    "StreamSchema",
    "StreamMetadata",
    # Exceptions
    "GoogleSheetsError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "InvalidRequestError",
    "ConnectionError",
]

__version__ = "1.0.0"
