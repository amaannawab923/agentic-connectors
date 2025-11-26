"""
Utility functions for Google Sheets connector.

Provides helper functions for:
- Header normalization
- Range notation building
- Schema inference
- Data type detection
"""

import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, parse_qs


def normalize_header(headers: List[Any]) -> List[str]:
    """
    Normalize column headers to valid, unique identifiers.

    Handles:
    - Empty headers (generates column_N names)
    - Duplicate headers (appends _N suffix)
    - Non-string values (converts to string)
    - Special characters (replaces with underscores)

    Args:
        headers: List of raw header values from the spreadsheet.

    Returns:
        List of normalized, unique header strings.

    Example:
        >>> normalize_header(["Name", "Email", "", "Name", None])
        ["name", "email", "column_2", "name_1", "column_4"]
    """
    normalized = []
    seen: Dict[str, int] = {}

    for i, header in enumerate(headers):
        # Handle empty or None headers
        if header is None or (isinstance(header, str) and header.strip() == ""):
            base_name = f"column_{i}"
        else:
            # Convert to string and clean
            base_name = str(header).strip()
            # Replace special characters with underscores
            base_name = re.sub(r"[^\w\s]", "_", base_name)
            # Replace whitespace with underscores
            base_name = re.sub(r"\s+", "_", base_name)
            # Remove leading/trailing underscores
            base_name = base_name.strip("_")
            # Convert to lowercase
            base_name = base_name.lower()
            # Ensure it starts with a letter or underscore
            if base_name and not base_name[0].isalpha() and base_name[0] != "_":
                base_name = f"col_{base_name}"
            # Handle empty result after cleaning
            if not base_name:
                base_name = f"column_{i}"

        # Handle duplicates
        if base_name in seen:
            seen[base_name] += 1
            unique_name = f"{base_name}_{seen[base_name]}"
        else:
            seen[base_name] = 0
            unique_name = base_name

        normalized.append(unique_name)

    return normalized


def build_range_notation(
    sheet_name: str,
    start_col: str = "A",
    start_row: Optional[int] = None,
    end_col: Optional[str] = None,
    end_row: Optional[int] = None,
) -> str:
    """
    Build A1 notation range string.

    Args:
        sheet_name: Name of the sheet (will be quoted if needed).
        start_col: Starting column (default "A").
        start_row: Starting row number (1-indexed, optional).
        end_col: Ending column (optional).
        end_row: Ending row number (optional).

    Returns:
        A1 notation range string.

    Examples:
        >>> build_range_notation("Sheet1", "A", 1, "D", 10)
        "'Sheet1'!A1:D10"
        >>> build_range_notation("My Sheet", "A", end_col="Z")
        "'My Sheet'!A:Z"
    """
    # Quote sheet name if it contains spaces or special characters
    if " " in sheet_name or "'" in sheet_name or "!" in sheet_name:
        # Escape single quotes by doubling them
        escaped_name = sheet_name.replace("'", "''")
        quoted_name = f"'{escaped_name}'"
    else:
        quoted_name = f"'{sheet_name}'"

    # Build range parts
    start_part = start_col
    if start_row is not None:
        start_part += str(start_row)

    if end_col is not None or end_row is not None:
        end_part = end_col or start_col
        if end_row is not None:
            end_part += str(end_row)
        return f"{quoted_name}!{start_part}:{end_part}"
    else:
        return f"{quoted_name}!{start_part}"


def parse_spreadsheet_id(url_or_id: str) -> str:
    """
    Extract spreadsheet ID from a Google Sheets URL or return the ID if already extracted.

    Args:
        url_or_id: Google Sheets URL or spreadsheet ID.

    Returns:
        The spreadsheet ID.

    Examples:
        >>> parse_spreadsheet_id("https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit")
        "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        >>> parse_spreadsheet_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    """
    # Check if it's already just an ID
    if not url_or_id.startswith("http"):
        return url_or_id

    # Parse URL
    parsed = urlparse(url_or_id)

    # Handle different URL formats
    path_parts = parsed.path.split("/")

    for i, part in enumerate(path_parts):
        if part == "d" and i + 1 < len(path_parts):
            return path_parts[i + 1]

    # Try to extract from query parameters (some export URLs)
    query_params = parse_qs(parsed.query)
    if "id" in query_params:
        return query_params["id"][0]

    raise ValueError(f"Could not extract spreadsheet ID from: {url_or_id}")


def infer_json_schema_type(value: Any) -> Dict[str, Any]:
    """
    Infer JSON Schema type from a Python value.

    Args:
        value: A Python value.

    Returns:
        JSON Schema type definition.
    """
    if value is None:
        return {"type": ["null", "string"]}

    if isinstance(value, bool):
        return {"type": ["null", "boolean"]}

    if isinstance(value, int):
        return {"type": ["null", "integer"]}

    if isinstance(value, float):
        return {"type": ["null", "number"]}

    if isinstance(value, str):
        # Check for date/time patterns
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return {"type": ["null", "string"], "format": "date"}
        if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", value):
            return {"type": ["null", "string"], "format": "date-time"}
        return {"type": ["null", "string"]}

    if isinstance(value, list):
        return {"type": ["null", "array"], "items": {}}

    if isinstance(value, dict):
        return {"type": ["null", "object"]}

    return {"type": ["null", "string"]}


def merge_schema_types(type1: Dict[str, Any], type2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two JSON Schema type definitions.

    Used when inferring schema from multiple sample values.

    Args:
        type1: First type definition.
        type2: Second type definition.

    Returns:
        Merged type definition.
    """
    # Handle null types
    types1 = type1.get("type", [])
    types2 = type2.get("type", [])

    if isinstance(types1, str):
        types1 = [types1]
    if isinstance(types2, str):
        types2 = [types2]

    # Combine types, keeping null
    combined = set(types1) | set(types2)

    # Simplify: if we have both integer and number, keep number
    if "integer" in combined and "number" in combined:
        combined.discard("integer")

    # If we have multiple non-null types, fall back to string
    non_null_types = combined - {"null"}
    if len(non_null_types) > 1:
        combined = {"null", "string"}

    result = {"type": list(combined)}

    # Preserve format if both have it
    if "format" in type1 and "format" in type2 and type1["format"] == type2["format"]:
        result["format"] = type1["format"]

    return result


def infer_schema_from_values(
    headers: List[str],
    sample_rows: List[List[Any]],
) -> Dict[str, Any]:
    """
    Infer JSON Schema from column headers and sample data.

    Args:
        headers: List of normalized column headers.
        sample_rows: List of rows (each row is a list of values).

    Returns:
        JSON Schema dictionary.
    """
    properties: Dict[str, Dict[str, Any]] = {}

    # Initialize with null types
    for header in headers:
        properties[header] = {"type": ["null", "string"]}

    # Analyze sample values
    for row in sample_rows:
        for i, header in enumerate(headers):
            if i < len(row):
                value = row[i]
                if value is not None and value != "":
                    inferred = infer_json_schema_type(value)
                    properties[header] = merge_schema_types(
                        properties[header],
                        inferred,
                    )

    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        lst: List to chunk.
        chunk_size: Maximum size of each chunk.

    Returns:
        List of chunks.

    Example:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_get(
    data: Union[Dict[str, Any], List[Any]],
    *keys: Union[str, int],
    default: Any = None,
) -> Any:
    """
    Safely get a nested value from a dictionary or list.

    Args:
        data: Dictionary or list to traverse.
        *keys: Keys or indices to follow.
        default: Default value if path doesn't exist.

    Returns:
        Value at the specified path, or default.

    Example:
        >>> data = {"a": {"b": [1, 2, 3]}}
        >>> safe_get(data, "a", "b", 1)
        2
        >>> safe_get(data, "a", "c", default="not found")
        "not found"
    """
    current = data
    for key in keys:
        try:
            if isinstance(current, dict):
                current = current.get(key, default)
            elif isinstance(current, (list, tuple)):
                current = current[key] if -len(current) <= key < len(current) else default
            else:
                return default
            if current is default:
                return default
        except (KeyError, IndexError, TypeError):
            return default
    return current


def column_letter_to_index(letter: str) -> int:
    """
    Convert a column letter (A, B, ..., Z, AA, AB, ...) to a 0-based index.

    Args:
        letter: Column letter(s) in A1 notation.

    Returns:
        0-based column index.

    Example:
        >>> column_letter_to_index("A")
        0
        >>> column_letter_to_index("Z")
        25
        >>> column_letter_to_index("AA")
        26
    """
    result = 0
    for char in letter.upper():
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def index_to_column_letter(index: int) -> str:
    """
    Convert a 0-based column index to a column letter.

    Args:
        index: 0-based column index.

    Returns:
        Column letter(s) in A1 notation.

    Example:
        >>> index_to_column_letter(0)
        "A"
        >>> index_to_column_letter(25)
        "Z"
        >>> index_to_column_letter(26)
        "AA"
    """
    result = ""
    index += 1  # Convert to 1-based
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result
