"""
Utility functions and custom exceptions for Google Sheets connector.

This module provides:
- Custom exception classes for error handling
- Helper functions for data transformation
- A1 notation utilities
"""

from typing import Any, Dict, List, Optional, Tuple
import re
from datetime import datetime


# =============================================================================
# Custom Exceptions
# =============================================================================

class GoogleSheetsError(Exception):
    """Base exception for Google Sheets connector errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(GoogleSheetsError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class RateLimitError(GoogleSheetsError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None
    ):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class NotFoundError(GoogleSheetsError):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class InvalidRequestError(GoogleSheetsError):
    """Raised when the request is invalid."""

    def __init__(self, message: str = "Invalid request"):
        super().__init__(message, status_code=400)


class ConnectionError(GoogleSheetsError):
    """Raised when connection to the API fails."""

    def __init__(self, message: str = "Connection failed"):
        super().__init__(message, status_code=None)


class ServerError(GoogleSheetsError):
    """Raised when the server returns an error."""

    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message, status_code=status_code)


# =============================================================================
# A1 Notation Utilities
# =============================================================================

def column_number_to_letter(column_number: int) -> str:
    """
    Convert a column number to A1 notation letter(s).

    Args:
        column_number: 1-indexed column number

    Returns:
        Column letter(s) in A1 notation (e.g., 'A', 'Z', 'AA', 'AZ')

    Examples:
        >>> column_number_to_letter(1)
        'A'
        >>> column_number_to_letter(26)
        'Z'
        >>> column_number_to_letter(27)
        'AA'
    """
    result = ""
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def column_letter_to_number(column_letter: str) -> int:
    """
    Convert A1 notation letter(s) to a column number.

    Args:
        column_letter: Column letter(s) in A1 notation

    Returns:
        1-indexed column number

    Examples:
        >>> column_letter_to_number('A')
        1
        >>> column_letter_to_number('Z')
        26
        >>> column_letter_to_number('AA')
        27
    """
    result = 0
    for char in column_letter.upper():
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result


def build_range_notation(
    sheet_name: str,
    start_row: Optional[int] = None,
    end_row: Optional[int] = None,
    start_col: Optional[str] = None,
    end_col: Optional[str] = None
) -> str:
    """
    Build A1 notation range string for a sheet.

    Args:
        sheet_name: Name of the sheet
        start_row: Starting row number (1-indexed)
        end_row: Ending row number (1-indexed)
        start_col: Starting column letter
        end_col: Ending column letter

    Returns:
        A1 notation range string

    Examples:
        >>> build_range_notation("Sheet1")
        "'Sheet1'"
        >>> build_range_notation("Sheet1", start_row=1, end_row=100)
        "'Sheet1'!1:100"
        >>> build_range_notation("Sheet1", start_row=1, start_col="A", end_col="Z")
        "'Sheet1'!A1:Z"
    """
    # Escape sheet name with single quotes
    escaped_name = f"'{sheet_name}'"

    # Build range part
    if start_row is None and start_col is None:
        return escaped_name

    range_parts = []

    # Start cell
    start_cell = ""
    if start_col:
        start_cell += start_col
    if start_row:
        start_cell += str(start_row)

    # End cell
    end_cell = ""
    if end_col:
        end_cell += end_col
    if end_row:
        end_cell += str(end_row)

    if start_cell and end_cell:
        return f"{escaped_name}!{start_cell}:{end_cell}"
    elif start_cell:
        return f"{escaped_name}!{start_cell}"
    else:
        return escaped_name


def parse_range_notation(range_notation: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse A1 notation range string.

    Args:
        range_notation: A1 notation range string

    Returns:
        Tuple of (sheet_name, start_cell, end_cell)
    """
    # Handle quoted sheet names
    if range_notation.startswith("'"):
        # Find the closing quote
        end_quote = range_notation.find("'", 1)
        if end_quote == -1:
            raise InvalidRequestError(f"Invalid range notation: {range_notation}")

        sheet_name = range_notation[1:end_quote]
        remainder = range_notation[end_quote + 1:]
    else:
        # Sheet name before !
        parts = range_notation.split("!", 1)
        sheet_name = parts[0]
        remainder = "!" + parts[1] if len(parts) > 1 else ""

    if not remainder or remainder == "!":
        return sheet_name, None, None

    # Parse range part (after !)
    range_part = remainder[1:] if remainder.startswith("!") else remainder

    if ":" in range_part:
        start_cell, end_cell = range_part.split(":", 1)
        return sheet_name, start_cell, end_cell
    else:
        return sheet_name, range_part, None


# =============================================================================
# Data Transformation Utilities
# =============================================================================

def sanitize_column_name(name: str) -> str:
    """
    Sanitize a column name for use as a field name.

    Args:
        name: Original column name

    Returns:
        Sanitized column name
    """
    if not name:
        return "unnamed_column"

    # Replace special characters with underscores
    sanitized = re.sub(r'[^\w\s]', '_', name)

    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')

    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"col_{sanitized}"

    return sanitized.lower() or "unnamed_column"


def infer_type_from_value(value: Any) -> str:
    """
    Infer JSON schema type from a Python value.

    Args:
        value: The value to analyze

    Returns:
        JSON schema type string
    """
    if value is None or value == "":
        return "null"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "number"

    if isinstance(value, str):
        # Try to parse as number
        try:
            float(value)
            return "number"
        except (ValueError, TypeError):
            pass

        # Try to parse as boolean
        if value.lower() in ("true", "false"):
            return "boolean"

        # Try to parse as date/datetime
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # ISO date
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO datetime
            r'^\d{1,2}/\d{1,2}/\d{4}$',  # US date
            r'^\d{1,2}-\d{1,2}-\d{4}$',  # EU date
        ]
        for pattern in date_patterns:
            if re.match(pattern, value):
                return "string"  # Keep as string but could be datetime

        return "string"

    return "string"


def infer_schema_from_data(
    headers: List[str],
    sample_data: List[List[Any]],
    sample_size: int = 100
) -> Dict[str, Any]:
    """
    Infer JSON schema from headers and sample data.

    Args:
        headers: List of column headers
        sample_data: Sample rows of data
        sample_size: Number of rows to sample for type inference

    Returns:
        JSON schema dictionary
    """
    properties = {}

    # Limit sample size
    sample_rows = sample_data[:sample_size]

    for col_idx, header in enumerate(headers):
        field_name = sanitize_column_name(header) if header else f"column_{col_idx + 1}"

        # Collect types from sample data
        types_found = set()
        for row in sample_rows:
            if col_idx < len(row):
                value = row[col_idx]
                inferred_type = infer_type_from_value(value)
                types_found.add(inferred_type)

        # Determine the best type
        types_found.discard("null")  # Remove null for now

        if not types_found:
            field_type = ["null", "string"]
        elif len(types_found) == 1:
            field_type = ["null", types_found.pop()]
        elif "string" in types_found:
            # If string is present, default to string
            field_type = ["null", "string"]
        elif "number" in types_found:
            # Prefer number over integer
            field_type = ["null", "number"]
        else:
            field_type = ["null", "string"]

        properties[field_name] = {
            "type": field_type,
            "original_name": header
        }

    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": True
    }


def normalize_row(
    row: List[Any],
    headers: List[str],
    row_number: int
) -> Dict[str, Any]:
    """
    Normalize a row of data into a dictionary.

    Args:
        row: List of cell values
        headers: List of column headers
        row_number: The 1-indexed row number

    Returns:
        Dictionary with column names as keys
    """
    record = {"_row_number": row_number}

    for col_idx, header in enumerate(headers):
        field_name = sanitize_column_name(header) if header else f"column_{col_idx + 1}"

        if col_idx < len(row):
            value = row[col_idx]
            # Convert empty strings to None
            record[field_name] = value if value != "" else None
        else:
            record[field_name] = None

    return record


def parse_spreadsheet_id(url_or_id: str) -> str:
    """
    Extract spreadsheet ID from a URL or return the ID if already valid.

    Args:
        url_or_id: Google Sheets URL or spreadsheet ID

    Returns:
        Spreadsheet ID

    Raises:
        InvalidRequestError: If the URL/ID is invalid
    """
    # If it looks like a URL, extract the ID
    if "docs.google.com" in url_or_id or "spreadsheets" in url_or_id:
        # Pattern for extracting spreadsheet ID from various URL formats
        patterns = [
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)/edit',
            r'key=([a-zA-Z0-9-_]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)

        raise InvalidRequestError(f"Could not extract spreadsheet ID from URL: {url_or_id}")

    # Validate as a raw ID
    if re.match(r'^[a-zA-Z0-9-_]+$', url_or_id):
        return url_or_id

    raise InvalidRequestError(f"Invalid spreadsheet ID: {url_or_id}")


def format_bytes(num_bytes: int) -> str:
    """
    Format bytes to human-readable string.

    Args:
        num_bytes: Number of bytes

    Returns:
        Human-readable string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


def get_timestamp() -> str:
    """Get current ISO 8601 timestamp."""
    return datetime.utcnow().isoformat() + "Z"
