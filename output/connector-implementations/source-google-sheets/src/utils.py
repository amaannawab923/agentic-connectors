"""
Utility functions for Google Sheets connector.

Provides helper functions for data transformation, validation,
and common operations.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


def extract_spreadsheet_id(url_or_id: str) -> str:
    """
    Extract the spreadsheet ID from a URL or return the ID if already extracted.

    Args:
        url_or_id: Either a full Google Sheets URL or just the spreadsheet ID.

    Returns:
        The spreadsheet ID.

    Raises:
        ValueError: If the input is not a valid URL or ID.

    Examples:
        >>> extract_spreadsheet_id("https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit")
        '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
        >>> extract_spreadsheet_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
    """
    if not url_or_id:
        raise ValueError("Spreadsheet ID or URL cannot be empty")

    # Try to extract from URL
    url_patterns = [
        r"https?://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)",
        r"https?://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)/",
    ]

    for pattern in url_patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)

    # Validate as direct ID
    id_pattern = r"^[a-zA-Z0-9-_]+$"
    if re.match(id_pattern, url_or_id):
        return url_or_id

    raise ValueError(
        f"Invalid spreadsheet ID or URL: {url_or_id}. "
        "Expected a Google Sheets URL or alphanumeric ID."
    )


def sanitize_sheet_name(sheet_name: str) -> str:
    """
    Sanitize a sheet name for use as a stream identifier.

    Converts special characters to underscores and ensures
    the name is valid for use as an identifier.

    Args:
        sheet_name: Original sheet name.

    Returns:
        Sanitized sheet name.

    Examples:
        >>> sanitize_sheet_name("My Sheet 2024")
        'my_sheet_2024'
        >>> sanitize_sheet_name("Data & Analysis")
        'data_analysis'
    """
    if not sheet_name:
        return "unnamed_sheet"

    # Convert to lowercase
    name = sheet_name.lower()

    # Replace spaces and special characters with underscores
    name = re.sub(r"[^a-z0-9_]", "_", name)

    # Replace multiple underscores with single underscore
    name = re.sub(r"_+", "_", name)

    # Remove leading/trailing underscores
    name = name.strip("_")

    # Ensure it doesn't start with a number
    if name and name[0].isdigit():
        name = f"sheet_{name}"

    # Ensure we have a valid name
    if not name:
        return "unnamed_sheet"

    return name


def normalize_header(header: str) -> str:
    """
    Normalize a column header for use as a field name.

    Converts to snake_case and ensures validity as a field name.

    Args:
        header: Original header value.

    Returns:
        Normalized header as a valid field name.

    Examples:
        >>> normalize_header("First Name")
        'first_name'
        >>> normalize_header("Email Address")
        'email_address'
        >>> normalize_header("")
        'column_0'
    """
    if not header or not header.strip():
        return "unnamed_column"

    # Convert to lowercase
    name = header.lower().strip()

    # Replace common separators with underscore
    name = re.sub(r"[\s\-./\\]", "_", name)

    # Remove non-alphanumeric characters (except underscore)
    name = re.sub(r"[^a-z0-9_]", "", name)

    # Replace multiple underscores with single
    name = re.sub(r"_+", "_", name)

    # Remove leading/trailing underscores
    name = name.strip("_")

    # Ensure doesn't start with number
    if name and name[0].isdigit():
        name = f"col_{name}"

    # Ensure we have a valid name
    if not name:
        return "unnamed_column"

    return name


def deduplicate_headers(headers: List[str]) -> List[str]:
    """
    Ensure all headers are unique by appending suffixes to duplicates.

    Args:
        headers: List of header values.

    Returns:
        List of unique header values.

    Examples:
        >>> deduplicate_headers(["name", "value", "name", "name"])
        ['name', 'value', 'name_1', 'name_2']
    """
    seen: Dict[str, int] = {}
    result: List[str] = []

    for header in headers:
        normalized = normalize_header(header)

        if normalized in seen:
            seen[normalized] += 1
            new_name = f"{normalized}_{seen[normalized]}"
            result.append(new_name)
        else:
            seen[normalized] = 0
            result.append(normalized)

    return result


def convert_value(value: Any, target_type: Optional[str] = None) -> Any:
    """
    Convert a cell value to the target type.

    Args:
        value: The value to convert.
        target_type: Target type ("string", "integer", "number", "boolean").

    Returns:
        Converted value or original if conversion fails.
    """
    if value is None or value == "":
        return None

    if target_type is None:
        return value

    try:
        if target_type == "integer":
            # Handle percentage strings
            if isinstance(value, str) and value.endswith("%"):
                return int(float(value.rstrip("%")))
            return int(float(value))

        elif target_type == "number":
            if isinstance(value, str) and value.endswith("%"):
                return float(value.rstrip("%")) / 100
            return float(value)

        elif target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1", "y")
            return bool(value)

        elif target_type == "string":
            return str(value)

    except (ValueError, TypeError):
        pass

    return value


def infer_type(values: List[Any]) -> str:
    """
    Infer the data type from a sample of values.

    Args:
        values: Sample of values from a column.

    Returns:
        Inferred type string ("string", "integer", "number", "boolean").
    """
    if not values:
        return "string"

    # Filter out empty values
    non_empty = [v for v in values if v not in (None, "", " ")]
    if not non_empty:
        return "string"

    # Check for boolean
    bool_values = {"true", "false", "yes", "no", "1", "0", "y", "n"}
    if all(str(v).lower() in bool_values for v in non_empty):
        return "boolean"

    # Check for integer
    try:
        for v in non_empty:
            int_val = int(float(str(v).rstrip("%")))
            if int_val != float(str(v).rstrip("%")):
                raise ValueError()
        return "integer"
    except (ValueError, TypeError):
        pass

    # Check for number
    try:
        for v in non_empty:
            float(str(v).rstrip("%"))
        return "number"
    except (ValueError, TypeError):
        pass

    return "string"


def generate_record_id(record: Dict[str, Any], keys: Optional[List[str]] = None) -> str:
    """
    Generate a unique ID for a record.

    If keys are provided, uses those fields. Otherwise uses all fields.

    Args:
        record: The record dictionary.
        keys: Optional list of key fields.

    Returns:
        MD5 hash string of the record.
    """
    if keys:
        data = {k: record.get(k) for k in keys}
    else:
        data = record

    # Create stable string representation
    items = sorted(data.items())
    content = "|".join(f"{k}:{v}" for k, v in items)

    return hashlib.md5(content.encode()).hexdigest()


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        lst: List to chunk.
        chunk_size: Maximum size of each chunk.

    Returns:
        List of chunks.

    Examples:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def format_a1_range(
    sheet_name: str,
    start_row: Optional[int] = None,
    end_row: Optional[int] = None,
    start_col: Optional[str] = None,
    end_col: Optional[str] = None,
) -> str:
    """
    Format an A1 notation range string.

    Args:
        sheet_name: Name of the sheet.
        start_row: Starting row number (1-indexed).
        end_row: Ending row number (1-indexed).
        start_col: Starting column letter.
        end_col: Ending column letter.

    Returns:
        A1 notation range string.

    Examples:
        >>> format_a1_range("Sheet1", 1, 100)
        "'Sheet1'!1:100"
        >>> format_a1_range("Sheet1", 1, 100, "A", "Z")
        "'Sheet1'!A1:Z100"
    """
    # Quote sheet name if it contains spaces or special characters
    if " " in sheet_name or any(c in sheet_name for c in "!':"):
        quoted_name = f"'{sheet_name}'"
    else:
        quoted_name = sheet_name

    # Build range
    if start_col and end_col and start_row and end_row:
        return f"{quoted_name}!{start_col}{start_row}:{end_col}{end_row}"
    elif start_row and end_row:
        return f"{quoted_name}!{start_row}:{end_row}"
    elif start_col and end_col:
        return f"{quoted_name}!{start_col}:{end_col}"
    else:
        return quoted_name


def get_column_letter(index: int) -> str:
    """
    Convert a column index to a letter (A, B, ..., Z, AA, AB, ...).

    Args:
        index: 0-indexed column number.

    Returns:
        Column letter.

    Examples:
        >>> get_column_letter(0)
        'A'
        >>> get_column_letter(25)
        'Z'
        >>> get_column_letter(26)
        'AA'
    """
    result = ""
    index += 1  # Convert to 1-indexed

    while index > 0:
        index -= 1
        result = chr(65 + (index % 26)) + result
        index //= 26

    return result


def get_current_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.

    Returns:
        ISO formatted timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.

    Args:
        data: The dictionary to search.
        *keys: Keys to traverse.
        default: Default value if not found.

    Returns:
        The value at the nested path or default.

    Examples:
        >>> safe_get({"a": {"b": 1}}, "a", "b")
        1
        >>> safe_get({"a": {"b": 1}}, "a", "c", default=0)
        0
    """
    result = data
    for key in keys:
        try:
            result = result[key]
        except (KeyError, TypeError, IndexError):
            return default
    return result


def flatten_dict(
    data: Dict[str, Any],
    separator: str = "_",
    prefix: str = "",
) -> Dict[str, Any]:
    """
    Flatten a nested dictionary.

    Args:
        data: Dictionary to flatten.
        separator: Separator for nested keys.
        prefix: Prefix for all keys.

    Returns:
        Flattened dictionary.

    Examples:
        >>> flatten_dict({"a": {"b": 1, "c": 2}})
        {'a_b': 1, 'a_c': 2}
    """
    items: List[tuple] = []

    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key

        if isinstance(value, dict):
            items.extend(
                flatten_dict(value, separator=separator, prefix=new_key).items()
            )
        else:
            items.append((new_key, value))

    return dict(items)
