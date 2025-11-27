"""
Utility function tests for the Notion connector.

These tests verify that the utility functions work correctly.
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils import (
    NotionError,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    extract_plain_text,
    extract_title,
    parse_notion_datetime,
    format_datetime_for_notion,
    format_property_value,
    flatten_properties,
    extract_block_content,
    normalize_notion_id,
    format_notion_id,
    extract_id_from_url,
    build_last_edited_filter,
    build_property_filter,
)


class TestNotionErrors:
    """Test custom exception classes."""

    def test_notion_error_creation(self):
        """Test NotionError creation."""
        error = NotionError(
            message="Test error",
            status_code=400,
            code="test_code",
            request_id="req-123"
        )
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.code == "test_code"
        assert error.request_id == "req-123"

    def test_notion_error_str(self):
        """Test NotionError string representation."""
        error = NotionError(
            message="Test error",
            status_code=400,
            code="test_code"
        )
        error_str = str(error)
        assert "Test error" in error_str
        assert "400" in error_str
        assert "test_code" in error_str

    def test_rate_limit_error(self):
        """Test RateLimitError is a NotionError."""
        error = RateLimitError("Rate limited", status_code=429, code="rate_limited")
        assert isinstance(error, NotionError)
        assert error.status_code == 429

    def test_authentication_error(self):
        """Test AuthenticationError is a NotionError."""
        error = AuthenticationError("Unauthorized", status_code=401, code="unauthorized")
        assert isinstance(error, NotionError)
        assert error.status_code == 401

    def test_not_found_error(self):
        """Test NotFoundError is a NotionError."""
        error = NotFoundError("Not found", status_code=404, code="object_not_found")
        assert isinstance(error, NotionError)
        assert error.status_code == 404


class TestExtractPlainText:
    """Test extract_plain_text function."""

    def test_extract_from_rich_text(self):
        """Test extracting plain text from rich text array."""
        rich_text = [
            {"type": "text", "plain_text": "Hello "},
            {"type": "text", "plain_text": "World"}
        ]
        result = extract_plain_text(rich_text)
        assert result == "Hello World"

    def test_extract_from_empty_array(self):
        """Test extracting from empty array."""
        result = extract_plain_text([])
        assert result == ""

    def test_extract_from_none(self):
        """Test extracting from None."""
        result = extract_plain_text(None)
        assert result == ""

    def test_extract_handles_non_dict_items(self):
        """Test extracting handles non-dict items gracefully."""
        rich_text = [
            {"plain_text": "Text"},
            "not a dict",  # Should be skipped
            {"plain_text": " More"}
        ]
        result = extract_plain_text(rich_text)
        assert result == "Text More"


class TestExtractTitle:
    """Test extract_title function."""

    def test_extract_title_from_database(self):
        """Test extracting title from database properties."""
        properties = {
            "title": [{"plain_text": "My Database"}]
        }
        result = extract_title(properties)
        assert result == "My Database"

    def test_extract_title_from_page_name(self):
        """Test extracting title from page Name property."""
        properties = {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "My Page"}]
            }
        }
        result = extract_title(properties)
        assert result == "My Page"

    def test_extract_title_from_title_type_property(self):
        """Test extracting title from any title-type property."""
        properties = {
            "Custom Title": {
                "type": "title",
                "title": [{"plain_text": "Custom Name"}]
            }
        }
        result = extract_title(properties)
        assert result == "Custom Name"

    def test_extract_title_returns_untitled(self):
        """Test that Untitled is returned when no title found."""
        properties = {
            "Status": {"type": "status"}
        }
        result = extract_title(properties)
        assert result == "Untitled"


class TestDateTimeUtils:
    """Test date/time utility functions."""

    def test_parse_notion_datetime_iso_z(self):
        """Test parsing ISO datetime with Z suffix."""
        result = parse_notion_datetime("2024-01-15T10:30:00.000Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_notion_datetime_simple_iso(self):
        """Test parsing simple ISO datetime."""
        result = parse_notion_datetime("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024

    def test_parse_notion_datetime_date_only(self):
        """Test parsing date-only format."""
        result = parse_notion_datetime("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_notion_datetime_none(self):
        """Test parsing None returns None."""
        result = parse_notion_datetime(None)
        assert result is None

    def test_parse_notion_datetime_invalid(self):
        """Test parsing invalid datetime returns None."""
        result = parse_notion_datetime("not-a-date")
        assert result is None

    def test_format_datetime_for_notion(self):
        """Test formatting datetime for Notion API."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_datetime_for_notion(dt)
        assert result == "2024-01-15T10:30:00.000Z"


class TestFormatPropertyValue:
    """Test format_property_value function."""

    def test_format_title_property(self):
        """Test formatting title property."""
        prop = {
            "type": "title",
            "title": [{"plain_text": "My Title"}]
        }
        result = format_property_value(prop)
        assert result == "My Title"

    def test_format_rich_text_property(self):
        """Test formatting rich_text property."""
        prop = {
            "type": "rich_text",
            "rich_text": [{"plain_text": "Some text"}]
        }
        result = format_property_value(prop)
        assert result == "Some text"

    def test_format_number_property(self):
        """Test formatting number property."""
        prop = {"type": "number", "number": 42}
        result = format_property_value(prop)
        assert result == 42

    def test_format_select_property(self):
        """Test formatting select property."""
        prop = {
            "type": "select",
            "select": {"name": "Option A", "color": "blue"}
        }
        result = format_property_value(prop)
        assert result == "Option A"

    def test_format_multi_select_property(self):
        """Test formatting multi_select property."""
        prop = {
            "type": "multi_select",
            "multi_select": [
                {"name": "Tag 1"},
                {"name": "Tag 2"}
            ]
        }
        result = format_property_value(prop)
        assert result == ["Tag 1", "Tag 2"]

    def test_format_checkbox_property(self):
        """Test formatting checkbox property."""
        prop = {"type": "checkbox", "checkbox": True}
        result = format_property_value(prop)
        assert result is True

    def test_format_url_property(self):
        """Test formatting url property."""
        prop = {"type": "url", "url": "https://example.com"}
        result = format_property_value(prop)
        assert result == "https://example.com"

    def test_format_email_property(self):
        """Test formatting email property."""
        prop = {"type": "email", "email": "test@example.com"}
        result = format_property_value(prop)
        assert result == "test@example.com"

    def test_format_date_property(self):
        """Test formatting date property."""
        prop = {
            "type": "date",
            "date": {"start": "2024-01-15", "end": "2024-01-20", "time_zone": None}
        }
        result = format_property_value(prop)
        assert result == {"start": "2024-01-15", "end": "2024-01-20", "time_zone": None}

    def test_format_relation_property(self):
        """Test formatting relation property."""
        prop = {
            "type": "relation",
            "relation": [{"id": "page-1"}, {"id": "page-2"}]
        }
        result = format_property_value(prop)
        assert result == ["page-1", "page-2"]

    def test_format_none_property(self):
        """Test formatting None property."""
        result = format_property_value(None)
        assert result is None


class TestFlattenProperties:
    """Test flatten_properties function."""

    def test_flatten_multiple_properties(self):
        """Test flattening multiple properties."""
        properties = {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Test Item"}]
            },
            "Status": {
                "type": "select",
                "select": {"name": "Active"}
            },
            "Count": {
                "type": "number",
                "number": 5
            }
        }
        result = flatten_properties(properties)

        assert result["Name"] == "Test Item"
        assert result["Status"] == "Active"
        assert result["Count"] == 5


class TestExtractBlockContent:
    """Test extract_block_content function."""

    def test_extract_paragraph_content(self):
        """Test extracting paragraph block content."""
        block = {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"plain_text": "Hello World"}]
            }
        }
        result = extract_block_content(block)
        assert result == "Hello World"

    def test_extract_heading_content(self):
        """Test extracting heading block content."""
        block = {
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"plain_text": "My Heading"}]
            }
        }
        result = extract_block_content(block)
        assert result == "My Heading"

    def test_extract_child_page_content(self):
        """Test extracting child_page block content."""
        block = {
            "type": "child_page",
            "child_page": {"title": "Nested Page"}
        }
        result = extract_block_content(block)
        assert result == "Nested Page"

    def test_extract_image_content(self):
        """Test extracting image block content."""
        block = {
            "type": "image",
            "image": {
                "caption": [{"plain_text": "My image"}],
                "type": "external",
                "external": {"url": "https://example.com/img.jpg"}
            }
        }
        result = extract_block_content(block)
        assert "Image" in result
        assert "My image" in result

    def test_extract_empty_block(self):
        """Test extracting empty block content."""
        block = {"type": None}
        result = extract_block_content(block)
        assert result == ""


class TestIDUtils:
    """Test ID utility functions."""

    def test_normalize_notion_id(self):
        """Test normalizing Notion ID."""
        # UUID: 12345678-1234-1234-1234-123456789abc = 32 hex chars
        result = normalize_notion_id("12345678-1234-1234-1234-123456789abc")
        # Without dashes: 32 chars
        assert result == "12345678123412341234123456789abc"
        assert len(result) == 32

    def test_normalize_already_normalized(self):
        """Test normalizing already normalized ID."""
        result = normalize_notion_id("12345678123412341234123456789abc")
        assert result == "12345678123412341234123456789abc"
        assert len(result) == 32

    def test_format_notion_id(self):
        """Test formatting Notion ID with dashes."""
        result = format_notion_id("12345678123412341234123456789abc")
        assert result == "12345678-1234-1234-1234-123456789abc"
        assert len(result) == 36

    def test_format_notion_id_already_formatted(self):
        """Test formatting already formatted ID."""
        result = format_notion_id("12345678-1234-1234-1234-123456789abc")
        # Should handle gracefully (removes dashes then re-adds)
        assert "-" in result

    def test_extract_id_from_url(self):
        """Test extracting ID from Notion URL.

        Note: The extract_id_from_url function expects specific URL formats:
        1. notion.so/workspace/Page-Name-{32-char-hex-id}
        2. notion.so/{32-char-hex-id}
        3. notion.so/workspace/{32-char-hex-id}

        URLs without proper format will return None.
        """
        # Format 1: workspace/page-title-id
        url1 = "https://www.notion.so/myworkspace/My-Page-12345678123412341234123456789abc"
        result1 = extract_id_from_url(url1)
        assert result1 is not None
        assert "12345678" in result1

        # Format 2: just the ID (less common)
        url2 = "https://notion.so/12345678123412341234123456789abc"
        result2 = extract_id_from_url(url2)
        assert result2 is not None

        # Format 3: workspace/id (without page name)
        url3 = "https://notion.so/workspace/12345678123412341234123456789abc"
        result3 = extract_id_from_url(url3)
        assert result3 is not None

    def test_extract_id_from_invalid_url(self):
        """Test extracting ID from invalid URL."""
        url = "https://example.com/not-a-notion-url"
        result = extract_id_from_url(url)
        assert result is None


class TestFilterBuilding:
    """Test filter building utilities."""

    def test_build_last_edited_filter(self):
        """Test building last_edited filter."""
        dt = datetime(2024, 1, 15, 0, 0, 0)
        result = build_last_edited_filter(dt)

        assert result["timestamp"] == "last_edited_time"
        assert "last_edited_time" in result
        assert "on_or_after" in result["last_edited_time"]

    def test_build_property_filter(self):
        """Test building property filter."""
        result = build_property_filter(
            property_name="Status",
            property_type="select",
            condition="equals",
            value="Active"
        )

        assert result["property"] == "Status"
        assert result["select"]["equals"] == "Active"
