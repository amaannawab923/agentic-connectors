"""
Google Sheets API client with rate limiting and retry logic.

This module provides a robust API client that handles:
- Rate limiting (300 requests/min project, 60 requests/min user)
- Exponential backoff with jitter
- Error handling and retries
- Request throttling
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import random
import logging
from collections import deque
from threading import Lock
from dataclasses import dataclass

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from .auth import GoogleSheetsAuthenticator
from .config import GoogleSheetsConfig
from .utils import (
    GoogleSheetsError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    InvalidRequestError,
    ServerError,
    build_range_notation,
)

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60  # Per-user limit
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 64.0
    jitter_factor: float = 0.5


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.

    Implements rate limiting to stay within Google Sheets API limits.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        window_size_seconds: float = 60.0
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            window_size_seconds: Size of the sliding window
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size_seconds
        self.timestamps: deque = deque()
        self._lock = Lock()

    def acquire(self) -> float:
        """
        Acquire a rate limit token.

        Returns:
            Time waited in seconds

        This method blocks until a token is available.
        """
        with self._lock:
            now = time.time()
            window_start = now - self.window_size

            # Remove timestamps outside the window
            while self.timestamps and self.timestamps[0] < window_start:
                self.timestamps.popleft()

            # Check if we need to wait
            if len(self.timestamps) >= self.requests_per_minute:
                # Calculate wait time
                oldest = self.timestamps[0]
                wait_time = oldest - window_start
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    # Clean up after waiting
                    now = time.time()
                    window_start = now - self.window_size
                    while self.timestamps and self.timestamps[0] < window_start:
                        self.timestamps.popleft()

            # Record this request
            self.timestamps.append(time.time())
            return 0.0

    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self.timestamps.clear()


class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.
    """

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 64.0,
        jitter_factor: float = 0.5
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            jitter_factor: Jitter factor (0-1)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a retry attempt.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.base_delay * (2 ** attempt)

        # Apply max delay cap
        delay = min(delay, self.max_delay)

        # Add jitter
        jitter = delay * self.jitter_factor * random.random()
        delay += jitter

        return delay

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """
        Determine if a request should be retried.

        Args:
            attempt: Current attempt number
            error: The exception that occurred

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False

        if isinstance(error, HttpError):
            status = error.resp.status
            # Retry on rate limit or server errors
            return status in [429, 500, 502, 503, 504]

        # Retry on connection errors
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True

        return False


class GoogleSheetsClient:
    """
    Google Sheets API client with built-in rate limiting and retry logic.

    This client provides methods for interacting with the Google Sheets API
    while respecting rate limits and handling transient errors.
    """

    def __init__(self, config: GoogleSheetsConfig):
        """
        Initialize the Google Sheets client.

        Args:
            config: Google Sheets configuration
        """
        self.config = config
        self.authenticator = GoogleSheetsAuthenticator(config)
        self._service: Optional[Resource] = None

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=60  # Per-user limit
        )

        # Initialize retry handler
        self.retry_handler = RetryHandler(
            max_retries=config.max_retries,
            base_delay=config.retry_delay,
            max_delay=64.0,
            jitter_factor=0.5
        )

    @property
    def service(self) -> Resource:
        """
        Get the Google Sheets API service.

        Returns:
            Google Sheets API service resource
        """
        if self._service is None:
            self._service = self.authenticator.build_service()
        return self._service

    def _handle_error(self, error: HttpError) -> None:
        """
        Convert HttpError to appropriate custom exception.

        Args:
            error: The HttpError from the API

        Raises:
            Appropriate custom exception
        """
        status = error.resp.status
        message = str(error)

        if status == 400:
            raise InvalidRequestError(message)
        elif status == 401:
            raise AuthenticationError(message)
        elif status == 403:
            raise AuthenticationError(
                f"Access denied. Ensure the spreadsheet is shared with the "
                f"service account email. Original error: {message}"
            )
        elif status == 404:
            raise NotFoundError(message)
        elif status == 429:
            raise RateLimitError(message)
        elif status >= 500:
            raise ServerError(message, status)
        else:
            raise GoogleSheetsError(message, status)

    def _execute_with_retry(self, request: Any) -> Dict[str, Any]:
        """
        Execute an API request with rate limiting and retry logic.

        Args:
            request: The API request to execute

        Returns:
            API response as dictionary

        Raises:
            GoogleSheetsError: If all retries fail
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.retry_handler.max_retries + 1):
            try:
                # Apply rate limiting
                self.rate_limiter.acquire()

                # Execute request
                response = request.execute()
                return response

            except HttpError as e:
                last_error = e

                if not self.retry_handler.should_retry(attempt, e):
                    self._handle_error(e)

                delay = self.retry_handler.calculate_delay(attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.retry_handler.max_retries}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                time.sleep(delay)

            except Exception as e:
                last_error = e

                if not self.retry_handler.should_retry(attempt, e):
                    raise GoogleSheetsError(str(e))

                delay = self.retry_handler.calculate_delay(attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.retry_handler.max_retries}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                time.sleep(delay)

        # All retries exhausted
        if last_error:
            if isinstance(last_error, HttpError):
                self._handle_error(last_error)
            raise GoogleSheetsError(f"Max retries exceeded: {last_error}")

        raise GoogleSheetsError("Max retries exceeded")

    def get_spreadsheet_metadata(
        self,
        fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get spreadsheet metadata.

        Args:
            fields: Optional field mask for response

        Returns:
            Spreadsheet metadata
        """
        request = self.service.spreadsheets().get(
            spreadsheetId=self.config.spreadsheet_id,
            fields=fields or "spreadsheetId,properties,sheets.properties"
        )
        return self._execute_with_retry(request)

    def get_sheet_names(self) -> List[str]:
        """
        Get list of sheet names in the spreadsheet.

        Returns:
            List of sheet names
        """
        metadata = self.get_spreadsheet_metadata(
            fields="sheets.properties.title"
        )
        return [
            sheet["properties"]["title"]
            for sheet in metadata.get("sheets", [])
        ]

    def get_sheet_properties(self, sheet_name: str) -> Dict[str, Any]:
        """
        Get properties for a specific sheet.

        Args:
            sheet_name: Name of the sheet

        Returns:
            Sheet properties
        """
        metadata = self.get_spreadsheet_metadata(
            fields="sheets.properties"
        )

        for sheet in metadata.get("sheets", []):
            if sheet["properties"]["title"] == sheet_name:
                return sheet["properties"]

        raise NotFoundError(f"Sheet '{sheet_name}' not found")

    def get_values(
        self,
        range_notation: str,
        value_render_option: Optional[str] = None,
        date_time_render_option: Optional[str] = None
    ) -> List[List[Any]]:
        """
        Get values from a range.

        Args:
            range_notation: A1 notation range
            value_render_option: How to render values
            date_time_render_option: How to render dates

        Returns:
            List of rows (each row is a list of cell values)
        """
        request = self.service.spreadsheets().values().get(
            spreadsheetId=self.config.spreadsheet_id,
            range=range_notation,
            valueRenderOption=value_render_option or self.config.value_render_option,
            dateTimeRenderOption=date_time_render_option or self.config.date_time_render_option
        )
        response = self._execute_with_retry(request)
        return response.get("values", [])

    def batch_get_values(
        self,
        ranges: List[str],
        value_render_option: Optional[str] = None,
        date_time_render_option: Optional[str] = None
    ) -> Dict[str, List[List[Any]]]:
        """
        Get values from multiple ranges in a single request.

        Args:
            ranges: List of A1 notation ranges
            value_render_option: How to render values
            date_time_render_option: How to render dates

        Returns:
            Dictionary mapping range to values
        """
        request = self.service.spreadsheets().values().batchGet(
            spreadsheetId=self.config.spreadsheet_id,
            ranges=ranges,
            valueRenderOption=value_render_option or self.config.value_render_option,
            dateTimeRenderOption=date_time_render_option or self.config.date_time_render_option
        )
        response = self._execute_with_retry(request)

        result = {}
        for value_range in response.get("valueRanges", []):
            range_key = value_range.get("range", "")
            result[range_key] = value_range.get("values", [])

        return result

    def get_headers(self, sheet_name: str, header_row: int = 1) -> List[str]:
        """
        Get column headers from a sheet.

        Args:
            sheet_name: Name of the sheet
            header_row: Row number containing headers (1-indexed)

        Returns:
            List of header strings
        """
        range_notation = build_range_notation(
            sheet_name,
            start_row=header_row,
            end_row=header_row
        )
        values = self.get_values(range_notation)

        if not values:
            return []

        # Return first row as headers
        headers = values[0]

        # Ensure all headers are strings
        return [str(h) if h else "" for h in headers]

    def get_row_count(self, sheet_name: str) -> int:
        """
        Get the row count for a sheet.

        Args:
            sheet_name: Name of the sheet

        Returns:
            Number of rows in the sheet
        """
        props = self.get_sheet_properties(sheet_name)
        return props.get("gridProperties", {}).get("rowCount", 0)

    def get_column_count(self, sheet_name: str) -> int:
        """
        Get the column count for a sheet.

        Args:
            sheet_name: Name of the sheet

        Returns:
            Number of columns in the sheet
        """
        props = self.get_sheet_properties(sheet_name)
        return props.get("gridProperties", {}).get("columnCount", 0)

    def read_sheet_data(
        self,
        sheet_name: str,
        start_row: int = 2,
        batch_size: Optional[int] = None
    ) -> List[List[Any]]:
        """
        Read all data from a sheet (excluding header row).

        Args:
            sheet_name: Name of the sheet
            start_row: Row to start reading from (1-indexed)
            batch_size: Optional batch size for chunked reading

        Returns:
            List of rows
        """
        batch_size = batch_size or self.config.batch_size

        # Get total row count
        total_rows = self.get_row_count(sheet_name)

        if total_rows <= start_row:
            return []

        all_rows = []
        current_row = start_row

        while current_row <= total_rows:
            end_row = min(current_row + batch_size - 1, total_rows)

            range_notation = build_range_notation(
                sheet_name,
                start_row=current_row,
                end_row=end_row,
                start_col="A",
                end_col="ZZ"
            )

            rows = self.get_values(range_notation)

            if not rows:
                break

            all_rows.extend(rows)
            current_row = end_row + 1

            logger.debug(
                f"Read rows {current_row - len(rows)} to {current_row - 1} "
                f"from sheet '{sheet_name}'"
            )

        return all_rows

    def read_sheet_in_batches(
        self,
        sheet_name: str,
        start_row: int = 2,
        batch_size: Optional[int] = None
    ):
        """
        Generator that reads sheet data in batches.

        Args:
            sheet_name: Name of the sheet
            start_row: Row to start reading from (1-indexed)
            batch_size: Batch size for reading

        Yields:
            Batches of rows (List[List[Any]])
        """
        batch_size = batch_size or self.config.batch_size

        # Get total row count
        total_rows = self.get_row_count(sheet_name)

        if total_rows <= start_row:
            return

        current_row = start_row

        while current_row <= total_rows:
            end_row = min(current_row + batch_size - 1, total_rows)

            range_notation = build_range_notation(
                sheet_name,
                start_row=current_row,
                end_row=end_row,
                start_col="A",
                end_col="ZZ"
            )

            rows = self.get_values(range_notation)

            if not rows:
                break

            yield rows

            current_row = end_row + 1

    def check_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Check connection to the spreadsheet.

        Returns:
            Tuple of (success, message, metadata)
        """
        try:
            metadata = self.get_spreadsheet_metadata()

            title = metadata.get("properties", {}).get("title", "Unknown")
            sheet_count = len(metadata.get("sheets", []))

            return (
                True,
                f"Successfully connected to spreadsheet '{title}'",
                {
                    "spreadsheet_id": metadata.get("spreadsheetId"),
                    "title": title,
                    "sheet_count": sheet_count
                }
            )
        except GoogleSheetsError as e:
            return (False, str(e), None)
        except Exception as e:
            return (False, f"Connection failed: {e}", None)
