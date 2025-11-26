"""
Google Sheets API client with rate limiting and retry logic.

Handles all API interactions with proper error handling and
exponential backoff for rate limits.
"""

import random
import time
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from src.auth import GoogleSheetsAuthenticator, AuthenticationError


class GoogleSheetsAPIError(Exception):
    """Base exception for Google Sheets API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class RateLimitError(GoogleSheetsAPIError):
    """Raised when rate limit is exceeded."""

    pass


class SpreadsheetNotFoundError(GoogleSheetsAPIError):
    """Raised when spreadsheet is not found."""

    pass


class AccessDeniedError(GoogleSheetsAPIError):
    """Raised when access to spreadsheet is denied."""

    pass


class InvalidRequestError(GoogleSheetsAPIError):
    """Raised for invalid API requests."""

    pass


class GoogleSheetsClient:
    """
    Google Sheets API client with rate limiting and retry logic.

    Implements exponential backoff for rate limits and transient errors.
    Provides methods for all common spreadsheet operations.
    """

    # Rate limit: 60 requests per minute per user
    DEFAULT_REQUESTS_PER_MINUTE = 60
    # Default batch size for row fetching
    DEFAULT_BATCH_SIZE = 200
    # Maximum retries for transient errors
    MAX_RETRIES = 5
    # Base delay for exponential backoff (seconds)
    BASE_DELAY = 1.0
    # Maximum delay between retries (seconds)
    MAX_DELAY = 60.0

    def __init__(
        self,
        authenticator: GoogleSheetsAuthenticator,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_retries: int = MAX_RETRIES,
    ):
        """
        Initialize the Google Sheets client.

        Args:
            authenticator: Authentication handler for API access.
            requests_per_minute: Rate limit for API requests.
            batch_size: Number of rows to fetch per API request.
            max_retries: Maximum number of retry attempts.
        """
        self._authenticator = authenticator
        self._requests_per_minute = requests_per_minute
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._service: Optional[Resource] = None
        self._last_request_time: float = 0
        self._request_interval = 60.0 / requests_per_minute

    def _get_service(self) -> Resource:
        """
        Get or create the Google Sheets API service.

        Returns:
            Google Sheets API service resource.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if self._service is None:
            credentials = self._authenticator.get_credentials()
            self._service = build("sheets", "v4", credentials=credentials)
        return self._service

    def _rate_limit(self) -> None:
        """
        Enforce rate limiting by waiting if necessary.

        Ensures we don't exceed the configured requests per minute.
        """
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self._request_interval:
            sleep_time = self._request_interval - elapsed
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current retry attempt number (0-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        delay = min(
            self.BASE_DELAY * (2**attempt) + random.uniform(0, 1),
            self.MAX_DELAY,
        )
        return delay

    def _handle_http_error(self, error: HttpError) -> None:
        """
        Convert HttpError to appropriate custom exception.

        Args:
            error: The HttpError from the API.

        Raises:
            GoogleSheetsAPIError: Appropriate subclass based on error code.
        """
        status_code = error.resp.status
        error_message = str(error)

        if status_code == 400:
            raise InvalidRequestError(
                f"Invalid request: {error_message}",
                status_code=status_code,
            )
        elif status_code == 401:
            raise AuthenticationError(
                "Invalid or expired credentials",
                {"status_code": status_code},
            )
        elif status_code == 403:
            raise AccessDeniedError(
                "Access denied. Check spreadsheet sharing settings.",
                status_code=status_code,
            )
        elif status_code == 404:
            raise SpreadsheetNotFoundError(
                "Spreadsheet not found. Verify the spreadsheet ID.",
                status_code=status_code,
            )
        elif status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded",
                status_code=status_code,
            )
        else:
            raise GoogleSheetsAPIError(
                f"API error: {error_message}",
                status_code=status_code,
            )

    def _execute_with_retry(self, request) -> Any:
        """
        Execute an API request with retry logic.

        Implements exponential backoff for rate limits and transient errors.

        Args:
            request: The API request to execute.

        Returns:
            The API response.

        Raises:
            GoogleSheetsAPIError: If all retries fail.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                self._rate_limit()
                return request.execute()

            except HttpError as e:
                status_code = e.resp.status

                # Retry on rate limits and server errors
                if status_code in [429, 500, 503]:
                    last_error = e
                    if attempt < self._max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        time.sleep(delay)
                        continue
                    else:
                        if status_code == 429:
                            raise RateLimitError(
                                f"Rate limit exceeded after {self._max_retries} retries",
                                status_code=status_code,
                            )
                        raise GoogleSheetsAPIError(
                            f"Server error after {self._max_retries} retries",
                            status_code=status_code,
                        )

                # Non-retryable errors
                self._handle_http_error(e)

        # Should not reach here, but handle edge case
        if last_error:
            raise GoogleSheetsAPIError(
                f"Request failed after {self._max_retries} retries: {str(last_error)}"
            )

    def get_spreadsheet_metadata(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get spreadsheet metadata including sheet information.

        Args:
            spreadsheet_id: The ID of the spreadsheet.

        Returns:
            Spreadsheet metadata dictionary.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        service = self._get_service()
        request = service.spreadsheets().get(spreadsheetId=spreadsheet_id)
        return self._execute_with_retry(request)

    def get_sheet_names(self, spreadsheet_id: str) -> List[str]:
        """
        Get list of sheet names in the spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet.

        Returns:
            List of sheet names.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        metadata = self.get_spreadsheet_metadata(spreadsheet_id)
        sheets = metadata.get("sheets", [])
        return [sheet["properties"]["title"] for sheet in sheets]

    def get_sheet_properties(
        self, spreadsheet_id: str, sheet_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get properties for a specific sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.

        Returns:
            Sheet properties dictionary or None if not found.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        metadata = self.get_spreadsheet_metadata(spreadsheet_id)
        for sheet in metadata.get("sheets", []):
            if sheet["properties"]["title"] == sheet_name:
                return sheet["properties"]
        return None

    def get_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        value_render_option: str = "FORMATTED_VALUE",
        date_time_render_option: str = "FORMATTED_STRING",
    ) -> List[List[Any]]:
        """
        Get values from a spreadsheet range.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range_name: A1 notation range (e.g., "Sheet1!A1:Z100").
            value_render_option: How values should be rendered.
            date_time_render_option: How dates should be rendered.

        Returns:
            2D list of values.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        service = self._get_service()
        request = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption=value_render_option,
            dateTimeRenderOption=date_time_render_option,
        )
        result = self._execute_with_retry(request)
        return result.get("values", [])

    def batch_get_values(
        self,
        spreadsheet_id: str,
        ranges: List[str],
        value_render_option: str = "FORMATTED_VALUE",
        date_time_render_option: str = "FORMATTED_STRING",
    ) -> Dict[str, List[List[Any]]]:
        """
        Get values from multiple ranges in a single request.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            ranges: List of A1 notation ranges.
            value_render_option: How values should be rendered.
            date_time_render_option: How dates should be rendered.

        Returns:
            Dictionary mapping range names to values.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        service = self._get_service()
        request = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=ranges,
            valueRenderOption=value_render_option,
            dateTimeRenderOption=date_time_render_option,
        )
        result = self._execute_with_retry(request)

        values_by_range = {}
        for value_range in result.get("valueRanges", []):
            range_key = value_range.get("range", "")
            values_by_range[range_key] = value_range.get("values", [])

        return values_by_range

    def get_headers(self, spreadsheet_id: str, sheet_name: str) -> List[str]:
        """
        Get the header row (first row) from a sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.

        Returns:
            List of header values.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        # Quote sheet name to handle special characters
        safe_sheet_name = f"'{sheet_name}'" if " " in sheet_name else sheet_name
        range_name = f"{safe_sheet_name}!1:1"
        values = self.get_values(spreadsheet_id, range_name)
        return values[0] if values else []

    def get_rows_batch(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        start_row: int,
        batch_size: Optional[int] = None,
    ) -> List[List[Any]]:
        """
        Get a batch of rows from a sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.
            start_row: 1-indexed row number to start from.
            batch_size: Number of rows to fetch (defaults to instance batch_size).

        Returns:
            List of rows, each row being a list of values.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        batch_size = batch_size or self._batch_size
        end_row = start_row + batch_size - 1

        # Quote sheet name to handle special characters
        safe_sheet_name = f"'{sheet_name}'" if " " in sheet_name else sheet_name
        range_name = f"{safe_sheet_name}!A{start_row}:{end_row}"

        return self.get_values(spreadsheet_id, range_name)

    def get_all_values(
        self, spreadsheet_id: str, sheet_name: str
    ) -> List[List[Any]]:
        """
        Get all values from a sheet, including header.

        Uses batched fetching for large sheets.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.

        Returns:
            List of all rows including header.

        Raises:
            GoogleSheetsAPIError: If the request fails.
        """
        all_values: List[List[Any]] = []
        start_row = 1

        while True:
            batch = self.get_rows_batch(
                spreadsheet_id, sheet_name, start_row, self._batch_size
            )

            if not batch:
                break

            all_values.extend(batch)

            # If we got fewer rows than requested, we've reached the end
            if len(batch) < self._batch_size:
                break

            start_row += self._batch_size

        return all_values

    def check_connection(self, spreadsheet_id: str) -> bool:
        """
        Verify connection to the spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet.

        Returns:
            True if connection is successful.

        Raises:
            GoogleSheetsAPIError: If connection fails.
        """
        try:
            self.get_spreadsheet_metadata(spreadsheet_id)
            return True
        except GoogleSheetsAPIError:
            raise

    @property
    def batch_size(self) -> int:
        """Get the configured batch size."""
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value: int) -> None:
        """Set the batch size."""
        if value < 1:
            raise ValueError("Batch size must be at least 1")
        if value > 1000:
            raise ValueError("Batch size cannot exceed 1000")
        self._batch_size = value
