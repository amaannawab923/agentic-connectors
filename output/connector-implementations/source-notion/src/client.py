"""
Notion API client with rate limiting and retry logic.

This module provides a robust HTTP client for interacting with the Notion API,
handling rate limits, retries, pagination, and error handling.
"""

import logging
import time
from typing import Any, Dict, Generator, Optional, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import NotionAuthenticator, create_authenticator
from .config import NotionConfig
from .utils import (
    NotionError,
    NotionRateLimitError,
    NotionAuthenticationError,
    log_api_call,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """
    Token bucket rate limiter for API requests.

    Implements a simple rate limiting mechanism to stay within
    Notion's API limits (3 requests per second average).
    """

    def __init__(self, requests_per_second: float = 3.0):
        """
        Initialize the rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time: Optional[float] = None

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        if self.last_request_time is None:
            self.last_request_time = time.time()
            return

        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def record_request(self) -> None:
        """Record that a request was made."""
        self.last_request_time = time.time()


# =============================================================================
# Notion API Client
# =============================================================================


class NotionClient:
    """
    Robust HTTP client for the Notion API.

    Features:
    - Automatic rate limiting
    - Exponential backoff retry logic
    - Pagination support
    - Comprehensive error handling
    """

    BASE_URL = "https://api.notion.com/v1"

    def __init__(
        self,
        config: NotionConfig,
        authenticator: Optional[NotionAuthenticator] = None,
    ):
        """
        Initialize the Notion client.

        Args:
            config: NotionConfig with API settings
            authenticator: Optional pre-configured authenticator
        """
        self.config = config
        self.authenticator = authenticator or create_authenticator(config)
        self.rate_limiter = RateLimiter(config.requests_per_second)

        # Configure session with retry logic
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create a configured requests session.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        # Configure retry strategy for connection errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST", "PATCH", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.

        Returns:
            Dictionary of HTTP headers
        """
        # Ensure authentication is still valid
        self.authenticator.refresh_if_needed()
        return self.authenticator.get_auth_headers()

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate errors.

        Args:
            response: Response from the API

        Returns:
            Parsed JSON response

        Raises:
            NotionError: If the response indicates an error
        """
        if response.ok:
            return response.json()

        # Parse error and raise appropriate exception
        raise NotionError.from_response(response)

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/users/me')
            params: Query parameters
            json: JSON body for POST/PATCH requests
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            NotionError: If the request fails after all retries
        """
        url = f"{self.BASE_URL}{endpoint}"
        timeout = timeout or self.config.request_timeout

        for attempt in range(self.config.max_retries):
            # Rate limit
            self.rate_limiter.wait_if_needed()

            start_time = time.time()

            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    params=params,
                    json=json,
                    timeout=timeout,
                )

                duration_ms = (time.time() - start_time) * 1000
                log_api_call(method, endpoint, response.status_code, duration_ms)

                # Handle successful response
                if response.ok:
                    return response.json()

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", self.config.retry_base_delay)
                    )
                    wait_time = retry_after * (2 ** attempt)
                    logger.warning(
                        f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{self.config.max_retries}"
                    )
                    time.sleep(wait_time)
                    continue

                # Handle server errors
                if response.status_code >= 500:
                    wait_time = self.config.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"Server error {response.status_code}. Waiting {wait_time}s before retry {attempt + 1}/{self.config.max_retries}"
                    )
                    time.sleep(wait_time)
                    continue

                # Client errors (4xx) - don't retry
                raise NotionError.from_response(response)

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Request timeout. Retry {attempt + 1}/{self.config.max_retries}"
                )
                if attempt == self.config.max_retries - 1:
                    raise NotionError(
                        f"Request timed out after {timeout}s",
                        code="timeout",
                    )

            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Connection error: {e}. Retry {attempt + 1}/{self.config.max_retries}"
                )
                if attempt == self.config.max_retries - 1:
                    raise NotionError(
                        f"Connection failed: {e}",
                        code="connection_error",
                    )
                time.sleep(self.config.retry_base_delay * (2 ** attempt))

        raise NotionError(
            f"Max retries ({self.config.max_retries}) exceeded for {endpoint}",
            code="max_retries_exceeded",
        )

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Parsed JSON response
        """
        return self.request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint
            json: JSON body

        Returns:
            Parsed JSON response
        """
        return self.request("POST", endpoint, json=json)

    # =========================================================================
    # Pagination
    # =========================================================================

    def paginate(
        self,
        endpoint: str,
        method: str = "POST",
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Paginate through all results from an endpoint.

        Args:
            endpoint: API endpoint
            method: HTTP method (GET or POST)
            body: Request body (for POST)
            params: Query parameters (for GET)
            page_size: Items per page (default from config)

        Yields:
            Individual result items
        """
        page_size = page_size or self.config.page_size
        body = body.copy() if body else {}
        params = params.copy() if params else {}

        # Add page_size to appropriate location
        if method == "POST":
            body["page_size"] = page_size
        else:
            params["page_size"] = page_size

        next_cursor: Optional[str] = None
        total_items = 0

        while True:
            # Add cursor if we have one
            if next_cursor:
                if method == "POST":
                    body["start_cursor"] = next_cursor
                else:
                    params["start_cursor"] = next_cursor

            # Make request
            if method == "POST":
                response = self.post(endpoint, json=body)
            else:
                response = self.get(endpoint, params=params)

            # Yield results
            results = response.get("results", [])
            for item in results:
                yield item
                total_items += 1

            # Check for more pages
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")

            if not has_more or not next_cursor:
                logger.debug(f"Pagination complete. Total items: {total_items}")
                break

    # =========================================================================
    # User Endpoints
    # =========================================================================

    def get_current_user(self) -> Dict[str, Any]:
        """
        Get the current bot user.

        Returns:
            Bot user object
        """
        return self.get("/users/me")

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get a specific user by ID.

        Args:
            user_id: Notion user ID

        Returns:
            User object
        """
        return self.get(f"/users/{user_id}")

    def list_users(self) -> Generator[Dict[str, Any], None, None]:
        """
        List all users in the workspace.

        Yields:
            User objects
        """
        yield from self.paginate("/users", method="GET")

    # =========================================================================
    # Database Endpoints
    # =========================================================================

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """
        Get a database by ID.

        Args:
            database_id: Notion database ID

        Returns:
            Database object with schema
        """
        return self.get(f"/databases/{database_id}")

    def query_database(
        self,
        database_id: str,
        filter: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Query a database for pages.

        Args:
            database_id: Notion database ID
            filter: Filter conditions
            sorts: Sort specifications

        Yields:
            Page objects from the database
        """
        body: Dict[str, Any] = {}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts

        yield from self.paginate(
            f"/databases/{database_id}/query",
            method="POST",
            body=body,
        )

    # =========================================================================
    # Page Endpoints
    # =========================================================================

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Get a page by ID.

        Args:
            page_id: Notion page ID

        Returns:
            Page object with properties
        """
        return self.get(f"/pages/{page_id}")

    def get_page_property(
        self,
        page_id: str,
        property_id: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Get a specific property value from a page.

        This is useful for paginated properties like relations and rollups.

        Args:
            page_id: Notion page ID
            property_id: Property ID

        Yields:
            Property value items
        """
        yield from self.paginate(
            f"/pages/{page_id}/properties/{property_id}",
            method="GET",
        )

    # =========================================================================
    # Block Endpoints
    # =========================================================================

    def get_block(self, block_id: str) -> Dict[str, Any]:
        """
        Get a block by ID.

        Args:
            block_id: Notion block ID

        Returns:
            Block object
        """
        return self.get(f"/blocks/{block_id}")

    def get_block_children(
        self,
        block_id: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Get children of a block.

        Args:
            block_id: Notion block/page ID

        Yields:
            Child block objects
        """
        yield from self.paginate(
            f"/blocks/{block_id}/children",
            method="GET",
        )

    def get_all_blocks(
        self,
        page_id: str,
        max_depth: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Recursively get all blocks from a page.

        Args:
            page_id: Notion page ID
            max_depth: Maximum recursion depth (default from config)

        Yields:
            Block objects with nested children
        """
        max_depth = max_depth or self.config.max_block_depth

        def fetch_blocks(
            block_id: str,
            current_depth: int = 0,
        ) -> Generator[Dict[str, Any], None, None]:
            if current_depth > max_depth:
                return

            for block in self.get_block_children(block_id):
                # Add depth information
                block["_depth"] = current_depth

                yield block

                # Recursively fetch children if block has them
                if block.get("has_children", False):
                    for child in fetch_blocks(block["id"], current_depth + 1):
                        yield child

        yield from fetch_blocks(page_id)

    # =========================================================================
    # Search Endpoints
    # =========================================================================

    def search(
        self,
        query: str = "",
        filter: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Search across all accessible pages and databases.

        Args:
            query: Search query string
            filter: Filter by object type (page or database)
            sort: Sort direction

        Yields:
            Search result objects (pages and/or databases)
        """
        body: Dict[str, Any] = {}
        if query:
            body["query"] = query
        if filter:
            body["filter"] = filter
        if sort:
            body["sort"] = sort

        yield from self.paginate("/search", method="POST", body=body)

    def search_pages(self, query: str = "") -> Generator[Dict[str, Any], None, None]:
        """
        Search for pages only.

        Args:
            query: Search query string

        Yields:
            Page objects
        """
        yield from self.search(
            query=query,
            filter={"property": "object", "value": "page"},
        )

    def search_databases(
        self,
        query: str = "",
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Search for databases only.

        Args:
            query: Search query string

        Yields:
            Database objects
        """
        yield from self.search(
            query=query,
            filter={"property": "object", "value": "database"},
        )

    # =========================================================================
    # Comment Endpoints
    # =========================================================================

    def get_comments(
        self,
        block_id: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Get comments on a block or page.

        Args:
            block_id: Notion block/page ID

        Yields:
            Comment objects
        """
        yield from self.paginate(
            "/comments",
            method="GET",
            params={"block_id": block_id},
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def check_connection(self) -> tuple[bool, Optional[str]]:
        """
        Check if the connection to Notion is working.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = self.get_current_user()
            bot_name = user.get("name", "Unknown")
            logger.info(f"Connected to Notion as: {bot_name}")
            return True, None
        except NotionAuthenticationError as e:
            return False, f"Authentication failed: {e.message}"
        except NotionError as e:
            return False, f"Connection failed: {e.message}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def get_workspace_info(self) -> Dict[str, Any]:
        """
        Get information about the connected workspace.

        Returns:
            Dictionary with workspace information
        """
        bot = self.get_current_user()

        return {
            "bot_id": bot.get("id"),
            "bot_name": bot.get("name"),
            "workspace_name": bot.get("bot", {}).get("workspace_name"),
            "workspace_icon": bot.get("bot", {}).get("owner", {}).get("workspace", {}).get("icon"),
        }
