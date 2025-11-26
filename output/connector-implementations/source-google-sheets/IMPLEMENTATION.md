# Google Sheets Source Connector Implementation

## Overview

A production-ready source connector for extracting data from Google Sheets spreadsheets. This connector supports both Service Account and OAuth2 authentication methods, implements rate limiting with exponential backoff, and provides efficient batch-based data extraction.

## File Structure

```
src/
├── __init__.py    - Package exports and version info
├── auth.py        - Authentication handlers (Service Account & OAuth2)
├── client.py      - Google Sheets API client with rate limiting and retries
├── config.py      - Pydantic configuration models with validation
├── connector.py   - Main connector class with check/discover/read operations
├── streams.py     - Data stream definitions and schema generation
└── utils.py       - Utility functions for data transformation
```

## Authentication

- **Type**: Service Account (recommended) or OAuth2
- **Required Credentials**:
  - **Service Account**: `service_account_info` (JSON string or dict) OR `service_account_file` (path to JSON key file)
  - **OAuth2**: `client_id`, `client_secret`, `refresh_token`
- **Token Refresh**: OAuth2 tokens are automatically refreshed when expired. Service Account credentials are managed automatically by the Google auth library.
- **Scopes**: `https://www.googleapis.com/auth/spreadsheets.readonly`

### Service Account Setup

1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Share the spreadsheet with the service account email (found in the JSON key)
4. Use the JSON key in the connector configuration

### OAuth2 Setup

1. Create OAuth2 credentials in Google Cloud Console
2. Obtain refresh token through OAuth2 flow
3. Configure the connector with client_id, client_secret, and refresh_token

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `spreadsheets.get` | GET | Get spreadsheet metadata (sheet names, properties) |
| `spreadsheets.values.get` | GET | Read values from a single range |
| `spreadsheets.values.batchGet` | GET | Read values from multiple ranges |

## Data Streams

| Stream Name | Sync Mode | Primary Key | Description |
|-------------|-----------|-------------|-------------|
| `{sheet_name}` | full_refresh | None (configurable) | Each sheet in the spreadsheet becomes a stream |

- Stream names are derived from sheet names (sanitized for use as identifiers)
- Schemas are dynamically generated from the first row (headers)
- All columns are typed as `string | null` by default

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `spreadsheet_id` | string | Yes | - | Google Spreadsheet ID (from URL) |
| `credentials` | object | Yes | - | Authentication credentials |
| `credentials.auth_type` | string | Yes | - | `service_account` or `oauth2` |
| `row_batch_size` | integer | No | 200 | Rows per API request (1-1000) |
| `requests_per_minute` | integer | No | 60 | Rate limit (1-300) |
| `include_row_number` | boolean | No | false | Add `_row_number` to records |
| `value_render_option` | string | No | `FORMATTED_VALUE` | How to render cell values |
| `date_time_render_option` | string | No | `FORMATTED_STRING` | How to render dates |

### Example Configuration (Service Account)

```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "credentials": {
    "auth_type": "service_account",
    "service_account_info": "{\"type\": \"service_account\", \"project_id\": \"...\", ...}"
  },
  "row_batch_size": 200,
  "include_row_number": true
}
```

### Example Configuration (OAuth2)

```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "credentials": {
    "auth_type": "oauth2",
    "client_id": "your-client-id.apps.googleusercontent.com",
    "client_secret": "your-client-secret",
    "refresh_token": "your-refresh-token"
  }
}
```

## Testing Guide

### Prerequisites

1. **Google Cloud Project** with Sheets API enabled
2. **Service Account** or **OAuth2 credentials**
3. **Test Spreadsheet** shared with the service account (if using service account auth)
4. Python 3.9+ with dependencies installed

### Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Connector

#### Check Connection

```bash
python -m src.connector check --config config.json
```

Expected output:
```json
{"type": "CONNECTION_STATUS", "status": "SUCCEEDED", "message": "Successfully connected to 'Your Spreadsheet Name'", "details": {"spreadsheet_id": "...", "spreadsheet_title": "...", "sheet_count": 3}}
```

#### Discover Streams

```bash
python -m src.connector discover --config config.json
```

Expected output:
```json
{
  "type": "CATALOG",
  "catalog": {
    "streams": [
      {
        "name": "sheet1",
        "json_schema": {
          "type": "object",
          "properties": {
            "column_a": {"type": ["string", "null"]},
            "column_b": {"type": ["string", "null"]}
          }
        },
        "supported_sync_modes": ["full_refresh"]
      }
    ]
  }
}
```

#### Read Data

```bash
# Read all streams
python -m src.connector read --config config.json

# Read specific streams
python -m src.connector read --config config.json --streams "Sheet1,Sheet2"

# Output to file
python -m src.connector read --config config.json --output output.jsonl
```

Expected output (per record):
```json
{"type": "RECORD", "record": {"column_a": "value1", "column_b": "value2", "_stream": "sheet1", "_extracted_at": "2024-01-15T10:30:00.000Z"}}
```

### Programmatic Usage

```python
from src.connector import GoogleSheetsConnector
from src.config import GoogleSheetsConfig

# Create config
config = GoogleSheetsConfig.from_dict({
    "spreadsheet_id": "your-spreadsheet-id",
    "credentials": {
        "auth_type": "service_account",
        "service_account_file": "/path/to/service-account.json"
    }
})

# Create connector
connector = GoogleSheetsConnector(config)

# Check connection
result = connector.check_connection()
print(f"Connection status: {result.status}")

# Discover streams
catalog = connector.discover()
print(f"Found {len(catalog['streams'])} streams")

# Read data
for record in connector.read():
    print(record)
```

### Expected Behavior

#### Success Cases

- **Valid credentials**: Connection check returns `SUCCEEDED`
- **Valid spreadsheet**: Discover returns catalog with all sheets
- **Data read**: Records are yielded as dictionaries with normalized column names

#### Common Error Scenarios

| Error | Cause | Resolution |
|-------|-------|------------|
| `AuthenticationError` | Invalid credentials | Check credentials JSON format and values |
| `SpreadsheetNotFoundError` | Invalid spreadsheet ID | Verify the spreadsheet ID from the URL |
| `AccessDeniedError` | No permission | Share spreadsheet with service account email |
| `RateLimitError` | Too many requests | Reduce `requests_per_minute` config |

## Implementation Notes

### Key Design Decisions

1. **Batch-based fetching**: Data is fetched in configurable batches (default 200 rows) to handle large spreadsheets efficiently without memory issues.

2. **Dynamic schema generation**: Schemas are inferred from the header row. All values are treated as strings since Google Sheets doesn't provide type information through the API.

3. **Header normalization**: Column names are normalized to snake_case for consistent field names (e.g., "First Name" → "first_name").

4. **Rate limiting**: Built-in rate limiting respects Google's quotas (60 requests/minute per user default) with automatic exponential backoff.

5. **Error handling**: Comprehensive error handling with custom exceptions for different failure modes.

### Known Limitations

1. **Incremental sync not supported**: Google Sheets doesn't provide change tracking, so only full refresh is available.

2. **All values as strings**: The API returns formatted values as strings; type coercion must be done downstream.

3. **Empty cells**: Empty cells in rows with data are returned as empty strings or `null`.

4. **Large spreadsheets**: Very large spreadsheets (>100K rows) may take significant time due to API rate limits.

5. **Merged cells**: Merged cells may not be handled correctly; only the top-left cell contains the value.

### Future Improvements

1. **Incremental sync via polling**: Implement state management to track last sync and compare for changes.

2. **Type inference**: Add optional type inference from sample data.

3. **Parallel fetching**: Implement concurrent batch fetching for multiple sheets.

4. **Change detection**: Use spreadsheet metadata (modifiedTime) for basic change detection.

5. **Write support**: Add destination connector capability for writing data back to sheets.

## Rate Limits Reference

| Limit Type | Per Project | Per User |
|------------|-------------|----------|
| Read Requests | 300/minute | 60/minute |
| Write Requests | 300/minute | 60/minute |
| Request Timeout | 180 seconds | - |

The connector defaults to 60 requests/minute to stay within per-user limits.
