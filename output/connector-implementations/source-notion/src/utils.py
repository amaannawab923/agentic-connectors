"""
Utility functions and custom exceptions for the Notion connector.

This module provides helper functions for parsing Notion API responses,
formatting data, and handling errors.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class NotionError(Exception):
    """Base exception for Notion API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Initialize a NotionError.

        Args:
            message: Human-readable error message
            status_code: HTTP status code from the API response
            code: Notion error code (e.g., 'rate_limited', 'unauthorized')
            request_id: Notion request ID for debugging
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.request_id = request_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.code:
            parts.append(f"Code: {self.code}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"code={self.code!r}, "
            f"request_id={self.request_id!r})"
        )

    @classmethod
    def from_response(cls, response: Any) -> "NotionError":
        """
        Create a NotionError from an API response.

        Args:
            response: requests.Response object from the API

        Returns:
            Appropriate NotionError subclass instance
        """
        try:
            data = response.json()
        except Exception:
            data = {}

        status_code = response.status_code
        code = data.get("code", "unknown")
        message = data.get("message", f"HTTP {status_code} error")
        request_id = response.headers.get("x-request-id")

        # Return appropriate subclass based on error code
        if code == "rate_limited" or status_code == 429:
            return NotionRateLimitError(message, status_code, code, request_id)
        elif code == "unauthorized" or status_code == 401:
            return NotionAuthenticationError(message, status_code, code, request_id)
        elif code == "object_not_found" or status_code == 404:
            return NotionNotFoundError(message, status_code, code, request_id)
        elif code == "validation_error" or status_code == 400:
            return NotionValidationError(message, status_code, code, request_id)
        elif status_code >= 500:
            return NotionServerError(message, status_code, code, request_id)
        else:
            return cls(message, status_code, code, request_id)


class NotionRateLimitError(NotionError):
    """Exception raised when rate limit is exceeded."""

    pass


class NotionAuthenticationError(NotionError):
    """Exception raised for authentication failures."""

    pass


class NotionNotFoundError(NotionError):
    """Exception raised when a resource is not found."""

    pass


class NotionValidationError(NotionError):
    """Exception raised for validation errors in requests."""

    pass


class NotionServerError(NotionError):
    """Exception raised for server-side errors (5xx)."""

    pass


class NotionConfigurationError(NotionError):
    """Exception raised for configuration errors."""

    pass


# =============================================================================
# Text Extraction Utilities
# =============================================================================


def extract_plain_text(rich_text: List[Dict[str, Any]]) -> str:
    """
    Extract plain text from Notion rich text array.

    Args:
        rich_text: List of rich text objects from Notion API

    Returns:
        Concatenated plain text string

    Example:
        >>> rich_text = [{"plain_text": "Hello "}, {"plain_text": "World"}]
        >>> extract_plain_text(rich_text)
        'Hello World'
    """
    if not rich_text:
        return ""

    parts = []
    for item in rich_text:
        if isinstance(item, dict) and "plain_text" in item:
            parts.append(item["plain_text"])

    return "".join(parts)


def extract_title(properties: Dict[str, Any]) -> str:
    """
    Extract title from Notion page/database properties.

    Args:
        properties: Properties dictionary from Notion object

    Returns:
        Title string or 'Untitled' if not found
    """
    # Check for 'title' property (databases)
    if "title" in properties:
        title_prop = properties["title"]
        if isinstance(title_prop, list):
            return extract_plain_text(title_prop)
        elif isinstance(title_prop, dict) and "title" in title_prop:
            return extract_plain_text(title_prop["title"])

    # Check for 'Name' property (common in pages)
    if "Name" in properties:
        name_prop = properties["Name"]
        if isinstance(name_prop, dict) and "title" in name_prop:
            return extract_plain_text(name_prop["title"])

    # Search for any title-type property
    for prop_name, prop_value in properties.items():
        if isinstance(prop_value, dict) and prop_value.get("type") == "title":
            return extract_plain_text(prop_value.get("title", []))

    return "Untitled"


# =============================================================================
# Date/Time Utilities
# =============================================================================


def parse_notion_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a Notion datetime string to a Python datetime object.

    Args:
        datetime_str: ISO 8601 datetime string from Notion API

    Returns:
        datetime object or None if parsing fails

    Example:
        >>> parse_notion_datetime("2024-01-15T10:30:00.000Z")
        datetime.datetime(2024, 1, 15, 10, 30, 0)
    """
    if not datetime_str:
        return None

    # Handle various Notion datetime formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse datetime: {datetime_str}")
    return None


def format_datetime_for_notion(dt: Union[datetime, str]) -> str:
    """
    Format a Python datetime for Notion API requests.

    Args:
        dt: datetime object or ISO string to format

    Returns:
        ISO 8601 formatted string
    """
    if isinstance(dt, str):
        # Already a string, try to normalize it
        parsed = parse_notion_datetime(dt)
        if parsed:
            dt = parsed
        else:
            return dt  # Return as-is if can't parse

    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# =============================================================================
# Property Value Formatting
# =============================================================================


def format_property_value(property_data: Dict[str, Any]) -> Any:
    """
    Format a Notion property value for output.

    Converts Notion's complex property structure into simpler values
    suitable for data extraction.

    Args:
        property_data: Property object from Notion API

    Returns:
        Simplified property value
    """
    if not property_data or not isinstance(property_data, dict):
        return None

    prop_type = property_data.get("type")

    if prop_type == "title":
        return extract_plain_text(property_data.get("title", []))

    elif prop_type == "rich_text":
        return extract_plain_text(property_data.get("rich_text", []))

    elif prop_type == "number":
        return property_data.get("number")

    elif prop_type == "select":
        select = property_data.get("select")
        return select.get("name") if select else None

    elif prop_type == "multi_select":
        multi_select = property_data.get("multi_select", [])
        return [item.get("name") for item in multi_select]

    elif prop_type == "status":
        status = property_data.get("status")
        return status.get("name") if status else None

    elif prop_type == "date":
        date = property_data.get("date")
        if date:
            return {
                "start": date.get("start"),
                "end": date.get("end"),
                "time_zone": date.get("time_zone"),
            }
        return None

    elif prop_type == "people":
        people = property_data.get("people", [])
        return [
            {
                "id": person.get("id"),
                "name": person.get("name"),
                "email": person.get("person", {}).get("email"),
            }
            for person in people
        ]

    elif prop_type == "files":
        files = property_data.get("files", [])
        result = []
        for file in files:
            file_data = {"name": file.get("name")}
            if file.get("type") == "file":
                file_data["url"] = file.get("file", {}).get("url")
            elif file.get("type") == "external":
                file_data["url"] = file.get("external", {}).get("url")
            result.append(file_data)
        return result

    elif prop_type == "checkbox":
        return property_data.get("checkbox")

    elif prop_type == "url":
        return property_data.get("url")

    elif prop_type == "email":
        return property_data.get("email")

    elif prop_type == "phone_number":
        return property_data.get("phone_number")

    elif prop_type == "formula":
        formula = property_data.get("formula", {})
        formula_type = formula.get("type")
        return formula.get(formula_type) if formula_type else None

    elif prop_type == "relation":
        relations = property_data.get("relation", [])
        return [rel.get("id") for rel in relations]

    elif prop_type == "rollup":
        rollup = property_data.get("rollup", {})
        rollup_type = rollup.get("type")
        if rollup_type == "array":
            return [format_property_value(item) for item in rollup.get("array", [])]
        return rollup.get(rollup_type) if rollup_type else None

    elif prop_type == "created_time":
        return property_data.get("created_time")

    elif prop_type == "created_by":
        created_by = property_data.get("created_by", {})
        return created_by.get("id")

    elif prop_type == "last_edited_time":
        return property_data.get("last_edited_time")

    elif prop_type == "last_edited_by":
        last_edited_by = property_data.get("last_edited_by", {})
        return last_edited_by.get("id")

    elif prop_type == "unique_id":
        unique_id = property_data.get("unique_id", {})
        prefix = unique_id.get("prefix", "")
        number = unique_id.get("number", "")
        return f"{prefix}-{number}" if prefix else str(number)

    elif prop_type == "verification":
        verification = property_data.get("verification", {})
        return {
            "state": verification.get("state"),
            "verified_by": verification.get("verified_by", {}).get("id"),
            "date": verification.get("date"),
        }

    else:
        # Return raw value for unknown types
        return property_data.get(prop_type)


def flatten_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten Notion properties into a simple key-value dictionary.

    Args:
        properties: Properties dictionary from Notion object

    Returns:
        Flattened dictionary with property names as keys
    """
    result = {}
    for name, prop_data in properties.items():
        result[name] = format_property_value(prop_data)
    return result


# =============================================================================
# Block Processing Utilities
# =============================================================================


def extract_block_content(block: Dict[str, Any]) -> str:
    """
    Extract text content from a Notion block.

    Args:
        block: Block object from Notion API

    Returns:
        Plain text content of the block
    """
    block_type = block.get("type")

    if not block_type:
        return ""

    block_data = block.get(block_type, {})

    # Text-based blocks (paragraph, heading_1, heading_2, heading_3, etc.)
    if "rich_text" in block_data:
        return extract_plain_text(block_data["rich_text"])

    # Code blocks
    if block_type == "code":
        code_text = extract_plain_text(block_data.get("rich_text", []))
        language = block_data.get("language", "")
        return f"```{language}\n{code_text}\n```"

    # Special block types
    if block_type == "child_page":
        return f"[Page: {block_data.get('title', '')}]"

    if block_type == "child_database":
        return f"[Database: {block_data.get('title', '')}]"

    if block_type == "image":
        caption = block_data.get("caption", [])
        return f"[Image: {extract_plain_text(caption)}]"

    if block_type == "video":
        caption = block_data.get("caption", [])
        return f"[Video: {extract_plain_text(caption)}]"

    if block_type == "file":
        caption = block_data.get("caption", [])
        return f"[File: {extract_plain_text(caption)}]"

    if block_type == "pdf":
        caption = block_data.get("caption", [])
        return f"[PDF: {extract_plain_text(caption)}]"

    if block_type == "audio":
        caption = block_data.get("caption", [])
        return f"[Audio: {extract_plain_text(caption)}]"

    if block_type == "equation":
        return f"$${block_data.get('expression', '')}$$"

    if block_type == "table_row":
        cells = block_data.get("cells", [])
        return " | ".join(extract_plain_text(cell) for cell in cells)

    if block_type == "bookmark":
        url = block_data.get("url", "")
        caption = extract_plain_text(block_data.get("caption", []))
        return f"[Bookmark: {caption or url}]({url})"

    if block_type == "embed":
        url = block_data.get("url", "")
        return f"[Embed: {url}]"

    if block_type == "link_preview":
        url = block_data.get("url", "")
        return f"[Link: {url}]"

    if block_type == "divider":
        return "---"

    if block_type == "table_of_contents":
        return "[Table of Contents]"

    if block_type == "breadcrumb":
        return "[Breadcrumb]"

    if block_type == "synced_block":
        return "[Synced Block]"

    if block_type == "template":
        return "[Template]"

    if block_type == "link_to_page":
        page_id = block_data.get("page_id") or block_data.get("database_id", "")
        return f"[Link to: {page_id}]"

    return ""


def get_block_url(block: Dict[str, Any]) -> Optional[str]:
    """
    Extract URL from a block if present.

    Args:
        block: Block object from Notion API

    Returns:
        URL string or None
    """
    block_type = block.get("type")
    if not block_type:
        return None

    block_data = block.get(block_type, {})

    if block_type == "bookmark":
        return block_data.get("url")

    if block_type == "embed":
        return block_data.get("url")

    if block_type == "link_preview":
        return block_data.get("url")

    if block_type in ("image", "file", "video", "pdf", "audio"):
        file_type = block_data.get("type")
        if file_type == "file":
            return block_data.get("file", {}).get("url")
        elif file_type == "external":
            return block_data.get("external", {}).get("url")

    return None


# =============================================================================
# ID Utilities
# =============================================================================


def normalize_notion_id(notion_id: str) -> str:
    """
    Normalize a Notion ID by removing dashes.

    Notion IDs can be provided with or without dashes.
    This normalizes them to the format without dashes.

    Args:
        notion_id: Notion UUID (with or without dashes)

    Returns:
        Normalized ID without dashes
    """
    return notion_id.replace("-", "")


def format_notion_id(notion_id: str) -> str:
    """
    Format a Notion ID with dashes (standard UUID format).

    Args:
        notion_id: Notion ID (with or without dashes)

    Returns:
        UUID-formatted ID with dashes
    """
    clean_id = normalize_notion_id(notion_id)
    if len(clean_id) == 32:
        return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    return notion_id


def extract_id_from_url(url: str) -> Optional[str]:
    """
    Extract a Notion page/database ID from a Notion URL.

    Args:
        url: Notion URL

    Returns:
        Extracted ID or None
    """
    # Pattern for Notion URLs
    patterns = [
        r"notion\.so/[^/]+/[^/]+-([a-f0-9]{32})",
        r"notion\.so/([a-f0-9]{32})",
        r"notion\.so/[^/]+/([a-f0-9]{32})",
        r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return format_notion_id(match.group(1))

    return None


def is_valid_notion_id(notion_id: str) -> bool:
    """
    Check if a string is a valid Notion ID.

    Args:
        notion_id: String to validate

    Returns:
        True if valid Notion ID, False otherwise
    """
    clean_id = normalize_notion_id(notion_id)
    return bool(re.match(r"^[a-f0-9]{32}$", clean_id))


# =============================================================================
# Filter Building Utilities
# =============================================================================


def build_last_edited_filter(start_date: Union[datetime, str]) -> Dict[str, Any]:
    """
    Build a filter for pages edited after a specific date.

    Args:
        start_date: datetime or ISO string to filter from

    Returns:
        Notion filter dictionary
    """
    return {
        "timestamp": "last_edited_time",
        "last_edited_time": {
            "on_or_after": format_datetime_for_notion(start_date)
        },
    }


def build_created_filter(start_date: Union[datetime, str]) -> Dict[str, Any]:
    """
    Build a filter for pages created after a specific date.

    Args:
        start_date: datetime or ISO string to filter from

    Returns:
        Notion filter dictionary
    """
    return {
        "timestamp": "created_time",
        "created_time": {
            "on_or_after": format_datetime_for_notion(start_date)
        },
    }


def build_property_filter(
    property_name: str,
    property_type: str,
    condition: str,
    value: Any
) -> Dict[str, Any]:
    """
    Build a property filter for database queries.

    Args:
        property_name: Name of the property to filter
        property_type: Type of the property (e.g., 'text', 'number')
        condition: Filter condition (e.g., 'equals', 'contains')
        value: Value to filter by

    Returns:
        Notion filter dictionary
    """
    return {
        "property": property_name,
        property_type: {
            condition: value
        }
    }


def combine_filters(filters: List[Dict[str, Any]], operator: str = "and") -> Dict[str, Any]:
    """
    Combine multiple filters with AND/OR logic.

    Args:
        filters: List of filter dictionaries
        operator: 'and' or 'or'

    Returns:
        Combined filter dictionary
    """
    if len(filters) == 0:
        return {}
    if len(filters) == 1:
        return filters[0]

    return {operator: filters}


# =============================================================================
# Logging Utilities
# =============================================================================


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """
    Set up logging for the Notion connector.

    Args:
        level: Logging level (default INFO)
        format_string: Custom format string (optional)
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set level for specific loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def log_api_call(
    method: str,
    endpoint: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None
) -> None:
    """
    Log an API call for debugging purposes.

    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: Response status code
        duration_ms: Request duration in milliseconds
    """
    parts = [f"{method} {endpoint}"]
    if status_code:
        parts.append(f"status={status_code}")
    if duration_ms:
        parts.append(f"duration={duration_ms:.0f}ms")
    logger.debug(" | ".join(parts))


# =============================================================================
# Data Transformation Utilities
# =============================================================================


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.

    Args:
        data: Dictionary to get value from
        *keys: Keys to traverse
        default: Default value if key not found

    Returns:
        Value at the key path or default
    """
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def truncate_string(s: str, max_length: int = 2000, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix
