# Google Sheets Source Connector Implementation

## Overview

This is a production-ready source connector for extracting data from Google Sheets. It provides a standalone implementation without external connector frameworks, featuring robust error handling, rate limiting, and comprehensive type hints.

## Features

- **Multiple Authentication Methods**: Service Account, OAuth 2.0, and API Key support
- **Rate Limiting**: Built-in rate limiter respecting Google's 60 requests/minute per-user limit
- **Exponential Backoff**: Automatic retries with jitter for transient failures
- **Schema Inference**: Automatic type inference from sample data
- **Batch Reading**: Configurable batch size for memory-efficient data extraction
- **Full Type Safety**: Complete type hints throughout the codebase
- **Pydantic Validation**: Configuration validation using Pydantic v2

## File Structure

```
src/
├── __init__.py          # Package exports
├── auth.py              # Authentication handling (Service Account, OAuth2, API Key)
├── client.py            # API client with rate limiting and retries
├── config.py            # Pydantic configuration models
├── connector.py         # Main connector class with check/discover/read
├── streams.py           # Data stream definitions
└── utils.py             # Utility functions and custom exceptions
requirements.txt         # Python dependencies
```

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Using Service Account Authentication

```python
from src import GoogleSheetsConnector, GoogleSheetsConfig, ServiceAccountCredentials

# Load your service account JSON
with open('service_account.json', 'r') as f:
    service_account_info = f.read()

config = GoogleSheetsConfig(
    spreadsheet_id="your-spreadsheet-id",
    credentials=ServiceAccountCredentials(
        service_account_info=service_account_info
    )
)

connector = GoogleSheetsConnector(config)

# Check connection
status = connector.check()
if status.connected:
    print(f"Connected to: {status.spreadsheet_title}")

    # Discover available sheets
    catalog = connector.discover()
    for entry in catalog.streams:
        print(f"Found stream: {entry.stream_name}")

    # Read data
    for record in connector.read():
        print(record.to_json())
```

### Using OAuth 2.0 Authentication

```python
from src import GoogleSheetsConnector, GoogleSheetsConfig, OAuth2Credentials

config = GoogleSheetsConfig(
    spreadsheet_id="your-spreadsheet-id",
    credentials=OAuth2Credentials(
        client_id="your-client-id",
        client_secret="your-client-secret",
        refresh_token="your-refresh-token"
    )
)

connector = GoogleSheetsConnector(config)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `spreadsheet_id` | str | required | Spreadsheet ID or full URL |
| `credentials` | Union | required | Authentication credentials |
| `batch_size` | int | 200 | Rows per API request |
| `value_render_option` | str | "UNFORMATTED_VALUE" | How to render cell values |
| `date_time_render_option` | str | "FORMATTED_STRING" | How to render dates |
| `include_row_numbers` | bool | True | Include `_row_number` field |
| `sanitize_column_names` | bool | True | Make column names JSON-safe |
| `max_retries` | int | 5 | Maximum retry attempts |
| `retry_delay` | float | 1.0 | Base delay between retries |

## CLI Usage

```bash
# Check connection
python -m src.connector check --config config.json

# Discover streams
python -m src.connector discover --config config.json

# Read data
python -m src.connector read --config config.json
```

## API Reference

### GoogleSheetsConnector

#### `check() -> ConnectionStatus`
Verifies connection to the spreadsheet.

#### `discover() -> Catalog`
Discovers available sheets and their schemas.

#### `read(selected_streams, state) -> Iterator[Record | StateMessage]`
Reads data from selected streams.

#### `read_stream(stream_name) -> Iterator[Dict]`
Reads data from a specific stream.

#### `sync(selected_streams) -> List[SyncResult]`
Performs a full sync and returns results.

### Error Handling

The connector provides custom exceptions:

- `GoogleSheetsError`: Base exception
- `AuthenticationError`: Authentication failures (401, 403)
- `RateLimitError`: Rate limit exceeded (429)
- `NotFoundError`: Resource not found (404)
- `InvalidRequestError`: Invalid request (400)
- `ServerError`: Server errors (5xx)

## Rate Limits

Google Sheets API limits:
- **300 requests/minute** per project
- **60 requests/minute** per user

The connector implements:
- Sliding window rate limiter (60 req/min)
- Exponential backoff with jitter
- Automatic retry on 429 and 5xx errors

## Known Limitations

1. **Full Refresh Only**: Google Sheets doesn't support change tracking
2. **No Streaming Updates**: Use polling for real-time data
3. **Large Sheets**: Sheets with >5M cells may timeout; use specific ranges
4. **Merged Cells**: May cause alignment issues
5. **Formula Dependencies**: External formula references may fail

## Dependencies

- `google-api-python-client>=2.100.0`
- `google-auth>=2.23.0`
- `google-auth-oauthlib>=1.1.0`
- `pydantic>=2.5.0`

## License

MIT License
