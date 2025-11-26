# Google Sheets Source Connector - Implementation Summary

## Overview

This is a production-ready source connector for extracting data from Google Sheets spreadsheets. The connector is standalone and does not rely on any external connector frameworks (no Airbyte CDK, no Singer SDK).

## Architecture

### File Structure

```
src/
├── __init__.py      # Package exports
├── auth.py          # Authentication handling (Service Account, OAuth2)
├── client.py        # API client with rate limiting and retry logic
├── config.py        # Configuration models using Pydantic
├── connector.py     # Main connector class
├── streams.py       # Data stream definitions
└── utils.py         # Utility functions
```

## Features

### Authentication Methods

1. **Service Account** (Recommended for automated pipelines)
   - Uses a JSON key file from Google Cloud Console
   - The spreadsheet must be shared with the service account email
   - Supports automatic credential refresh

2. **OAuth2** (For user-delegated access)
   - Uses client ID, client secret, and refresh token
   - Suitable when accessing spreadsheets on behalf of users
   - Handles token refresh automatically

### Rate Limiting & Retry Logic

- Configurable requests per minute (default: 60, Google limit: 300/project)
- Exponential backoff with jitter on rate limit errors (HTTP 429)
- Automatic retries on server errors (5xx)
- Configurable max retries and delay parameters

### Data Extraction

- **Batch Reading**: Reads data in configurable batches (default: 1000 rows)
- **Header Normalization**: Handles empty headers, duplicates, and special characters
- **Schema Inference**: Automatically infers JSON Schema from sample data
- **Multi-Sheet Support**: Can read from multiple sheets in a single spreadsheet

## Usage Example

```python
from src import (
    GoogleSheetsConnector,
    GoogleSheetsConfig,
    ServiceAccountCredentials,
)

# Configure the connector
config = GoogleSheetsConfig(
    spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    credentials=ServiceAccountCredentials(
        project_id="my-project",
        private_key="-----BEGIN PRIVATE KEY-----\n...",
        client_email="connector@my-project.iam.gserviceaccount.com",
    ),
    row_batch_size=1000,
    header_row=1,
)

# Create connector instance
with GoogleSheetsConnector(config) as connector:
    # Test the connection
    result = connector.check_connection()
    if not result.success:
        print(f"Connection failed: {result.message}")
        exit(1)

    print(f"Connected to: {result.spreadsheet_title}")

    # Discover available streams (sheets)
    catalog = connector.discover()
    print(f"Found {len(catalog.streams)} sheets")

    # Read data from a specific sheet
    for record in connector.read("Sheet1"):
        print(record)

    # Or read from all sheets
    for record in connector.read_all():
        sheet_name = record.pop("_stream")
        print(f"[{sheet_name}] {record}")
```

## Configuration Options

### GoogleSheetsConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `spreadsheet_id` | str | Required | The ID from the Google Sheets URL |
| `credentials` | ServiceAccountCredentials \| OAuth2Credentials | Required | Authentication credentials |
| `streams` | List[StreamConfig] | None | Specific sheets to extract (all if None) |
| `row_batch_size` | int | 1000 | Rows per API call |
| `header_row` | int | 1 | Row containing column headers |
| `include_row_number` | bool | True | Add `_row_number` field to records |

### RateLimitSettings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `requests_per_minute` | int | 60 | Max requests per minute |
| `max_retries` | int | 5 | Max retry attempts |
| `base_delay` | float | 1.0 | Base delay for backoff (seconds) |
| `max_delay` | float | 60.0 | Max delay between retries (seconds) |

## Error Handling

The connector defines custom exceptions for clear error handling:

- `AuthenticationError`: Credential or permission issues
- `APIError`: Base API error with status code and reason
- `RateLimitError`: Rate limit exceeded (HTTP 429)
- `NotFoundError`: Spreadsheet or sheet not found (HTTP 404)
- `PermissionDeniedError`: Access denied (HTTP 403)

## API Compliance

### Scopes Used

```
https://www.googleapis.com/auth/spreadsheets.readonly
https://www.googleapis.com/auth/drive.readonly
```

### Rate Limits Respected

- 300 read requests/minute per project
- 60 read requests/minute per user
- 180 second request timeout
- Automatic backoff on 429 responses

## Known Limitations

1. **Full Refresh Only**: No incremental sync support (Google Sheets doesn't track changes)
2. **Maximum Cells**: Google Sheets limit of 10 million cells per spreadsheet
3. **Empty Rows**: Consecutive empty rows may signal end of data
4. **Merged Cells**: Merged cells may result in None values for non-anchor cells
5. **Formula Values**: By default, returns computed values, not formulas

## Testing

To test the connector:

```python
# test_connector.py
import json
from src import create_connector

# Load credentials
with open("service_account.json") as f:
    creds = json.load(f)

# Create connector
connector = create_connector({
    "spreadsheet_id": "your-spreadsheet-id",
    "credentials": {
        "auth_type": "service_account",
        **creds,
    },
})

# Test connection
result = connector.check_connection()
print(f"Connection: {'OK' if result.success else 'FAILED'}")
print(f"Details: {result}")
```

## Dependencies

- `google-api-python-client>=2.100.0`
- `google-auth>=2.23.0`
- `google-auth-httplib2>=0.1.1`
- `google-auth-oauthlib>=1.1.0`
- `pydantic>=2.5.0`
- `httplib2>=0.22.0`
- `requests>=2.31.0`

Install with:
```bash
pip install -r requirements.txt
```
