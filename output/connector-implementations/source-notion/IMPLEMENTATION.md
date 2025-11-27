# Notion Source Connector Implementation

## Overview

This is a production-ready source connector for extracting data from Notion workspaces. The connector supports both internal integration tokens and OAuth 2.0 authentication, implements comprehensive rate limiting and retry logic, and provides full incremental sync support.

## Architecture

```
source-notion/
├── src/
│   ├── __init__.py      # Package exports
│   ├── auth.py          # Authentication handlers (Token, OAuth2)
│   ├── client.py        # API client with rate limiting
│   ├── config.py        # Pydantic configuration models
│   ├── connector.py     # Main connector class
│   ├── streams.py       # Data stream definitions
│   └── utils.py         # Utilities and exceptions
└── requirements.txt     # Python dependencies
```

## Features

### Authentication
- **Internal Integration Token**: Static tokens for single-workspace integrations
- **OAuth 2.0**: For public integrations accessing multiple workspaces
- Automatic token refresh for OAuth (when supported)
- Token validation on connection check

### Rate Limiting
- Token bucket rate limiter (3 requests/second default)
- Configurable rate limits
- Respects `Retry-After` headers from Notion API
- Exponential backoff for rate limit errors

### Error Handling
- Custom exception hierarchy:
  - `NotionError` (base)
  - `RateLimitError`
  - `AuthenticationError`
  - `NotFoundError`
  - `ValidationError`
- Automatic retry for transient errors (429, 5xx)
- Detailed error messages with request IDs

### Data Streams

| Stream | Description | Incremental | Primary Key |
|--------|-------------|-------------|-------------|
| `users` | Workspace users (people and bots) | No | `id` |
| `databases` | Database schemas and metadata | Yes | `id` |
| `pages` | Page metadata and properties | Yes | `id` |
| `blocks` | Page content blocks (recursive) | Yes | `id` |
| `comments` | Page and block comments | Yes | `id` |

### Incremental Sync
- Uses `last_edited_time` as cursor for most streams
- State checkpointing every 100 records
- Configurable start date for initial sync

## Configuration

### Basic Configuration (Internal Token)

```json
{
  "credentials": {
    "auth_type": "token",
    "token": "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  },
  "start_date": "2024-01-01T00:00:00Z",
  "page_size": 100,
  "fetch_page_blocks": true,
  "max_block_depth": 3
}
```

### OAuth 2.0 Configuration

```json
{
  "credentials": {
    "auth_type": "oauth2",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "access_token": "your-access-token"
  },
  "start_date": "2024-01-01T00:00:00Z"
}
```

### Advanced Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `api_version` | string | `2022-06-28` | Notion API version |
| `requests_per_second` | float | `3.0` | Rate limit (max 10) |
| `max_retries` | int | `5` | Retry attempts |
| `retry_base_delay` | float | `1.0` | Base backoff delay |
| `page_size` | int | `100` | Items per page (max 100) |
| `request_timeout` | int | `60` | Request timeout (seconds) |
| `fetch_page_blocks` | bool | `true` | Fetch block content |
| `max_block_depth` | int | `3` | Max nested block depth |
| `database_ids` | list | `null` | Specific databases to sync |

## Usage

### Programmatic Usage

```python
from src import NotionSourceConnector, NotionConfig, InternalTokenCredentials

# Create configuration
config = NotionConfig(
    credentials=InternalTokenCredentials(
        auth_type="token",
        token="secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ),
    start_date="2024-01-01T00:00:00Z"
)

# Initialize connector
connector = NotionSourceConnector(config)

# Check connection
status = connector.check()
print(f"Connection: {status.status}")

# Discover streams
catalog = connector.discover()
for stream in catalog.streams:
    print(f"Stream: {stream.name}")

# Read data
for message in connector.read():
    if message.get("type") == "RECORD":
        print(f"Record from {message['record']['stream']}")
    elif message.get("type") == "STATE":
        print(f"State checkpoint")
```

### Convenience Methods

```python
# Read specific streams
for user in connector.read_users():
    print(f"User: {user['name']}")

for database in connector.read_databases():
    print(f"Database: {database['title']}")

for page in connector.read_pages():
    print(f"Page: {page['title']}")

# Read blocks from specific pages
for block in connector.read_blocks(page_ids=["page-id-1", "page-id-2"]):
    print(f"Block: {block['type']}")

# Query specific database
for page in connector.read_database("database-id"):
    print(f"Database page: {page['title']}")
```

### CLI Usage

```bash
# Check connection
python -m src.connector check --config config.json

# Discover streams
python -m src.connector discover --config config.json

# Read data
python -m src.connector read --config config.json

# Incremental read with state
python -m src.connector read --config config.json --state state.json

# Debug mode
python -m src.connector read --config config.json --debug
```

## API Reference

### NotionSourceConnector

Main connector class.

#### Methods

- `check() -> ConnectionStatus`: Validate connection
- `discover() -> Catalog`: Discover available streams
- `read(stream_names, state) -> Generator`: Read data from streams
- `read_users() -> Generator`: Read users stream
- `read_databases() -> Generator`: Read databases stream
- `read_pages() -> Generator`: Read pages stream
- `read_blocks(page_ids) -> Generator`: Read blocks stream
- `read_comments(page_ids) -> Generator`: Read comments stream
- `read_database(database_id) -> Generator`: Read specific database
- `get_state() -> Dict`: Get current state
- `set_state(state)`: Set connector state

### NotionClient

Low-level API client.

#### Methods

- `get_current_user() -> Dict`: Get bot user info
- `list_users() -> Generator`: List all users
- `get_database(id) -> Dict`: Get database schema
- `query_database(id, filter, sorts) -> Generator`: Query database
- `get_page(id) -> Dict`: Get page
- `get_block_children(id) -> Generator`: Get block children
- `get_all_blocks(page_id, max_depth) -> Generator`: Get all blocks recursively
- `search(query, filter) -> Generator`: Search pages/databases
- `get_comments(block_id) -> Generator`: Get comments

## Error Handling

```python
from src.utils import (
    NotionError,
    RateLimitError,
    AuthenticationError,
    NotFoundError
)

try:
    connector.read()
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
except AuthenticationError as e:
    print(f"Auth error: {e.message}")
except NotFoundError as e:
    print(f"Not found: {e.message}")
except NotionError as e:
    print(f"API error: {e.code} - {e.message}")
```

## Limitations

1. **Rate Limits**: Notion enforces 3 requests/second average
2. **Search API**: May not return recently shared pages immediately
3. **Rich Text**: Truncated to 2000 characters per property
4. **Nested Blocks**: Require separate API calls (configurable depth)
5. **Formula/Rollup**: May have delayed updates

## Testing

```python
# Unit tests
pytest tests/unit

# Integration tests (requires Notion token)
NOTION_TOKEN=secret_xxx pytest tests/integration
```

## Dependencies

- `requests>=2.28.0`: HTTP client
- `pydantic>=2.0.0`: Configuration validation
- `typing-extensions>=4.0.0`: Type hint support
- `urllib3>=1.26.0`: HTTP utilities
- `python-dateutil>=2.8.0`: Date parsing

## Version History

- **1.0.0**: Initial release
  - Full support for Users, Databases, Pages, Blocks, Comments
  - Internal token and OAuth 2.0 authentication
  - Rate limiting and retry logic
  - Incremental sync support
