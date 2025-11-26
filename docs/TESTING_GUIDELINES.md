# Connector Testing Guidelines

This document provides comprehensive guidelines for testing generated connectors. These patterns ensure reliable, reproducible tests that work with various API client libraries.

## Table of Contents

1. [Core Testing Principles](#core-testing-principles)
2. [HTTP-Level Mocking](#http-level-mocking)
3. [Why Not Client-Level Mocking](#why-not-client-level-mocking)
4. [Authentication Mocking](#authentication-mocking)
5. [Test Structure](#test-structure)
6. [Common Patterns by API Type](#common-patterns-by-api-type)
7. [Virtual Environment Setup](#virtual-environment-setup)
8. [Troubleshooting](#troubleshooting)

---

## Core Testing Principles

### 1. Always Use HTTP-Level Mocking

**Use `httpretty` or `responses` library** to intercept HTTP requests at the socket level. This works with ALL HTTP client libraries including:
- `requests`
- `httplib2` (used by Google API clients)
- `urllib3`
- `aiohttp`

**Never use** `unittest.mock.patch` to mock API client constructors directly (e.g., `patch('googleapiclient.discovery.build')`).

### 2. Always Use Virtual Environments

Every connector should have its own virtual environment:
```bash
cd connector-directory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install httpretty pytest
```

### 3. Mock All External Endpoints

Mock every HTTP endpoint the connector touches:
- OAuth2 token endpoints
- API discovery endpoints (for Google APIs)
- Actual API data endpoints

---

## HTTP-Level Mocking

### Using httpretty (Recommended)

`httpretty` works at the socket level and intercepts ALL HTTP traffic, regardless of which HTTP client library is used.

```python
import httpretty
import json
import re

def setup_httpretty_mocks():
    """Setup HTTP-level mocks for API testing."""
    # Enable httpretty - blocks all external HTTP calls
    httpretty.enable(verbose=True, allow_net_connect=False)

    # Mock endpoints using regex for dynamic paths
    httpretty.register_uri(
        httpretty.GET,
        re.compile(r"https://api\.example\.com/v1/resources/[^/]+$"),
        body=json.dumps({"id": "123", "name": "Test Resource"}),
        content_type="application/json"
    )

    # Mock POST endpoints
    httpretty.register_uri(
        httpretty.POST,
        "https://api.example.com/v1/resources",
        body=json.dumps({"id": "456", "created": True}),
        content_type="application/json",
        status=201
    )

def cleanup_httpretty():
    """Clean up httpretty after tests."""
    httpretty.disable()
    httpretty.reset()
```

### Key httpretty Features

1. **Regex URL Matching**: Use `re.compile()` for dynamic URL paths
2. **Multiple Response Bodies**: Return different responses for sequential calls
3. **Request Inspection**: Access `httpretty.last_request()` to verify request data
4. **Verbose Mode**: Enable `verbose=True` for debugging

---

## Why Not Client-Level Mocking

### The Problem

When you mock at the client level:
```python
# DON'T DO THIS
with patch('googleapiclient.discovery.build') as mock_build:
    mock_service = MagicMock()
    mock_build.return_value = mock_service
```

**Issues:**
1. `MagicMock` objects return `MagicMock` for all attribute access
2. Properties like `universe_domain` return `MagicMock` instead of strings
3. Internal validation in API clients fails
4. Doesn't test actual HTTP serialization/deserialization

### Real Error Example

```
ValueError: universe_domain must be a string; got <MagicMock ...>
```

This happens because Google's API client validates `universe_domain` is a string, but `MagicMock.universe_domain` returns another `MagicMock`.

### The Solution

HTTP-level mocking lets the actual client library work normally - it just intercepts the final HTTP requests:

```python
# DO THIS INSTEAD
import httpretty

httpretty.enable()
httpretty.register_uri(
    httpretty.GET,
    "https://sheets.googleapis.com/v4/spreadsheets/test-id",
    body=json.dumps({"spreadsheetId": "test-id", ...}),
    content_type="application/json"
)

# Now the real client works, but HTTP calls are intercepted
service = build('sheets', 'v4', credentials=creds)
result = service.spreadsheets().get(spreadsheetId='test-id').execute()
```

---

## Authentication Mocking

### OAuth2 Token Endpoint

Always mock the OAuth2 token endpoint for service account authentication:

```python
MOCK_OAUTH_TOKEN = {
    "access_token": "mock-access-token-12345",
    "token_type": "Bearer",
    "expires_in": 3600
}

httpretty.register_uri(
    httpretty.POST,
    "https://oauth2.googleapis.com/token",
    body=json.dumps(MOCK_OAUTH_TOKEN),
    content_type="application/json"
)
```

### Valid Private Keys for Testing

Google's service account validation requires valid PEM-format private keys. **Invalid keys will fail validation before any HTTP calls are made.**

#### Generate a Valid Test Key

```bash
openssl genpkey -algorithm RSA -out test_private_key.pem -pkeyopt rsa_keygen_bits:2048
```

#### Key Format Requirements

Use PKCS#8 format (`-----BEGIN PRIVATE KEY-----`), NOT PKCS#1 format (`-----BEGIN RSA PRIVATE KEY-----`):

```python
# CORRECT - PKCS#8 format
VALID_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCvXqQH1TGUswJg
ah/dHw+6e1ynQz7G0bB3FpuGRAGhdStLcXoBYe65g7x8Pga3AWH2Vqs0snGESIDE
...
-----END PRIVATE KEY-----"""

# WRONG - PKCS#1 format (may not work with all libraries)
WRONG_FORMAT = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""
```

---

## Test Structure

### Recommended Test File Structure

```python
#!/usr/bin/env python3
"""
Connector Integration Tests with HTTP Mocking

Uses httpretty for HTTP-level mocking to test connector functionality
without making actual API calls.
"""

import json
import sys
import os
import subprocess
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ============================================================
# MOCK DATA
# ============================================================

VALID_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
... (valid RSA key) ...
-----END PRIVATE KEY-----"""

MOCK_OAUTH_TOKEN = {
    "access_token": "mock-access-token",
    "token_type": "Bearer",
    "expires_in": 3600
}

MOCK_API_RESPONSE = {
    # Your API-specific mock data
}

# ============================================================
# TEST CONFIGURATION
# ============================================================

def get_test_config():
    """Return test configuration for the connector."""
    return {
        "credentials": {
            "type": "service_account",
            "private_key": VALID_PRIVATE_KEY,
            # ... other fields
        },
        # ... other config
    }

# ============================================================
# HTTPRETTY SETUP
# ============================================================

def setup_httpretty_mocks():
    """Setup all HTTP mocks."""
    import httpretty

    httpretty.enable(verbose=True, allow_net_connect=False)

    # Mock OAuth
    httpretty.register_uri(
        httpretty.POST,
        "https://oauth2.googleapis.com/token",
        body=json.dumps(MOCK_OAUTH_TOKEN),
        content_type="application/json"
    )

    # Mock API endpoints
    # ... add your mocks

def cleanup_httpretty():
    """Clean up httpretty."""
    import httpretty
    httpretty.disable()
    httpretty.reset()

# ============================================================
# TESTS
# ============================================================

def test_syntax_validation():
    """Test 1: Syntax validation."""
    # ... implementation

def test_import_validation():
    """Test 2: Import validation."""
    # ... implementation

def test_connection_check():
    """Test 3: Connection check with mocked HTTP."""
    setup_httpretty_mocks()
    try:
        # Test code
        pass
    finally:
        cleanup_httpretty()

def test_schema_discovery():
    """Test 4: Schema discovery."""
    setup_httpretty_mocks()
    try:
        # Test code
        pass
    finally:
        cleanup_httpretty()

def test_data_reading():
    """Test 5: Data reading."""
    setup_httpretty_mocks()
    try:
        # Test code
        pass
    finally:
        cleanup_httpretty()

# ============================================================
# MAIN
# ============================================================

def main():
    """Run all tests and output JSON results."""
    results = {
        "status": "passed",
        "passed": True,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "errors": [],
        "logs": ""
    }

    tests = [
        ("Syntax Validation", test_syntax_validation),
        ("Import Validation", test_import_validation),
        ("Connection Check", test_connection_check),
        ("Schema Discovery", test_schema_discovery),
        ("Data Reading", test_data_reading),
    ]

    for name, test_func in tests:
        results["tests_run"] += 1
        try:
            test_func()
            results["tests_passed"] += 1
            results["logs"] += f"PASS: {name}\n"
        except Exception as e:
            results["tests_failed"] += 1
            results["errors"].append(f"{name}: {str(e)}")
            results["logs"] += f"FAIL: {name} - {str(e)}\n"

    results["passed"] = results["tests_failed"] == 0
    results["status"] = "passed" if results["passed"] else "failed"

    print(json.dumps(results, indent=2))
    return 0 if results["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## Authentication Pattern Selection

Before writing tests, identify the authentication type used by the connector:

| Auth Type | When to Use | Example APIs |
|-----------|-------------|--------------|
| **Google Service Account** | Google APIs with service account JSON | Sheets, Drive, Analytics, BigQuery |
| **API Key** | Simple key in header/query param | Stripe, SendGrid, Twilio, OpenWeather |
| **OAuth2** | Token refresh flow | Salesforce, HubSpot, Slack, GitHub |
| **Basic Auth** | Username/password | Jira, Jenkins, some legacy APIs |

---

## Common Patterns by API Type

### Google APIs (Sheets, Drive, etc.)

Google APIs use `httplib2` and require discovery document mocking:

```python
# Mock discovery document
DISCOVERY_DOC = {
    "kind": "discovery#restDescription",
    "discoveryVersion": "v1",
    "id": "sheets:v4",
    "name": "sheets",
    "version": "v4",
    "baseUrl": "https://sheets.googleapis.com/",
    "rootUrl": "https://sheets.googleapis.com/",
    "servicePath": "",
    "batchPath": "batch",
    "parameters": {},
    "schemas": {},
    "resources": {
        "spreadsheets": {
            "methods": {
                "get": {
                    "id": "sheets.spreadsheets.get",
                    "path": "v4/spreadsheets/{spreadsheetId}",
                    "httpMethod": "GET",
                    "parameters": {
                        "spreadsheetId": {
                            "type": "string",
                            "required": True,
                            "location": "path"
                        }
                    },
                    "response": {"$ref": "Spreadsheet"}
                }
            },
            "resources": {
                "values": {
                    "methods": {
                        "get": {
                            "id": "sheets.spreadsheets.values.get",
                            "path": "v4/spreadsheets/{spreadsheetId}/values/{range}",
                            "httpMethod": "GET",
                            "parameters": {
                                "spreadsheetId": {"type": "string", "required": True, "location": "path"},
                                "range": {"type": "string", "required": True, "location": "path"}
                            },
                            "response": {"$ref": "ValueRange"}
                        }
                    }
                }
            }
        }
    }
}

httpretty.register_uri(
    httpretty.GET,
    "https://sheets.discovery.googleapis.com/discovery/v1/apis/sheets/v4/rest",
    body=json.dumps(DISCOVERY_DOC),
    content_type="application/json"
)

# Also mock the alternative discovery URL
httpretty.register_uri(
    httpretty.GET,
    "https://www.googleapis.com/discovery/v1/apis/sheets/v4/rest",
    body=json.dumps(DISCOVERY_DOC),
    content_type="application/json"
)
```

### API Key Authentication (Stripe, SendGrid, etc.)

Simple APIs using API key authentication:

```python
def get_test_config():
    return {
        "api_key": "test_api_key_sk_12345",
    }

def setup_httpretty_mocks():
    httpretty.enable(verbose=True, allow_net_connect=False)

    # No OAuth mock needed - just mock API endpoints
    httpretty.register_uri(
        httpretty.GET,
        re.compile(r"https://api\.stripe\.com/v1/.*"),
        body=json.dumps({
            "object": "list",
            "data": [{"id": "cus_123", "email": "test@example.com"}],
            "has_more": False
        }),
        content_type="application/json"
    )
```

### OAuth2 APIs (Salesforce, HubSpot, etc.)

APIs requiring OAuth2 token refresh:

```python
def get_test_config():
    return {
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "refresh_token": "test-refresh-token",
    }

def setup_httpretty_mocks():
    httpretty.enable(verbose=True, allow_net_connect=False)

    # Mock token refresh endpoint
    httpretty.register_uri(
        httpretty.POST,
        "https://login.salesforce.com/services/oauth2/token",
        body=json.dumps({
            "access_token": "mock-access-token",
            "token_type": "Bearer",
            "instance_url": "https://test.salesforce.com"
        }),
        content_type="application/json"
    )

    # Mock API endpoints
    httpretty.register_uri(
        httpretty.GET,
        re.compile(r"https://.*\.salesforce\.com/services/data/.*"),
        body=json.dumps({"records": [...]}),
        content_type="application/json"
    )
```

### Basic Auth APIs (Jira, etc.)

Simple username/password authentication:

```python
def get_test_config():
    return {
        "username": "test_user",
        "password": "test_password",
        "base_url": "https://company.atlassian.net"
    }

def setup_httpretty_mocks():
    httpretty.enable(verbose=True, allow_net_connect=False)

    # No OAuth mock needed - httpretty handles Basic auth headers
    httpretty.register_uri(
        httpretty.GET,
        re.compile(r"https://company\.atlassian\.net/rest/api/.*"),
        body=json.dumps({"issues": [...]}),
        content_type="application/json"
    )
```

### APIs with Pagination

```python
# First page
httpretty.register_uri(
    httpretty.GET,
    re.compile(r"https://api\.example\.com/v1/items\?page=1"),
    body=json.dumps({
        "items": [{"id": 1}],
        "next_page": 2
    }),
    content_type="application/json"
)

# Second page
httpretty.register_uri(
    httpretty.GET,
    re.compile(r"https://api\.example\.com/v1/items\?page=2"),
    body=json.dumps({
        "items": [{"id": 2}],
        "next_page": None
    }),
    content_type="application/json"
)
```

---

## Virtual Environment Setup

### Setup Script

```bash
#!/bin/bash
# setup_test_env.sh

CONNECTOR_DIR="$1"

if [ -z "$CONNECTOR_DIR" ]; then
    echo "Usage: ./setup_test_env.sh /path/to/connector"
    exit 1
fi

cd "$CONNECTOR_DIR"

# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install connector dependencies
pip install -r requirements.txt

# Install test dependencies
pip install httpretty pytest

echo "Virtual environment ready. Activate with:"
echo "  source $CONNECTOR_DIR/venv/bin/activate"
```

### Running Tests

```bash
cd connector-directory
source venv/bin/activate
python tests/test_qa_final.py
```

---

## Troubleshooting

### Common Issues

#### 1. "externally-managed-environment" Error

**Problem**: macOS/Linux system Python refuses pip install.

**Solution**: Always use a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install httpretty
```

#### 2. "Invalid private key format" Error

**Problem**: Service account validation fails.

**Solution**: Generate a valid RSA key:
```bash
openssl genpkey -algorithm RSA -out test_key.pem -pkeyopt rsa_keygen_bits:2048
```

Then read and use it:
```python
with open('test_key.pem', 'r') as f:
    VALID_PRIVATE_KEY = f.read()
```

#### 3. "universe_domain must be a string" Error

**Problem**: Using `unittest.mock` to mock Google API client.

**Solution**: Switch to HTTP-level mocking with `httpretty`.

#### 4. "Connection refused" or Timeout Errors

**Problem**: `httpretty` not intercepting requests.

**Solution**:
1. Ensure `httpretty.enable()` is called before any imports that create HTTP clients
2. Use `allow_net_connect=False` to catch unmocked endpoints
3. Check URL patterns match exactly (use regex for dynamic paths)

#### 5. SSL Certificate Errors

**Problem**: Some libraries validate SSL even with mocking.

**Solution**: httpretty handles this automatically. If issues persist, check you're mocking the correct URL (http vs https).

---

## Required Test Dependencies

Add to `requirements.txt` or install separately:

```
httpretty>=1.1.4
pytest>=7.0.0
```

---

## Summary Checklist

Before writing connector tests:

- [ ] Create virtual environment
- [ ] Install `httpretty` and `pytest`
- [ ] Generate valid RSA private key (PKCS#8 format)
- [ ] Mock OAuth2 token endpoint
- [ ] Mock API discovery endpoint (for Google APIs)
- [ ] Mock all API data endpoints with realistic responses
- [ ] Use regex patterns for dynamic URL paths
- [ ] Always cleanup httpretty after tests
- [ ] Output JSON results in the expected format

---

*Last Updated: November 25, 2025*
*Based on learnings from Google Sheets connector testing*
