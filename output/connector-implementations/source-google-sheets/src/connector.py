"""
Main Google Sheets connector implementation.

Provides the primary interface for connecting to Google Sheets,
discovering available data streams, and reading data.
"""

import json
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generator, Iterator, List, Optional, Union

from src.auth import (
    GoogleSheetsAuthenticator,
    ServiceAccountAuth,
    OAuth2Auth,
    AuthenticationError,
    create_authenticator,
)
from src.client import (
    GoogleSheetsClient,
    GoogleSheetsAPIError,
    SpreadsheetNotFoundError,
    AccessDeniedError,
)
from src.config import GoogleSheetsConfig
from src.streams import SheetStream, StreamCatalog, SyncMode
from src.utils import get_current_timestamp


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ConnectorStatus(str, Enum):
    """Status codes for connector operations."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class ConnectionCheckResult:
    """Result of a connection check operation."""

    status: ConnectorStatus
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class SyncResult:
    """Result of a sync operation."""

    stream_name: str
    records_read: int
    status: ConnectorStatus
    error: Optional[str] = None


class GoogleSheetsConnector:
    """
    Production-ready Google Sheets source connector.

    Supports OAuth2 and Service Account authentication.
    Implements check, discover, and read operations.
    """

    def __init__(
        self,
        config: Union[GoogleSheetsConfig, Dict[str, Any]],
    ):
        """
        Initialize the Google Sheets connector.

        Args:
            config: Configuration for the connector (GoogleSheetsConfig or dict).
        """
        # Parse config if needed
        if isinstance(config, dict):
            self._config = GoogleSheetsConfig.from_dict(config)
        else:
            self._config = config

        # Initialize authenticator
        self._authenticator = self._create_authenticator()

        # Initialize client
        self._client = GoogleSheetsClient(
            authenticator=self._authenticator,
            requests_per_minute=self._config.requests_per_minute,
            batch_size=self._config.row_batch_size,
        )

        # Stream catalog (lazy loaded)
        self._catalog: Optional[StreamCatalog] = None

    def _create_authenticator(self) -> GoogleSheetsAuthenticator:
        """
        Create the appropriate authenticator based on config.

        Returns:
            GoogleSheetsAuthenticator instance.
        """
        auth_type = self._config.get_auth_type()
        credentials = self._config.get_credentials_dict()
        return create_authenticator(auth_type, credentials)

    @property
    def spreadsheet_id(self) -> str:
        """Get the configured spreadsheet ID."""
        return self._config.spreadsheet_id

    @property
    def catalog(self) -> StreamCatalog:
        """
        Get the stream catalog.

        Lazy loads the catalog on first access.

        Returns:
            StreamCatalog instance.
        """
        if self._catalog is None:
            self._catalog = StreamCatalog(
                client=self._client,
                spreadsheet_id=self._config.spreadsheet_id,
                include_row_number=self._config.include_row_number,
            )
        return self._catalog

    def check_connection(self) -> ConnectionCheckResult:
        """
        Verify connection to the Google Sheets API.

        Tests authentication and spreadsheet access.

        Returns:
            ConnectionCheckResult with status and message.
        """
        logger.info(f"Checking connection to spreadsheet: {self.spreadsheet_id}")

        try:
            # Test authentication by getting spreadsheet metadata
            metadata = self._client.get_spreadsheet_metadata(self.spreadsheet_id)

            spreadsheet_title = metadata.get("properties", {}).get("title", "Unknown")
            sheet_count = len(metadata.get("sheets", []))

            return ConnectionCheckResult(
                status=ConnectorStatus.SUCCEEDED,
                message=f"Successfully connected to '{spreadsheet_title}'",
                details={
                    "spreadsheet_id": self.spreadsheet_id,
                    "spreadsheet_title": spreadsheet_title,
                    "sheet_count": sheet_count,
                },
            )

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return ConnectionCheckResult(
                status=ConnectorStatus.FAILED,
                message=f"Authentication failed: {e.message}",
                details=e.details,
            )

        except SpreadsheetNotFoundError as e:
            logger.error(f"Spreadsheet not found: {e}")
            return ConnectionCheckResult(
                status=ConnectorStatus.FAILED,
                message=f"Spreadsheet not found: {self.spreadsheet_id}",
                details={"spreadsheet_id": self.spreadsheet_id},
            )

        except AccessDeniedError as e:
            logger.error(f"Access denied: {e}")
            return ConnectionCheckResult(
                status=ConnectorStatus.FAILED,
                message="Access denied. Ensure the spreadsheet is shared with the service account.",
                details={"spreadsheet_id": self.spreadsheet_id},
            )

        except GoogleSheetsAPIError as e:
            logger.error(f"API error: {e}")
            return ConnectionCheckResult(
                status=ConnectorStatus.FAILED,
                message=f"API error: {e.message}",
                details={"status_code": e.status_code},
            )

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return ConnectionCheckResult(
                status=ConnectorStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
            )

    def discover(self) -> Dict[str, Any]:
        """
        Discover available streams from the spreadsheet.

        Returns a catalog of all sheets with their schemas.

        Returns:
            Catalog dictionary with stream definitions.
        """
        logger.info(f"Discovering streams from spreadsheet: {self.spreadsheet_id}")

        try:
            catalog_data = self.catalog.get_catalog()

            # Filter streams based on config
            if self._config.stream_selection:
                filtered_streams = []
                for stream in catalog_data.get("streams", []):
                    stream_name = stream.get("name", "")
                    if self._config.should_sync_sheet(stream_name):
                        filtered_streams.append(stream)
                catalog_data["streams"] = filtered_streams

            logger.info(f"Discovered {len(catalog_data.get('streams', []))} streams")
            return catalog_data

        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            raise

    def get_stream(self, sheet_name: str) -> Optional[SheetStream]:
        """
        Get a specific stream by sheet name.

        Args:
            sheet_name: Name of the sheet.

        Returns:
            SheetStream if found, None otherwise.
        """
        return self.catalog.get_stream(sheet_name)

    def get_available_streams(self) -> List[str]:
        """
        Get list of available stream names.

        Returns:
            List of sheet names.
        """
        return self.catalog.get_stream_names()

    def read_stream(
        self,
        stream_name: str,
    ) -> Generator[Dict[str, Any], None, SyncResult]:
        """
        Read all records from a specific stream.

        Args:
            stream_name: Name of the stream/sheet to read.

        Yields:
            Record dictionaries.

        Returns:
            SyncResult with statistics.
        """
        logger.info(f"Reading stream: {stream_name}")

        stream = self.get_stream(stream_name)
        if stream is None:
            logger.error(f"Stream not found: {stream_name}")
            return SyncResult(
                stream_name=stream_name,
                records_read=0,
                status=ConnectorStatus.FAILED,
                error=f"Stream not found: {stream_name}",
            )

        try:
            records_read = 0
            for record in stream.read_records():
                yield record
                records_read += 1

            logger.info(f"Read {records_read} records from {stream_name}")
            return SyncResult(
                stream_name=stream_name,
                records_read=records_read,
                status=ConnectorStatus.SUCCEEDED,
            )

        except Exception as e:
            logger.error(f"Error reading stream {stream_name}: {e}")
            return SyncResult(
                stream_name=stream_name,
                records_read=records_read,
                status=ConnectorStatus.FAILED,
                error=str(e),
            )

    def read_all_streams(
        self,
        selected_streams: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, List[SyncResult]]:
        """
        Read records from all (or selected) streams.

        Args:
            selected_streams: Optional list of stream names to read.
                            If None, reads all streams.

        Yields:
            Record dictionaries with added _stream metadata.

        Returns:
            List of SyncResult for each stream.
        """
        results: List[SyncResult] = []

        # Determine which streams to read
        if selected_streams:
            stream_names = [s for s in selected_streams if s in self.catalog.streams]
        else:
            # Filter based on config
            stream_names = [
                name
                for name in self.catalog.get_stream_names()
                if self._config.should_sync_sheet(name)
            ]

        logger.info(f"Reading {len(stream_names)} streams")

        for stream_name in stream_names:
            stream = self.catalog.get_stream(stream_name)
            if stream is None:
                results.append(
                    SyncResult(
                        stream_name=stream_name,
                        records_read=0,
                        status=ConnectorStatus.FAILED,
                        error=f"Stream not found: {stream_name}",
                    )
                )
                continue

            try:
                records_read = 0
                for record in stream.read_records():
                    # Add stream metadata
                    record["_stream"] = stream_name
                    record["_extracted_at"] = get_current_timestamp()
                    yield record
                    records_read += 1

                results.append(
                    SyncResult(
                        stream_name=stream_name,
                        records_read=records_read,
                        status=ConnectorStatus.SUCCEEDED,
                    )
                )
                logger.info(f"Completed reading {stream_name}: {records_read} records")

            except Exception as e:
                logger.error(f"Error reading stream {stream_name}: {e}")
                results.append(
                    SyncResult(
                        stream_name=stream_name,
                        records_read=0,
                        status=ConnectorStatus.FAILED,
                        error=str(e),
                    )
                )

        return results

    def read(
        self,
        streams: Optional[List[str]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Simple read interface for all configured streams.

        Args:
            streams: Optional list of stream names to read.

        Yields:
            Record dictionaries.
        """
        gen = self.read_all_streams(selected_streams=streams)

        # Consume generator and yield records
        try:
            while True:
                record = next(gen)
                yield record
        except StopIteration as e:
            # e.value contains the return value (list of SyncResults)
            results = e.value
            logger.info(f"Read completed. Results: {len(results)} streams processed")


def main():
    """
    Command-line interface for the Google Sheets connector.

    Usage:
        python -m src.connector check --config config.json
        python -m src.connector discover --config config.json
        python -m src.connector read --config config.json [--streams sheet1,sheet2]
    """
    import argparse

    parser = argparse.ArgumentParser(description="Google Sheets Source Connector")
    parser.add_argument(
        "command",
        choices=["check", "discover", "read"],
        help="Command to execute",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to configuration JSON file",
    )
    parser.add_argument(
        "--streams",
        help="Comma-separated list of streams to read (for read command)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (defaults to stdout)",
    )

    args = parser.parse_args()

    # Load config
    try:
        with open(args.config, "r") as f:
            config_data = json.load(f)
        config = GoogleSheetsConfig.from_dict(config_data)
    except FileNotFoundError:
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to parse config: {e}", file=sys.stderr)
        sys.exit(1)

    # Create connector
    connector = GoogleSheetsConnector(config)

    # Execute command
    output_file = open(args.output, "w") if args.output else sys.stdout

    try:
        if args.command == "check":
            result = connector.check_connection()
            output = {
                "type": "CONNECTION_STATUS",
                "status": result.status.value,
                "message": result.message,
            }
            if result.details:
                output["details"] = result.details
            print(json.dumps(output), file=output_file)

            if result.status == ConnectorStatus.FAILED:
                sys.exit(1)

        elif args.command == "discover":
            catalog = connector.discover()
            output = {"type": "CATALOG", "catalog": catalog}
            print(json.dumps(output, indent=2), file=output_file)

        elif args.command == "read":
            selected_streams = None
            if args.streams:
                selected_streams = [s.strip() for s in args.streams.split(",")]

            for record in connector.read(streams=selected_streams):
                output = {"type": "RECORD", "record": record}
                print(json.dumps(output), file=output_file)

    finally:
        if args.output:
            output_file.close()


if __name__ == "__main__":
    main()
