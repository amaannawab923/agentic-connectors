Now I have all the information needed. Let me compile the comprehensive research document.

# Google Sheets Source Connector Research

## 1. Executive Summary

Google Sheets API v4 provides RESTful access to spreadsheet data with support for OAuth 2.0 and service account authentication. The API has per-minute rate limits (300 requests/minute per project, 60 per user) with no daily limits, making it suitable for batch data extraction. Existing implementations in Airbyte use a low-level CDK approach with batch row fetching for efficient data retrieval.

## 2. Authentication

Google Sheets API supports three authentication methods:

### Service Account (Recommended for Connectors)
Best for automated/server-side applications. Requires sharing the spreadsheet with the service account email.

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

credentials = service_account.Credentials.from_service_account_file(
    'service-account.json', 
    scopes=SCOPES
)
service = build('sheets', 'v4', credentials=credentials)
```

### OAuth 2.0 (For User-Delegated Access)
Best when accessing user's personal spreadsheets.

```python
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return creds

service = build("sheets", "v4", credentials=get_credentials())
```

### API Key (Read-Only Public Sheets)
Only works for publicly accessible spreadsheets.

```python
from googleapiclient.discovery import build

service = build('sheets', 'v4', developerKey='YOUR_API_KEY')
```

## 3. Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `spreadsheets.get` | GET | Get spreadsheet metadata (sheets, properties) |
| `spreadsheets.values.get` | GET | Read values from a single range |
| `spreadsheets.values.batchGet` | GET | Read values from multiple ranges |
| `spreadsheets.getByDataFilter` | POST | Get spreadsheet data matching filters |

### Key API Calls

```python
# Get spreadsheet metadata (sheet names, properties)
spreadsheet = service.spreadsheets().get(
    spreadsheetId=SPREADSHEET_ID
).execute()

# Get all values from a sheet
result = service.spreadsheets().values().get(
    spreadsheetId=SPREADSHEET_ID,
    range='Sheet1'  # or 'Sheet1!A1:Z1000'
).execute()
values = result.get('values', [])

# Batch get multiple ranges
result = service.spreadsheets().values().batchGet(
    spreadsheetId=SPREADSHEET_ID,
    ranges=['Sheet1!A1:B10', 'Sheet2!A1:C20']
).execute()
```

## 4. Rate Limits

| Limit Type | Per Project | Per User |
|------------|-------------|----------|
| Read Requests | 300/minute | 60/minute |
| Write Requests | 300/minute | 60/minute |
| Request Timeout | 180 seconds | - |
| Recommended Payload | 2 MB max | - |

**No daily limits** as long as per-minute quotas are respected.

### Retry Strategy with Exponential Backoff

```python
import time
import random
from googleapiclient.errors import HttpError

def execute_with_backoff(request, max_retries=5):
    """Execute API request with exponential backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status == 429:  # Rate limit exceeded
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limited. Waiting {wait_time:.2f}s...")
                time.sleep(wait_time)
            elif e.resp.status in [500, 503]:  # Server errors
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                raise
    raise Exception(f"Max retries ({max_retries}) exceeded")
```

## 5. Pagination

Google Sheets API doesn't use cursor-based pagination. Instead, use range-based fetching:

```python
def fetch_sheet_in_batches(service, spreadsheet_id, sheet_name, batch_size=1000):
    """Fetch large sheets in batches using range-based pagination."""
    all_values = []
    start_row = 1
    
    while True:
        range_name = f"{sheet_name}!A{start_row}:{start_row + batch_size - 1}"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            break
            
        all_values.extend(values)
        
        # If we got fewer rows than requested, we've reached the end
        if len(values) < batch_size:
            break
            
        start_row += batch_size
    
    return all_values
```

**Airbyte approach**: Uses `row_batch_size` configuration (default: 200 rows) per API call.

## 6. Error Handling

| Error Code | Description | Action |
|------------|-------------|--------|
| 400 | Bad Request (invalid range, etc.) | Fix request parameters |
| 401 | Invalid credentials | Re-authenticate |
| 403 | Forbidden (no access to spreadsheet) | Check sharing permissions |
| 404 | Spreadsheet not found | Verify spreadsheet ID |
| 429 | Rate limit exceeded | Exponential backoff |
| 500/503 | Server error | Retry with backoff |

```python
from googleapiclient.errors import HttpError

def handle_sheets_error(error: HttpError):
    """Handle Google Sheets API errors."""
    status = error.resp.status
    
    if status == 400:
        raise ValueError(f"Invalid request: {error}")
    elif status == 401:
        raise PermissionError("Invalid or expired credentials")
    elif status == 403:
        raise PermissionError("No access to spreadsheet. Check sharing settings.")
    elif status == 404:
        raise FileNotFoundError("Spreadsheet not found. Check spreadsheet ID.")
    elif status == 429:
        return "RATE_LIMITED"  # Signal for retry
    elif status in [500, 503]:
        return "SERVER_ERROR"  # Signal for retry
    else:
        raise error
```

## 7. Python Code Example - Complete Connector

```python
"""Google Sheets Source Connector - Core Implementation"""

import os
import time
import random
from typing import Iterator, Dict, Any, List, Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsConnector:
    """Production-ready Google Sheets source connector."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(
        self,
        spreadsheet_id: str,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[Dict] = None,
        oauth_token: Optional[Dict] = None,
        batch_size: int = 200
    ):
        self.spreadsheet_id = spreadsheet_id
        self.batch_size = batch_size
        self.service = self._build_service(
            credentials_path, credentials_json, oauth_token
        )
    
    def _build_service(
        self,
        credentials_path: Optional[str],
        credentials_json: Optional[Dict],
        oauth_token: Optional[Dict]
    ):
        """Build Google Sheets API service with appropriate credentials."""
        if credentials_json:
            # Service account from dict
            creds = service_account.Credentials.from_service_account_info(
                credentials_json, scopes=self.SCOPES
            )
        elif credentials_path:
            # Service account from file
            creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=self.SCOPES
            )
        elif oauth_token:
            # OAuth2 token
            creds = Credentials.from_authorized_user_info(
                oauth_token, scopes=self.SCOPES
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        else:
            raise ValueError("Must provide credentials_path, credentials_json, or oauth_token")
        
        return build('sheets', 'v4', credentials=creds)
    
    def _execute_with_backoff(self, request, max_retries: int = 5):
        """Execute API request with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status in [429, 500, 503]:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                else:
                    raise
    
    def check_connection(self) -> bool:
        """Verify connection to the spreadsheet."""
        try:
            self._execute_with_backoff(
                self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id)
            )
            return True
        except HttpError as e:
            raise ConnectionError(f"Failed to connect: {e}")
    
    def discover_streams(self) -> List[Dict[str, Any]]:
        """Discover available sheets and their schemas."""
        spreadsheet = self._execute_with_backoff(
            self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id)
        )
        
        streams = []
        for sheet in spreadsheet.get('sheets', []):
            sheet_name = sheet['properties']['title']
            
            # Get header row to infer schema
            result = self._execute_with_backoff(
                self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{sheet_name}'!1:1"
                )
            )
            
            headers = result.get('values', [[]])[0] if result.get('values') else []
            
            streams.append({
                'name': sheet_name,
                'schema': {
                    'type': 'object',
                    'properties': {h: {'type': 'string'} for h in headers}
                },
                'headers': headers
            })
        
        return streams
    
    def read_stream(self, sheet_name: str) -> Iterator[Dict[str, Any]]:
        """Read all rows from a sheet as records."""
        # First, get headers
        header_result = self._execute_with_backoff(
            self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{sheet_name}'!1:1"
            )
        )
        headers = header_result.get('values', [[]])[0]
        
        if not headers:
            return
        
        # Fetch data in batches
        start_row = 2  # Skip header row
        
        while True:
            end_row = start_row + self.batch_size - 1
            range_name = f"'{sheet_name}'!A{start_row}:{end_row}"
            
            result = self._execute_with_backoff(
                self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                )
            )
            
            rows = result.get('values', [])
            if not rows:
                break
            
            for row in rows:
                # Pad row if it has fewer columns than headers
                padded_row = row + [''] * (len(headers) - len(row))
                record = dict(zip(headers, padded_row[:len(headers)]))
                yield record
            
            if len(rows) < self.batch_size:
                break
                
            start_row += self.batch_size


# Usage Example
if __name__ == "__main__":
    connector = GoogleSheetsConnector(
        spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        credentials_path="service-account.json",
        batch_size=200
    )
    
    # Check connection
    connector.check_connection()
    
    # Discover available sheets
    streams = connector.discover_streams()
    print(f"Found {len(streams)} sheets")
    
    # Read data from first sheet
    for stream in streams:
        print(f"\nReading: {stream['name']}")
        for i, record in enumerate(connector.read_stream(stream['name'])):
            print(record)
            if i >= 5:  # Limit output for demo
                break
```

## 8. Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["spreadsheet_id", "credentials"],
  "properties": {
    "spreadsheet_id": {
      "type": "string",
      "description": "The ID of the Google Spreadsheet (from URL)",
      "pattern": "^[a-zA-Z0-9-_]+$"
    },
    "credentials": {
      "oneOf": [
        {
          "type": "object",
          "title": "Service Account",
          "required": ["auth_type", "service_account_info"],
          "properties": {
            "auth_type": { "const": "service_account" },
            "service_account_info": {
              "type": "string",
              "description": "Service account JSON key (as string)"
            }
          }
        },
        {
          "type": "object", 
          "title": "OAuth2",
          "required": ["auth_type", "client_id", "client_secret", "refresh_token"],
          "properties": {
            "auth_type": { "const": "oauth2" },
            "client_id": { "type": "string" },
            "client_secret": { "type": "string" },
            "refresh_token": { "type": "string" }
          }
        }
      ]
    },
    "row_batch_size": {
      "type": "integer",
      "default": 200,
      "minimum": 1,
      "maximum": 1000,
      "description": "Number of rows to fetch per API request"
    }
  }
}
```

## 9. File Structure

```
source-google-sheets/
├── src/
│   └── source_google_sheets/
│       ├── __init__.py
│       ├── source.py           # Main connector implementation
│       ├── client.py           # Google Sheets API client wrapper
│       ├── auth.py             # Authentication handlers
│       └── schemas.py          # Pydantic models for config
├── tests/
│   ├── unit/
│   │   ├── test_client.py
│   │   └── test_auth.py
│   └── integration/
│       └── test_source.py
├── pyproject.toml
├── README.md
└── metadata.yaml
```

## 10. References

- [Google Sheets API Usage Limits](https://developers.google.com/workspace/sheets/api/limits) - Official rate limits documentation
- [Google Sheets API Python Quickstart](https://developers.google.com/workspace/sheets/api/quickstart/python) - Official Python setup guide
- [Airbyte source-google-sheets](https://github.com/airbytehq/airbyte/tree/master/airbyte-integrations/connectors/source-google-sheets) - Reference implementation
- [gspread Authentication](https://docs.gspread.org/en/latest/oauth2.html) - Alternative Python library docs
- [Google Sheets API Limits Guide](https://stateful.com/blog/google-sheets-api-limits) - Practical limits guide
- [airbyte-source-google-sheets on PyPI](https://pypi.org/project/airbyte-source-google-sheets/) - Published connector package
- [Meltano tap-google-sheets](https://hub.meltano.com/extractors/tap-google-sheets--airbyte/) - Meltano variant documentation