"""
Notion Source Connector

A production-ready connector for extracting data from Notion workspaces.
Supports internal integration tokens and OAuth 2.0 authentication.
"""

from .auth import (
    NotionAuthenticator,
    TokenAuthenticator,
    OAuth2Authenticator,
    create_authenticator,
)
from .client import NotionClient
from .config import (
    NotionConfig,
    TokenCredentials,
    OAuth2Credentials,
    StreamConfig,
    ConnectorState,
    StreamState,
)
from .connector import NotionSourceConnector
from .streams import (
    BaseStream,
    UsersStream,
    DatabasesStream,
    PagesStream,
    BlocksStream,
    CommentsStream,
    DatabasePagesStream,
    get_all_streams,
    get_stream_by_name,
)
from .utils import (
    NotionError,
    NotionAuthenticationError,
    NotionRateLimitError,
    NotionNotFoundError,
    NotionValidationError,
    NotionServerError,
    NotionConfigurationError,
    extract_plain_text,
    extract_title,
    parse_notion_datetime,
    format_datetime_for_notion,
    format_property_value,
    flatten_properties,
    extract_block_content,
    get_block_url,
    normalize_notion_id,
    format_notion_id,
    setup_logging,
)

__version__ = "1.0.0"
__all__ = [
    # Auth
    "NotionAuthenticator",
    "TokenAuthenticator",
    "OAuth2Authenticator",
    "create_authenticator",
    # Client
    "NotionClient",
    # Config
    "NotionConfig",
    "TokenCredentials",
    "OAuth2Credentials",
    "StreamConfig",
    "ConnectorState",
    "StreamState",
    # Connector
    "NotionSourceConnector",
    # Streams
    "BaseStream",
    "UsersStream",
    "DatabasesStream",
    "PagesStream",
    "BlocksStream",
    "CommentsStream",
    "DatabasePagesStream",
    "get_all_streams",
    "get_stream_by_name",
    # Exceptions
    "NotionError",
    "NotionAuthenticationError",
    "NotionRateLimitError",
    "NotionNotFoundError",
    "NotionValidationError",
    "NotionServerError",
    "NotionConfigurationError",
    # Utils
    "extract_plain_text",
    "extract_title",
    "parse_notion_datetime",
    "format_datetime_for_notion",
    "format_property_value",
    "flatten_properties",
    "extract_block_content",
    "get_block_url",
    "normalize_notion_id",
    "format_notion_id",
    "setup_logging",
]
