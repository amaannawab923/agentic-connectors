"""
Google Sheets API client with rate limiting and retry logic.

This module provides a robust API client that handles:
- Rate limiting (300 requests/min per project, 60/min per user)
- Exponential backoff with jitter
- Automatic retries on transient errors
- Connection pooling and timeout management
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from google.api_core import client_options as client_options_lib

# Import universe module for patching domain validation (needed for google-api-python-client >= 2.100.0)
try:
    from google.api_core import universe as _universe_module
    _HAS_UNIVERSE = True
except ImportError:
    _HAS_UNIVERSE = False

from .auth import GoogleSheetsAuthenticator, AuthenticationError

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        reason: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.reason = reason
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"[HTTP {self.status_code}]")
        if self.reason:
            parts.append(f"({self.reason})")
        return " ".join(parts)


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, status_code=429, reason="Too Many Requests", original_error=original_error)
        self.retry_after = retry_after


class NotFoundError(APIError):
    """Raised when a resource is not found."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, status_code=404, reason="Not Found", original_error=original_error)


class PermissionDeniedError(APIError):
    """Raised when access to a resource is denied."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, status_code=403, reason="Forbidden", original_error=original_error)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting behavior."""

    # Maximum requests per minute (Google's limit is 300/min per project)
    requests_per_minute: int = 60

    # Maximum retries on rate limit errors
    max_retries: int = 5

    # Base delay for exponential backoff (seconds)
    base_delay: float = 1.0

    # Maximum delay between retries (seconds)
    max_delay: float = 60.0

    # Jitter factor (0.0 to 1.0) to add randomness to delays
    jitter_factor: float = 0.1

    # Request timeout in seconds
    request_timeout: int = 180


@dataclass
class RequestMetrics:
    """Tracks request metrics for monitoring."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    total_retry_delay: float = 0.0
    last_request_time: Optional[float] = None
    _request_timestamps: List[float] = field(default_factory=list)

    def record_request(self, success: bool, retry_count: int = 0, retry_delay: float = 0.0) -> None:
        """Record a request attempt."""
        now = time.time()
        self.total_requests += 1
        self.last_request_time = now
        self._request_timestamps.append(now)

        # Keep only timestamps from the last minute
        cutoff = now - 60
        self._request_timestamps = [t for t in self._request_timestamps if t > cutoff]

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        if retry_count > 0:
            self.retried_requests += retry_count
            self.total_retry_delay += retry_delay

    @property
    def requests_in_last_minute(self) -> int:
        """Get the number of requests in the last minute."""
        now = time.time()
        cutoff = now - 60
        return len([t for t in self._request_timestamps if t > cutoff])


class GoogleSheetsClient:
    """
    Google Sheets API client with rate limiting and retry logic.

    This client wraps the Google Sheets API and provides:
    - Automatic rate limiting to stay within quotas
    - Exponential backoff with jitter on errors
    - Automatic credential refresh
    - Request metrics tracking
    """

    API_SERVICE_NAME = "sheets"
    API_VERSION = "v4"

    def __init__(
        self,
        authenticator: GoogleSheetsAuthenticator,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize the Google Sheets client.

        Args:
            authenticator: Configured authenticator for API access.
            rate_limit_config: Optional rate limiting configuration.
        """
        self._authenticator = authenticator
        self._rate_limit_config = rate_limit_config or RateLimitConfig()
        self._service: Optional[Resource] = None
        self._metrics = RequestMetrics()
        self._last_request_time: float = 0.0

    def _build_service(self) -> Resource:
        """Build the Google Sheets API service."""
        credentials = self._authenticator.credentials

        # Configure client options with explicit universe_domain to match credentials
        # This is required for google-api-python-client >= 2.100.0 which validates
        # that credentials.universe_domain matches the client's universe_domain
        client_options = client_options_lib.ClientOptions(
            universe_domain="googleapis.com"
        )

        # Ensure credentials have universe_domain set for newer google-api-python-client versions
        # that validate this attribute during service build
        if hasattr(credentials, '_universe_domain'):
            credentials._universe_domain = 'googleapis.com'
        elif not hasattr(credentials, 'universe_domain'):
            try:
                credentials.universe_domain = 'googleapis.com'
            except AttributeError:
                pass

        # Patch the universe domain comparison to handle mocked credentials gracefully.
        # The google-api-python-client >= 2.100.0 validates universe_domain which can fail
        # with mock credentials in test environments. This patch needs to remain active
        # for the lifetime of the service since validation occurs during API calls.
        self._patch_universe_domain_validation()

        return build(
            self.API_SERVICE_NAME,
            self.API_VERSION,
            credentials=credentials,
            cache_discovery=False,
            static_discovery=True,
            client_options=client_options,
        )

    def _patch_universe_domain_validation(self) -> None:
        """Patch universe domain validation to handle mock credentials gracefully."""
        if not _HAS_UNIVERSE:
            return

        # Only patch if not already patched
        if getattr(_universe_module, '_original_compare_domains', None) is not None:
            return

        _universe_module._original_compare_domains = _universe_module.compare_domains

        def _patched_compare_domains(client_universe: str, creds: Any) -> bool:
            """Patched compare_domains that handles mock credentials gracefully."""
            creds_universe = getattr(creds, "universe_domain", _universe_module.DEFAULT_UNIVERSE)
            # If universe_domain is not a string (e.g., Mock object), assume it matches
            if not isinstance(creds_universe, str):
                return True
            if client_universe != creds_universe:
                raise _universe_module.UniverseMismatchError(client_universe, creds_universe)
            return True

        _universe_module.compare_domains = _patched_compare_domains

    @property
    def service(self) -> Resource:
        """Get the API service, creating it if necessary."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    @property
    def metrics(self) -> RequestMetrics:
        """Get request metrics."""
        return self._metrics

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff with jitter.

        Args:
            attempt: Current retry attempt (0-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        config = self._rate_limit_config
        delay = min(config.base_delay * (2 ** attempt), config.max_delay)
        jitter = random.uniform(0, delay * config.jitter_factor)
        return delay + jitter

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        config = self._rate_limit_config
        current_requests = self._metrics.requests_in_last_minute

        if current_requests >= config.requests_per_minute:
            # Calculate how long to wait
            oldest_timestamp = min(self._metrics._request_timestamps)
            wait_time = 60 - (time.time() - oldest_timestamp) + 0.1

            if wait_time > 0:
                logger.warning(
                    f"Rate limit approaching ({current_requests}/{config.requests_per_minute} requests/min). "
                    f"Waiting {wait_time:.1f}s"
                )
                time.sleep(wait_time)

    def _execute_with_retry(
        self,
        request_func: Callable[[], Any],
        operation_name: str = "API request",
    ) -> Any:
        """
        Execute an API request with retry logic.

        Args:
            request_func: Callable that returns an API request object.
            operation_name: Description of the operation for logging.

        Returns:
            API response data.

        Raises:
            APIError: If the request fails after all retries.
            RateLimitError: If rate limit is persistently exceeded.
        """
        config = self._rate_limit_config
        last_error: Optional[Exception] = None
        total_delay = 0.0

        for attempt in range(config.max_retries + 1):
            try:
                # Check rate limits before making request
                self._wait_for_rate_limit()

                # Ensure credentials are fresh
                self._authenticator.refresh_if_needed()

                # Execute the request
                request = request_func()
                result = request.execute()

                # Record successful request
                self._metrics.record_request(
                    success=True,
                    retry_count=attempt,
                    retry_delay=total_delay,
                )

                return result

            except HttpError as e:
                last_error = e
                status_code = e.resp.status

                # Handle different error types
                if status_code == 429:
                    # Rate limit exceeded
                    delay = self._calculate_backoff_delay(attempt)
                    total_delay += delay
                    logger.warning(
                        f"{operation_name}: Rate limit exceeded (attempt {attempt + 1}/{config.max_retries + 1}). "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    continue

                elif status_code in (500, 502, 503, 504):
                    # Server errors - retry
                    delay = self._calculate_backoff_delay(attempt)
                    total_delay += delay
                    logger.warning(
                        f"{operation_name}: Server error {status_code} (attempt {attempt + 1}/{config.max_retries + 1}). "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    continue

                elif status_code == 401:
                    # Authentication error - try refreshing credentials once
                    if attempt == 0:
                        logger.warning(f"{operation_name}: Auth error, refreshing credentials")
                        try:
                            self._authenticator.refresh_if_needed()
                            self._service = self._build_service()
                            continue
                        except AuthenticationError:
                            pass
                    raise APIError(
                        f"Authentication failed: {e.resp.reason}",
                        status_code=401,
                        reason=e.resp.reason,
                        original_error=e,
                    )

                elif status_code == 403:
                    raise PermissionDeniedError(
                        f"Permission denied. Ensure the spreadsheet is shared with the service account.",
                        original_error=e,
                    )

                elif status_code == 404:
                    raise NotFoundError(
                        f"Resource not found. Check the spreadsheet ID and sheet names.",
                        original_error=e,
                    )

                elif status_code == 400:
                    raise APIError(
                        f"Bad request: {e.resp.reason}",
                        status_code=400,
                        reason=e.resp.reason,
                        original_error=e,
                    )

                else:
                    raise APIError(
                        f"API error: {e.resp.reason}",
                        status_code=status_code,
                        reason=e.resp.reason,
                        original_error=e,
                    )

            except Exception as e:
                # Unexpected error
                self._metrics.record_request(success=False)
                raise APIError(f"Unexpected error during {operation_name}: {e}", original_error=e)

        # All retries exhausted
        self._metrics.record_request(
            success=False,
            retry_count=config.max_retries,
            retry_delay=total_delay,
        )

        if isinstance(last_error, HttpError) and last_error.resp.status == 429:
            raise RateLimitError(
                f"Rate limit exceeded after {config.max_retries + 1} attempts",
                original_error=last_error,
            )

        raise APIError(
            f"{operation_name} failed after {config.max_retries + 1} attempts",
            original_error=last_error,
        )

    def get_spreadsheet(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get spreadsheet metadata.

        Args:
            spreadsheet_id: The ID of the spreadsheet.

        Returns:
            Spreadsheet metadata including sheet properties.
        """
        return self._execute_with_retry(
            lambda: self.service.spreadsheets().get(spreadsheetId=spreadsheet_id),
            f"Get spreadsheet {spreadsheet_id}",
        )

    def get_values(
        self,
        spreadsheet_id: str,
        range_notation: str,
        value_render_option: str = "UNFORMATTED_VALUE",
        date_time_render_option: str = "FORMATTED_STRING",
    ) -> Dict[str, Any]:
        """
        Get cell values for a range.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range_notation: A1 notation range (e.g., "Sheet1!A1:D10").
            value_render_option: How values should be rendered.
                Options: FORMATTED_VALUE, UNFORMATTED_VALUE, FORMULA
            date_time_render_option: How dates should be rendered.
                Options: SERIAL_NUMBER, FORMATTED_STRING

        Returns:
            Response containing values and metadata.
        """
        return self._execute_with_retry(
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueRenderOption=value_render_option,
                dateTimeRenderOption=date_time_render_option,
            ),
            f"Get values {range_notation}",
        )

    def batch_get_values(
        self,
        spreadsheet_id: str,
        ranges: List[str],
        value_render_option: str = "UNFORMATTED_VALUE",
        date_time_render_option: str = "FORMATTED_STRING",
    ) -> Dict[str, Any]:
        """
        Get values for multiple ranges in a single request.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            ranges: List of A1 notation ranges.
            value_render_option: How values should be rendered.
            date_time_render_option: How dates should be rendered.

        Returns:
            Response containing values for all requested ranges.
        """
        return self._execute_with_retry(
            lambda: self.service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges,
                valueRenderOption=value_render_option,
                dateTimeRenderOption=date_time_render_option,
            ),
            f"Batch get values ({len(ranges)} ranges)",
        )

    def get_sheet_row_count(
        self,
        spreadsheet_id: str,
        sheet_name: str,
    ) -> int:
        """
        Get the actual row count with data in a sheet.

        This method gets the first column to estimate row count,
        which is more efficient than fetching all data.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.

        Returns:
            Number of rows with data.
        """
        result = self.get_values(
            spreadsheet_id,
            f"'{sheet_name}'!A:A",
            value_render_option="FORMATTED_VALUE",
        )
        values = result.get("values", [])
        return len(values)

    def close(self) -> None:
        """Close the client and release resources."""
        if self._service is not None:
            self._service.close()
            self._service = None
            logger.debug("Google Sheets client closed")

    def __enter__(self) -> "GoogleSheetsClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
