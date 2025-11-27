"""
Utility function tests for Google Sheets connector.

These tests verify the utility functions work correctly.
"""

import pytest
from src.utils import (
    column_number_to_letter,
    column_letter_to_number,
    build_range_notation,
    parse_range_notation,
    sanitize_column_name,
    infer_type_from_value,
    infer_schema_from_data,
    normalize_row,
    parse_spreadsheet_id,
    format_bytes,
    get_timestamp,
    GoogleSheetsError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    InvalidRequestError,
)


class TestColumnConversions:
    """Test column number/letter conversions."""

    def test_column_number_to_letter_single(self):
        """Test single letter columns."""
        assert column_number_to_letter(1) == "A"
        assert column_number_to_letter(26) == "Z"

    def test_column_number_to_letter_double(self):
        """Test double letter columns."""
        assert column_number_to_letter(27) == "AA"
        assert column_number_to_letter(52) == "AZ"
        assert column_number_to_letter(53) == "BA"

    def test_column_letter_to_number_single(self):
        """Test single letter to number."""
        assert column_letter_to_number("A") == 1
        assert column_letter_to_number("Z") == 26

    def test_column_letter_to_number_double(self):
        """Test double letter to number."""
        assert column_letter_to_number("AA") == 27
        assert column_letter_to_number("AZ") == 52

    def test_column_conversions_roundtrip(self):
        """Test that conversions are reversible."""
        for num in [1, 26, 27, 100, 702]:
            letter = column_number_to_letter(num)
            assert column_letter_to_number(letter) == num


class TestRangeNotation:
    """Test range notation functions."""

    def test_build_range_notation_sheet_only(self):
        """Test building range with just sheet name."""
        result = build_range_notation("Sheet1")
        assert result == "'Sheet1'"

    def test_build_range_notation_with_rows(self):
        """Test building range with row numbers."""
        result = build_range_notation("Sheet1", start_row=1, end_row=100)
        assert result == "'Sheet1'!1:100"

    def test_build_range_notation_full_range(self):
        """Test building full range notation."""
        result = build_range_notation(
            "Sheet1",
            start_row=1,
            end_row=100,
            start_col="A",
            end_col="Z"
        )
        assert result == "'Sheet1'!A1:Z100"

    def test_parse_range_notation_simple(self):
        """Test parsing simple range notation."""
        sheet_name, start, end = parse_range_notation("'Sheet1'!A1:Z100")
        assert sheet_name == "Sheet1"
        assert start == "A1"
        assert end == "Z100"

    def test_parse_range_notation_sheet_only(self):
        """Test parsing sheet name only."""
        sheet_name, start, end = parse_range_notation("'My Sheet'")
        assert sheet_name == "My Sheet"
        assert start is None
        assert end is None


class TestSanitizeColumnName:
    """Test column name sanitization."""

    def test_sanitize_basic(self):
        """Test basic sanitization."""
        assert sanitize_column_name("Column Name") == "column_name"
        assert sanitize_column_name("email") == "email"

    def test_sanitize_special_characters(self):
        """Test sanitizing special characters."""
        assert sanitize_column_name("Special@Character!") == "special_character"
        assert sanitize_column_name("Column#1$2") == "column_1_2"

    def test_sanitize_leading_number(self):
        """Test sanitizing names that start with numbers."""
        assert sanitize_column_name("123Column") == "col_123column"

    def test_sanitize_empty(self):
        """Test sanitizing empty string."""
        assert sanitize_column_name("") == "unnamed_column"

    def test_sanitize_whitespace(self):
        """Test sanitizing whitespace."""
        assert sanitize_column_name("  Multiple   Spaces  ") == "multiple_spaces"


class TestTypeInference:
    """Test type inference functions."""

    def test_infer_type_null(self):
        """Test inferring null type."""
        assert infer_type_from_value(None) == "null"
        assert infer_type_from_value("") == "null"

    def test_infer_type_boolean(self):
        """Test inferring boolean type."""
        assert infer_type_from_value(True) == "boolean"
        assert infer_type_from_value(False) == "boolean"
        assert infer_type_from_value("true") == "boolean"
        assert infer_type_from_value("false") == "boolean"

    def test_infer_type_integer(self):
        """Test inferring integer type."""
        assert infer_type_from_value(42) == "integer"

    def test_infer_type_number(self):
        """Test inferring number type."""
        assert infer_type_from_value(3.14) == "number"
        assert infer_type_from_value("3.14") == "number"

    def test_infer_type_string(self):
        """Test inferring string type."""
        assert infer_type_from_value("hello") == "string"
        assert infer_type_from_value("2024-01-01") == "string"


class TestSchemaInference:
    """Test schema inference."""

    def test_infer_schema_basic(self):
        """Test basic schema inference."""
        headers = ["Name", "Age"]
        sample_data = [
            ["John", "30"],
            ["Jane", "25"],
        ]
        schema = infer_schema_from_data(headers, sample_data)

        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]

    def test_infer_schema_mixed_types(self):
        """Test schema inference with mixed types."""
        headers = ["Value"]
        sample_data = [
            ["100"],
            ["200"],
            ["text"],
        ]
        schema = infer_schema_from_data(headers, sample_data)

        # Mixed types should default to string
        assert "value" in schema["properties"]


class TestNormalizeRow:
    """Test row normalization."""

    def test_normalize_row_basic(self):
        """Test basic row normalization."""
        row = ["John", "john@example.com", "active"]
        headers = ["Name", "Email", "Status"]

        record = normalize_row(row, headers, row_number=2)

        assert record["_row_number"] == 2
        assert record["name"] == "John"
        assert record["email"] == "john@example.com"
        assert record["status"] == "active"

    def test_normalize_row_missing_values(self):
        """Test normalization with missing values."""
        row = ["John"]
        headers = ["Name", "Email", "Status"]

        record = normalize_row(row, headers, row_number=2)

        assert record["name"] == "John"
        assert record["email"] is None
        assert record["status"] is None


class TestParseSpreadsheetId:
    """Test spreadsheet ID parsing."""

    def test_parse_raw_id(self):
        """Test parsing raw spreadsheet ID."""
        result = parse_spreadsheet_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        assert result == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    def test_parse_from_url(self):
        """Test parsing ID from URL."""
        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
        result = parse_spreadsheet_id(url)
        assert result == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    def test_parse_invalid_raises_error(self):
        """Test that invalid ID raises error."""
        with pytest.raises(InvalidRequestError):
            parse_spreadsheet_id("invalid id with spaces!@#")


class TestFormatBytes:
    """Test byte formatting."""

    def test_format_bytes(self):
        """Test formatting bytes to human readable."""
        assert "B" in format_bytes(100)
        assert "KB" in format_bytes(1024)
        assert "MB" in format_bytes(1024 * 1024)


class TestGetTimestamp:
    """Test timestamp generation."""

    def test_get_timestamp_format(self):
        """Test timestamp format."""
        timestamp = get_timestamp()
        assert "Z" in timestamp
        assert "T" in timestamp


class TestExceptions:
    """Test custom exceptions."""

    def test_google_sheets_error(self):
        """Test GoogleSheetsError."""
        error = GoogleSheetsError("Test error", status_code=500)
        assert error.message == "Test error"
        assert error.status_code == 500

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Auth failed")
        assert error.status_code == 401

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Rate limit", retry_after=60.0)
        assert error.status_code == 429
        assert error.retry_after == 60.0

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Not found")
        assert error.status_code == 404
