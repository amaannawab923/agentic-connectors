"""
Connection tests for Google Sheets connector.

These tests verify that the connector can establish connections
using mocked Google API credentials.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.config import GoogleSheetsConfig
from src.connector import GoogleSheetsConnector
from src.client import GoogleSheetsClient
from src.auth import GoogleSheetsAuthenticator


class TestConnectionCheck:
    """Test connection checking with mocked API."""

    def test_successful_connection_check(
        self,
        valid_service_account_config,
        spreadsheet_metadata_fixture
    ):
        """Test that connection check succeeds with valid credentials and mocked client."""
        # Mock at the client level to avoid Google SDK complexity
        with patch.object(GoogleSheetsClient, 'check_connection') as mock_check:
            mock_check.return_value = (
                True,
                "Successfully connected to spreadsheet 'Test Spreadsheet'",
                {
                    "spreadsheet_id": spreadsheet_metadata_fixture["spreadsheetId"],
                    "title": spreadsheet_metadata_fixture["properties"]["title"],
                    "sheet_count": len(spreadsheet_metadata_fixture["sheets"])
                }
            )

            config = GoogleSheetsConfig(**valid_service_account_config)
            connector = GoogleSheetsConnector(config)

            status = connector.check()

            assert status.connected is True
            assert status.spreadsheet_title == "Test Spreadsheet"
            assert status.sheet_count == 3

    def test_connection_check_with_oauth2(
        self,
        valid_oauth2_config,
        spreadsheet_metadata_fixture
    ):
        """Test connection check with OAuth2 credentials."""
        with patch.object(GoogleSheetsClient, 'check_connection') as mock_check:
            mock_check.return_value = (
                True,
                "Successfully connected",
                {
                    "spreadsheet_id": spreadsheet_metadata_fixture["spreadsheetId"],
                    "title": spreadsheet_metadata_fixture["properties"]["title"],
                    "sheet_count": len(spreadsheet_metadata_fixture["sheets"])
                }
            )

            config = GoogleSheetsConfig(**valid_oauth2_config)
            connector = GoogleSheetsConnector(config)

            status = connector.check()
            assert status.connected is True

    def test_connection_check_with_api_key(
        self,
        valid_api_key_config,
        spreadsheet_metadata_fixture
    ):
        """Test connection check with API key credentials."""
        with patch.object(GoogleSheetsClient, 'check_connection') as mock_check:
            mock_check.return_value = (
                True,
                "Successfully connected",
                {
                    "spreadsheet_id": spreadsheet_metadata_fixture["spreadsheetId"],
                    "title": spreadsheet_metadata_fixture["properties"]["title"],
                    "sheet_count": len(spreadsheet_metadata_fixture["sheets"])
                }
            )

            config = GoogleSheetsConfig(**valid_api_key_config)
            connector = GoogleSheetsConnector(config)

            status = connector.check()
            assert status.connected is True


class TestConnectionFailures:
    """Test connection failure scenarios."""

    def test_authentication_failure(
        self,
        valid_service_account_config,
        error_401_fixture
    ):
        """Test that authentication failure is handled gracefully."""
        from src.utils import AuthenticationError

        with patch.object(GoogleSheetsClient, 'check_connection') as mock_check:
            mock_check.return_value = (
                False,
                "Authentication failed: 401 Unauthorized",
                None
            )

            config = GoogleSheetsConfig(**valid_service_account_config)
            connector = GoogleSheetsConnector(config)

            status = connector.check()
            assert status.connected is False
            assert status.error is not None

    def test_not_found_failure(
        self,
        valid_service_account_config,
        error_404_fixture
    ):
        """Test that not found error is handled gracefully."""
        with patch.object(GoogleSheetsClient, 'check_connection') as mock_check:
            mock_check.return_value = (
                False,
                "Spreadsheet not found: 404",
                None
            )

            config = GoogleSheetsConfig(**valid_service_account_config)
            connector = GoogleSheetsConnector(config)

            status = connector.check()
            assert status.connected is False

    def test_connection_raises_exception(
        self,
        valid_service_account_config
    ):
        """Test that exceptions are handled gracefully."""
        from src.utils import GoogleSheetsError

        with patch.object(GoogleSheetsClient, 'check_connection') as mock_check:
            mock_check.side_effect = GoogleSheetsError("Connection timeout")

            config = GoogleSheetsConfig(**valid_service_account_config)
            connector = GoogleSheetsConnector(config)

            status = connector.check()
            assert status.connected is False
            assert "timeout" in status.error.lower()


class TestClientRateLimiter:
    """Test rate limiter functionality."""

    def test_rate_limiter_init(self):
        """Test that rate limiter initializes correctly."""
        from src.client import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.window_size == 60.0

    def test_rate_limiter_acquire(self):
        """Test that rate limiter acquire works."""
        from src.client import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Should succeed without delay
        wait_time = limiter.acquire()
        assert wait_time == 0.0

    def test_rate_limiter_reset(self):
        """Test that rate limiter reset works."""
        from src.client import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)
        limiter.acquire()
        limiter.reset()
        assert len(limiter.timestamps) == 0


class TestRetryHandler:
    """Test retry handler functionality."""

    def test_retry_handler_init(self):
        """Test that retry handler initializes correctly."""
        from src.client import RetryHandler

        handler = RetryHandler(max_retries=5, base_delay=1.0)
        assert handler.max_retries == 5
        assert handler.base_delay == 1.0

    def test_calculate_delay_exponential(self):
        """Test that delay calculation is exponential."""
        from src.client import RetryHandler

        handler = RetryHandler(max_retries=5, base_delay=1.0, jitter_factor=0)

        # Without jitter, delays should be 1, 2, 4, 8, 16...
        delay0 = handler.calculate_delay(0)
        delay1 = handler.calculate_delay(1)
        delay2 = handler.calculate_delay(2)

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

    def test_should_retry_on_429(self):
        """Test that retry is suggested on 429 error."""
        from src.client import RetryHandler
        from googleapiclient.errors import HttpError
        import httplib2

        handler = RetryHandler(max_retries=5)
        mock_response = httplib2.Response({'status': 429})
        error = HttpError(mock_response, b'Rate limit exceeded')

        assert handler.should_retry(0, error) is True
        assert handler.should_retry(5, error) is False  # Max retries exceeded

    def test_should_retry_on_server_error(self):
        """Test that retry is suggested on 5xx errors."""
        from src.client import RetryHandler
        from googleapiclient.errors import HttpError
        import httplib2

        handler = RetryHandler(max_retries=5)

        for status in [500, 502, 503, 504]:
            mock_response = httplib2.Response({'status': status})
            error = HttpError(mock_response, b'Server error')
            assert handler.should_retry(0, error) is True

    def test_should_not_retry_on_400(self):
        """Test that retry is not suggested on 400 error."""
        from src.client import RetryHandler
        from googleapiclient.errors import HttpError
        import httplib2

        handler = RetryHandler(max_retries=5)
        mock_response = httplib2.Response({'status': 400})
        error = HttpError(mock_response, b'Bad request')

        assert handler.should_retry(0, error) is False
