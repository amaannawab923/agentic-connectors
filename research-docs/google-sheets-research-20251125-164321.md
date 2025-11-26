Excellent! Now I have all the information needed. Let me compile the comprehensive markdown document:

# Google Sheets Source Connector - Implementation Research

## 1. Executive Summary

The Google Sheets API v4 provides a straightforward REST interface for reading spreadsheet data with generous free rate limits (300 reads/min per project, 60/min per user). Authentication is best handled via OAuth2 for user contexts or Service Account credentials for automated pipelines. The API uses simple range-based queries without complex pagination, making it ideal for source connector implementation. Key considerations include exponential backoff for rate limiting (429 errors) and handling oversized documents.

## 2. API Overview

### Base URL
```
https://sheets.googleapis.com/v4/
```

### API Version
Google Sheets API v4 (current stable version)

### Key Capabilities
- Read and write spreadsheet data
- Manage sheets, formatting, and formulas
- Batch operations for efficiency
- Real-time collaboration support
- **No pagination required** - data retrieved by range specification

### Pricing
**100% Free** - No charges for API usage, even when exceeding quotas (requests are throttled, not billed)

## 3. Authentication Patterns

### Recommended: Service Account (For Automated Pipelines)

**Best for:** Data connectors, ETL pipelines, server-side applications

**Setup Steps:**
1. Create a GCP project
2. Enable Google Sheets API and Google Drive API
3. Create a service account and download JSON key
4. Share spreadsheet with service account email (e.g., `my-service@project.iam.gserviceaccount.com`)

**Required Scopes:**
```python
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',  # Read-only
    # OR
    'https://www.googleapis.com/auth/spreadsheets',  # Read-write
]
```

**Python Code Example:**
```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = 'path/to/service-account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, 
    scopes=SCOPES
)

# Build service
service = build('sheets', 'v4', credentials=credentials)
```

### Alternative: OAuth 2.0 (For User-Facing Applications)

**Best for:** Applications requiring user consent, cloud-based connectors

**Configuration:**
- Client ID and Client Secret from GCP Console
- OAuth redirect URL
- User authorization flow with consent screen
- Refresh tokens for long-lived access

**Airbyte Cloud uses OAuth** to simplify user authentication through their UI.

### Configuration Schema

```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "credentials": {
    "auth_type": "service_account",
    "service_account_info": "{...JSON key content...}"
  },
  "names_conversion": true,  // Convert to SQL-compliant names
  "batch_size": 200  // Rows per API call
}
```

## 4. Key Endpoints

### Primary Data Reading Endpoints

#### 1. **spreadsheets.values.get**
**Purpose:** Retrieve a single range of values

**Endpoint:**
```
GET https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}
```

**Example:**
```python
result = service.spreadsheets().values().get(
    spreadsheetId='1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms',
    range='Sheet1!A1:Z1000'
).execute()

values = result.get('values', [])
```

**Parameters:**
- `spreadsheetId`: The spreadsheet ID (from URL)
- `range`: A1 notation (e.g., "Sheet1!A1:D10")
- `majorDimension`: ROWS or COLUMNS (default: ROWS)
- `valueRenderOption`: FORMATTED_VALUE, UNFORMATTED_VALUE, or FORMULA

#### 2. **spreadsheets.values.batchGet**
**Purpose:** Retrieve multiple ranges in a single request (efficient!)

**Endpoint:**
```
GET https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values:batchGet
```

**Example:**
```python
result = service.spreadsheets().values().batchGet(
    spreadsheetId='1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms',
    ranges=['Sheet1!A1:Z100', 'Sheet2!A1:Z100']
).execute()

for value_range in result.get('valueRanges', []):
    values = value_range.get('values', [])
```

#### 3. **spreadsheets.get**
**Purpose:** Get spreadsheet metadata (sheet names, properties)

**Endpoint:**
```
GET https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}
```

**Example:**
```python
spreadsheet = service.spreadsheets().get(
    spreadsheetId='1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
).execute()

sheets = spreadsheet.get('sheets', [])
for sheet in sheets:
    title = sheet['properties']['title']
    sheet_id = sheet['properties']['sheetId']
```

## 5. Rate Limits & Retry Strategy

### Rate Limits (Per-Minute Quotas)

| Limit Type | Project Limit | Per-User Limit |
|------------|---------------|----------------|
| **Read Requests** | 300/min | 60/min |
| **Write Requests** | 300/min | 60/min |

**Important Notes:**
- Quotas reset every 60 seconds
- **No daily limit** as long as you stay within per-minute quotas
- Service account requests count as a single user
- Read and write limits are tracked separately

### Additional Constraints

- **Request Timeout:** 180 seconds max processing time
- **Payload Size:** Recommended max 2 MB
- **No pagination needed:** Specify ranges directly

### Retry Strategy: Truncated Exponential Backoff

**Error to Retry:** `429 Too Many Requests`

**Algorithm:**
```python
import time
import random

def exponential_backoff_retry(func, max_retries=5):
    """Retry with exponential backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            return func()
        except HttpError as e:
            if e.resp.status == 429:  # Rate limit
                # Check for Retry-After header
                retry_after = e.resp.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    # Exponential backoff: min((2^n + random), 64)
                    wait_time = min(
                        (2 ** attempt) + random.uniform(0, 1),
                        64  # Maximum backoff
                    )
                
                print(f"Rate limited. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception(f"Failed after {max_retries} retries")
```

**HTTP Status Codes to Retry:**
- `408` - Request Timeout
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error
- `502` - Bad Gateway
- `503` - Service Unavailable

## 6. Pagination

### No Traditional Pagination Required

Google Sheets API uses **range-based data retrieval** instead of offset/cursor pagination.

**Strategy:** Split large sheets into chunks using A1 notation

```python
def read_sheet_in_batches(service, spreadsheet_id, sheet_name, batch_size=1000):
    """Read a sheet in batches to avoid timeouts."""
    offset = 1  # Start at row 1
    
    while True:
        range_name = f"{sheet_name}!A{offset}:Z{offset + batch_size - 1}"
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            break  # No more data
        
        yield values
        
        if len(values) < batch_size:
            break  # Last batch
        
        offset += batch_size
```

**Best Practices:**
- Default batch size: **200 rows** (Airbyte default)
- For wide sheets: Consider column limits (e.g., A:M instead of A:Z)
- Use `batchGet` for multiple sheets to reduce API calls

## 7. Error Handling

### Google Sheets Specific Error Codes

From `ErrorCode` enum:

| Error Code | Meaning | Solution |
|------------|---------|----------|
| `ERROR_CODE_UNSPECIFIED` | General API error | Check request format, retry |
| `DOCUMENT_TOO_LARGE_TO_EDIT` | Spreadsheet too large to modify | Make a copy, split data |
| `DOCUMENT_TOO_LARGE_TO_LOAD` | Spreadsheet too large to read | Make a copy, reduce data |

### HTTP Error Codes

| Code | Meaning | Handling Strategy |
|------|---------|-------------------|
| `400` | Bad Request | Invalid range, spreadsheet ID, or parameters |
| `401` | Unauthorized | Invalid/expired credentials - refresh auth |
| `403` | Forbidden | No spreadsheet access - check sharing permissions |
| `404` | Not Found | Invalid spreadsheet ID or sheet name |
| `429` | Too Many Requests | **Exponential backoff retry** |
| `500` | Internal Server Error | Retry with backoff (transient) |
| `503` | Service Unavailable | Retry with backoff (transient) |

### Implementation Example

```python
from googleapiclient.errors import HttpError

def safe_api_call(service, spreadsheet_id, range_name, max_retries=3):
    """Make API call with error handling."""
    for attempt in range(max_retries):
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
            
        except HttpError as e:
            error_code = e.resp.status
            
            if error_code == 403:
                raise Exception(
                    f"Permission denied. Share spreadsheet with service account."
                )
            
            elif error_code == 404:
                raise Exception(
                    f"Spreadsheet or range not found: {spreadsheet_id}"
                )
            
            elif error_code in [429, 500, 503]:
                if attempt < max_retries - 1:
                    wait = min((2 ** attempt) + random.uniform(0, 1), 32)
                    time.sleep(wait)
                    continue
                else:
                    raise
            
            else:
                raise
    
    raise Exception("Max retries exceeded")
```

## 8. Configuration Schema

### Minimal Configuration (JSON)

```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "credentials": {
    "type": "service_account",
    "project_id": "your-project",
    "private_key_id": "key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_email": "service-account@your-project.iam.gserviceaccount.com",
    "client_id": "12345",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
  }
}
```

### Extended Configuration (Airbyte-style)

```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "credentials": {
    "auth_type": "service_account",
    "service_account_info": "{...}"
  },
  "row_batch_size": 200,
  "names_conversion": true,
  "batch_size": 200
}
```

## 9. File Structure

### Recommended Connector Structure (Airbyte Pattern)

```
source-google-sheets/
├── source_google_sheets/
│   ├── __init__.py
│   ├── source.py              # Main source implementation
│   ├── client.py              # API client wrapper
│   ├── streams.py             # Stream definitions
│   ├── auth.py                # Authentication handlers
│   └── spec.yaml              # Configuration specification
├── unit_tests/
│   ├── test_source.py
│   ├── test_client.py
│   └── test_streams.py
├── integration_tests/
│   └── test_full_refresh.py
├── metadata.yaml              # Connector metadata
├── pyproject.toml             # Dependencies (Poetry)
└── README.md
```

### Key Files

**`source.py`** - Main connector class:
```python
class SourceGoogleSheets(AbstractSource):
    def check_connection(self, logger, config):
        # Verify credentials and spreadsheet access
        pass
    
    def streams(self, config):
        # Return list of stream objects (one per sheet)
        pass
```

**`streams.py`** - Stream implementation:
```python
class GoogleSheetsStream(HttpStream):
    def __init__(self, spreadsheet_id, sheet_name, credentials):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        # Initialize Google Sheets service
    
    def read_records(self):
        # Yield rows from the sheet
        pass
```

## 10. Python Code Example - Complete Working Implementation

```python
"""
Complete Google Sheets Source Connector Example
"""

import time
import random
from typing import List, Dict, Any, Iterator
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsClient:
    """Client for interacting with Google Sheets API v4."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self, service_account_file: str):
        """Initialize the client with service account credentials."""
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=self.SCOPES
        )
        self.service = build('sheets', 'v4', credentials=credentials)
    
    def get_spreadsheet_metadata(self, spreadsheet_id: str) -> Dict[str, Any]:
        """Get spreadsheet metadata including all sheet names."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            return spreadsheet
        except HttpError as e:
            if e.resp.status == 403:
                raise Exception(
                    f"Permission denied. Share spreadsheet {spreadsheet_id} "
                    f"with your service account email."
                )
            raise
    
    def get_sheet_names(self, spreadsheet_id: str) -> List[str]:
        """Extract all sheet names from a spreadsheet."""
        metadata = self.get_spreadsheet_metadata(spreadsheet_id)
        sheets = metadata.get('sheets', [])
        return [sheet['properties']['title'] for sheet in sheets]
    
    def read_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        batch_size: int = 200,
        max_retries: int = 5
    ) -> Iterator[List[List[Any]]]:
        """
        Read a sheet in batches with automatic retry on rate limits.
        
        Yields batches of rows.
        """
        offset = 1  # Start at row 1
        
        while True:
            # Define the range for this batch
            range_name = f"{sheet_name}!A{offset}:ZZ{offset + batch_size - 1}"
            
            # Read with retry logic
            values = self._read_range_with_retry(
                spreadsheet_id,
                range_name,
                max_retries
            )
            
            if not values:
                break  # No more data
            
            yield values
            
            if len(values) < batch_size:
                break  # Last batch
            
            offset += batch_size
    
    def _read_range_with_retry(
        self,
        spreadsheet_id: str,
        range_name: str,
        max_retries: int
    ) -> List[List[Any]]:
        """Read a range with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueRenderOption='UNFORMATTED_VALUE'  # Get raw values
                ).execute()
                
                return result.get('values', [])
                
            except HttpError as e:
                error_code = e.resp.status
                
                # Don't retry on client errors (except 429)
                if error_code == 404:
                    raise Exception(f"Sheet range not found: {range_name}")
                
                elif error_code == 403:
                    raise Exception("Permission denied. Check spreadsheet sharing.")
                
                # Retry on rate limits and server errors
                elif error_code in [429, 500, 503]:
                    if attempt < max_retries - 1:
                        wait_time = self._calculate_backoff(attempt, e.resp)
                        print(f"Rate limited (attempt {attempt + 1}/{max_retries}). "
                              f"Waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Max retries exceeded after {max_retries} attempts")
                
                else:
                    raise
        
        return []
    
    def _calculate_backoff(self, attempt: int, response) -> float:
        """Calculate exponential backoff with jitter."""
        # Check for Retry-After header
        retry_after = response.get('Retry-After')
        if retry_after:
            return int(retry_after)
        
        # Exponential backoff: min((2^n + random), 64)
        return min((2 ** attempt) + random.uniform(0, 1), 64)


# Example Usage
def main():
    """Example: Extract data from Google Sheets."""
    
    # Configuration
    SERVICE_ACCOUNT_FILE = 'path/to/service-account.json'
    SPREADSHEET_ID = '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
    
    # Initialize client
    client = GoogleSheetsClient(SERVICE_ACCOUNT_FILE)
    
    # Get all sheet names
    print("Discovering sheets...")
    sheet_names = client.get_sheet_names(SPREADSHEET_ID)
    print(f"Found {len(sheet_names)} sheets: {sheet_names}")
    
    # Read data from each sheet
    for sheet_name in sheet_names:
        print(f"\nReading sheet: {sheet_name}")
        
        row_count = 0
        for batch in client.read_sheet(SPREADSHEET_ID, sheet_name, batch_size=200):
            row_count += len(batch)
            
            # Process batch
            if row_count <= 200:  # Print first batch only
                for row in batch:
                    print(row)
        
        print(f"Total rows in '{sheet_name}': {row_count}")


if __name__ == "__main__":
    main()
```

### Installation Requirements

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Or with Poetry:
```toml
[tool.poetry.dependencies]
python = "^3.9"
google-auth = "^2.16.0"
google-auth-oauthlib = "^1.0.0"
google-auth-httplib2 = "^0.1.0"
google-api-python-client = "^2.70.0"
```

## 11. Known Issues & Limitations

### API Limitations

1. **Single Spreadsheet Per Connector**
   - Airbyte connector limited to one spreadsheet
   - For multiple spreadsheets, use multiple connector instances or Google Drive connector

2. **Document Size Limits**
   - Very large spreadsheets (>5M cells) may hit `DOCUMENT_TOO_LARGE` errors
   - Solution: Split data or make a copy

3. **Grid Sheets Only**
   - Only supports "Grid" sheet types
   - Charts, pivot tables, and other sheet types are not synced

4. **Data Type Handling**
   - All data typically extracted as strings
   - Type inference required in downstream processing
   - Dates may need format conversion

5. **Request Timeout**
   - 180-second max processing time per request
   - For large ranges, break into smaller batches

### Authentication Gotchas

1. **Service Account Sharing**
   - Must explicitly share spreadsheet with service account email
   - Common error: 403 Forbidden if not shared

2. **API Enablement**
   - Both Google Sheets API **and** Google Drive API must be enabled
   - Drive API needed because Sheets are stored in Drive

3. **Scope Permissions**
   - Use `.readonly` scope for source connectors
   - Full scope grants write access (unnecessary risk)

### Performance Considerations

1. **Rate Limits**
   - 60 requests/min per user is the most common bottleneck
   - Service accounts count as one user
   - Solution: Implement proper backoff

2. **Batch Size Tuning**
   - Default 200 rows works for most cases
   - Wider sheets: reduce batch size
   - Narrow sheets: can increase to 500-1000 rows

3. **Column Limits**
   - Google Sheets supports up to 18,278 columns (ZZZ)
   - Most connectors limit to A:ZZ (676 columns) for performance

## 12. References

### Official Documentation
- [Google Sheets API v4 Overview](https://developers.google.com/workspace/sheets/api/reference/rest)
- [Usage Limits & Quotas](https://developers.google.com/workspace/sheets/api/limits)
- [Python Quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python)
- [Error Code Reference](https://developers.google.com/sheets/api/reference/rest/v4/ErrorCode)
- [Method: spreadsheets.values.get](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/get)
- [Method: spreadsheets.values.batchGet](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchGet)

### Open Source Implementations
- [Airbyte source-google-sheets](https://github.com/airbytehq/airbyte/tree/master/airbyte-integrations/connectors/source-google-sheets)
- [Airbyte Documentation](https://github.com/airbytehq/airbyte/blob/master/docs/integrations/sources/google-sheets.md)
- [Meltano tap-google-sheets](https://hub.meltano.com/extractors/tap-google-sheets--airbyte/)

### Python Libraries
- [google-auth](https://pypi.org/project/google-auth/) - Authentication
- [google-api-python-client](https://pypi.org/project/google-api-python-client/) - API client
- [gspread](https://docs.gspread.org/) - Alternative higher-level library

### Best Practices Articles
- [Exponential Backoff](https://cloud.google.com/storage/docs/retry-strategy)
- [Service Account Authentication Guide](https://denisluiz.medium.com/python-with-google-sheets-service-account-step-by-step-8f74c26ed28e)

---

**Last Updated:** 2025 (API v4 stable)