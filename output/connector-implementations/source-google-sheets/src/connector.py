"""
Main Google Sheets connector implementation.

Provides the core connector functionality:
- Connection testing
- Schema discovery
- Data extraction
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from .auth import (
    GoogleSheetsAuthenticator,
    ServiceAccountAuthenticator,
    OAuth2Authenticator,
    AuthenticationError,
)
from .client import (
    GoogleSheetsClient,
    RateLimitConfig,
    APIError,
    NotFoundError,
    PermissionDeniedError,
)
from .config import (
    GoogleSheetsConfig,
    ServiceAccountCredentials,
    OAuth2Credentials,
    Catalog,
    CatalogEntry,
    StreamConfig,
)
from .streams import SheetStream, StreamMetadata
from .utils import normalize_header, infer_schema_from_values

logger = logging.getLogger(__name__)


@dataclass
class ConnectionTestResult:
    """Result of a connection test."""

    success: bool
    message: str
    spreadsheet_title: Optional[str] = None
    sheet_count: Optional[int] = None
    error: Optional[Exception] = None

    def __str__(self) -> str:
        if self.success:
            return f"Connection successful: {self.spreadsheet_title} ({self.sheet_count} sheets)"
        return f"Connection failed: {self.message}"


class GoogleSheetsConnector:
    """
    Google Sheets source connector.

    Extracts data from Google Sheets spreadsheets with support for:
    - Multiple sheets per spreadsheet
    - Automatic schema inference
    - Configurable batch sizes for large sheets
    - Rate limiting and retry logic

    Example usage:
    ```python
    config = GoogleSheetsConfig(
        spreadsheet_id="your-spreadsheet-id",
        credentials=ServiceAccountCredentials(
            project_id="your-project",
            private_key="...",
            client_email="...",
        ),
    )

    connector = GoogleSheetsConnector(config)

    # Test connection
    result = connector.check_connection()
    if result.success:
        # Discover available streams
        catalog = connector.discover()

        # Read data from a specific sheet
        for record in connector.read("Sheet1"):
            print(record)
    ```
    """

    def __init__(self, config: GoogleSheetsConfig):
        """
        Initialize the connector with configuration.

        Args:
            config: Connector configuration including credentials and settings.
        """
        self.config = config
        self._authenticator: Optional[GoogleSheetsAuthenticator] = None
        self._client: Optional[GoogleSheetsClient] = None
        self._spreadsheet_metadata: Optional[Dict[str, Any]] = None

    def _create_authenticator(self) -> GoogleSheetsAuthenticator:
        """Create the appropriate authenticator based on credentials type."""
        if isinstance(self.config.credentials, ServiceAccountCredentials):
            return ServiceAccountAuthenticator(
                credentials_info=self.config.credentials.to_google_credentials_dict()
            )
        elif isinstance(self.config.credentials, OAuth2Credentials):
            return OAuth2Authenticator(
                client_id=self.config.credentials.client_id,
                client_secret=self.config.credentials.client_secret,
                refresh_token=self.config.credentials.refresh_token,
            )
        else:
            raise AuthenticationError(
                f"Unknown credentials type: {type(self.config.credentials)}"
            )

    @property
    def authenticator(self) -> GoogleSheetsAuthenticator:
        """Get or create the authenticator."""
        if self._authenticator is None:
            self._authenticator = self._create_authenticator()
        return self._authenticator

    @property
    def client(self) -> GoogleSheetsClient:
        """Get or create the API client."""
        if self._client is None:
            rate_config = RateLimitConfig(
                requests_per_minute=self.config.rate_limit.requests_per_minute,
                max_retries=self.config.rate_limit.max_retries,
                base_delay=self.config.rate_limit.base_delay,
                max_delay=self.config.rate_limit.max_delay,
            )
            self._client = GoogleSheetsClient(
                authenticator=self.authenticator,
                rate_limit_config=rate_config,
            )
        return self._client

    def check_connection(self) -> ConnectionTestResult:
        """
        Test the connection to the Google Sheets API.

        Verifies:
        - Authentication credentials are valid
        - The specified spreadsheet exists and is accessible

        Returns:
            ConnectionTestResult with success status and details.
        """
        try:
            # Attempt to get spreadsheet metadata
            metadata = self.client.get_spreadsheet(self.config.spreadsheet_id)
            self._spreadsheet_metadata = metadata

            title = metadata.get("properties", {}).get("title", "Unknown")
            sheet_count = len(metadata.get("sheets", []))

            logger.info(f"Connection successful: '{title}' with {sheet_count} sheets")

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                spreadsheet_title=title,
                sheet_count=sheet_count,
            )

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Authentication failed: {e.message}",
                error=e,
            )

        except PermissionDeniedError as e:
            logger.error(f"Permission denied: {e}")
            return ConnectionTestResult(
                success=False,
                message=(
                    "Permission denied. Please ensure the spreadsheet is shared with "
                    f"the service account email or that OAuth permissions are granted."
                ),
                error=e,
            )

        except NotFoundError as e:
            logger.error(f"Spreadsheet not found: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Spreadsheet not found. Please check the spreadsheet ID.",
                error=e,
            )

        except APIError as e:
            logger.error(f"API error: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"API error: {e.message}",
                error=e,
            )

        except Exception as e:
            logger.exception("Unexpected error during connection test")
            return ConnectionTestResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                error=e,
            )

    def _get_spreadsheet_metadata(self) -> Dict[str, Any]:
        """Get spreadsheet metadata, caching the result."""
        if self._spreadsheet_metadata is None:
            self._spreadsheet_metadata = self.client.get_spreadsheet(
                self.config.spreadsheet_id
            )
        return self._spreadsheet_metadata

    def _get_sheet_info(self) -> List[Dict[str, Any]]:
        """Get information about all sheets in the spreadsheet."""
        metadata = self._get_spreadsheet_metadata()
        sheets = []

        for sheet in metadata.get("sheets", []):
            props = sheet.get("properties", {})
            grid_props = props.get("gridProperties", {})
            sheets.append({
                "sheet_id": props.get("sheetId"),
                "title": props.get("title"),
                "index": props.get("index"),
                "row_count": grid_props.get("rowCount", 0),
                "column_count": grid_props.get("columnCount", 0),
                "frozen_row_count": grid_props.get("frozenRowCount", 0),
                "frozen_column_count": grid_props.get("frozenColumnCount", 0),
            })

        return sheets

    def _infer_stream_schema(
        self,
        sheet_name: str,
        header_row: int = 1,
        sample_rows: int = 100,
    ) -> Dict[str, Any]:
        """
        Infer JSON schema for a sheet by sampling data.

        Args:
            sheet_name: Name of the sheet.
            header_row: Row number containing headers (1-indexed).
            sample_rows: Number of rows to sample for type inference.

        Returns:
            JSON Schema dictionary.
        """
        # Get headers
        header_range = f"'{sheet_name}'!{header_row}:{header_row}"
        header_result = self.client.get_values(
            self.config.spreadsheet_id,
            header_range,
            value_render_option="FORMATTED_VALUE",
        )

        raw_headers = header_result.get("values", [[]])[0] if header_result.get("values") else []

        if not raw_headers:
            return {
                "type": "object",
                "properties": {},
            }

        # Normalize headers
        headers = normalize_header(raw_headers)

        # Get sample data for type inference
        data_start = header_row + 1
        data_end = data_start + sample_rows - 1
        data_range = f"'{sheet_name}'!A{data_start}:ZZ{data_end}"

        data_result = self.client.get_values(
            self.config.spreadsheet_id,
            data_range,
            value_render_option="UNFORMATTED_VALUE",
        )

        sample_values = data_result.get("values", [])

        # Infer schema from sampled values
        return infer_schema_from_values(headers, sample_values)

    def discover(self) -> Catalog:
        """
        Discover available streams (sheets) and their schemas.

        Returns:
            Catalog containing all discoverable streams with their schemas.
        """
        sheets_info = self._get_sheet_info()
        catalog_entries = []

        for sheet_info in sheets_info:
            sheet_name = sheet_info["title"]

            # Check if this sheet is in the configured streams
            stream_config = self._get_stream_config(sheet_name)
            if stream_config and not stream_config.enabled:
                continue

            header_row = (
                stream_config.header_row if stream_config
                else self.config.header_row
            )

            try:
                schema = self._infer_stream_schema(
                    sheet_name,
                    header_row=header_row,
                )

                entry = CatalogEntry(
                    stream_name=sheet_name,
                    schema=schema,
                    supported_sync_modes=["full_refresh"],
                    source_defined_cursor=False,
                )
                catalog_entries.append(entry)

                logger.info(
                    f"Discovered stream '{sheet_name}' with "
                    f"{len(schema.get('properties', {}))} columns"
                )

            except APIError as e:
                logger.warning(f"Failed to discover schema for sheet '{sheet_name}': {e}")
                continue

        return Catalog(streams=catalog_entries)

    def _get_stream_config(self, stream_name: str) -> Optional[StreamConfig]:
        """Get stream-specific configuration if defined."""
        if self.config.streams:
            for stream in self.config.streams:
                if stream.name == stream_name:
                    return stream
        return None

    def read(
        self,
        stream_name: str,
        header_row: Optional[int] = None,
        batch_size: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all records from a sheet.

        Args:
            stream_name: Name of the sheet to read.
            header_row: Row containing headers (1-indexed). Uses config default if not specified.
            batch_size: Rows per API call. Uses config default if not specified.

        Yields:
            Dictionary for each row with column headers as keys.

        Raises:
            APIError: If the API request fails.
        """
        # Get stream-specific configuration
        stream_config = self._get_stream_config(stream_name)

        effective_header_row = (
            header_row
            or (stream_config.header_row if stream_config else None)
            or self.config.header_row
        )

        effective_batch_size = (
            batch_size
            or (stream_config.batch_size if stream_config else None)
            or self.config.row_batch_size
        )

        stream = SheetStream(
            client=self.client,
            spreadsheet_id=self.config.spreadsheet_id,
            sheet_name=stream_name,
            header_row=effective_header_row,
            batch_size=effective_batch_size,
            include_row_number=self.config.include_row_number,
        )

        yield from stream.read()

    def read_all(
        self,
        catalog: Optional[Catalog] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all records from all configured streams.

        Args:
            catalog: Optional catalog to use. If not provided, discovery is performed.

        Yields:
            Dictionary containing stream name and record data:
            {
                "_stream": "sheet_name",
                ...record_data
            }
        """
        if catalog is None:
            catalog = self.discover()

        for entry in catalog.streams:
            stream_name = entry.stream_name
            logger.info(f"Reading stream: {stream_name}")

            for record in self.read(stream_name):
                yield {"_stream": stream_name, **record}

    def get_stream_metadata(self, stream_name: str) -> StreamMetadata:
        """
        Get metadata for a specific stream.

        Args:
            stream_name: Name of the sheet.

        Returns:
            StreamMetadata with sheet information.
        """
        sheets_info = self._get_sheet_info()

        for info in sheets_info:
            if info["title"] == stream_name:
                return StreamMetadata(
                    name=info["title"],
                    sheet_id=info["sheet_id"],
                    row_count=info["row_count"],
                    column_count=info["column_count"],
                )

        raise ValueError(f"Stream not found: {stream_name}")

    def close(self) -> None:
        """Close the connector and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None
        self._authenticator = None
        self._spreadsheet_metadata = None
        logger.debug("Connector closed")

    def __enter__(self) -> "GoogleSheetsConnector":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


def create_connector(config_dict: Dict[str, Any]) -> GoogleSheetsConnector:
    """
    Factory function to create a connector from a configuration dictionary.

    Args:
        config_dict: Configuration dictionary containing:
            - spreadsheet_id: The spreadsheet ID
            - credentials: Authentication credentials
            - Optional: streams, row_batch_size, header_row, etc.

    Returns:
        Configured GoogleSheetsConnector instance.

    Example:
    ```python
    connector = create_connector({
        "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "credentials": {
            "auth_type": "service_account",
            "project_id": "my-project",
            "private_key": "-----BEGIN PRIVATE KEY-----...",
            "client_email": "connector@my-project.iam.gserviceaccount.com",
        },
    })
    ```
    """
    config = GoogleSheetsConfig.from_dict(config_dict)
    return GoogleSheetsConnector(config)
