"""
Main Google Sheets connector class.

This module provides the main connector interface with standard
check, discover, and read operations.
"""

from typing import Any, Dict, Iterator, List, Optional, Union
from dataclasses import dataclass
import logging
import json
from datetime import datetime

from .config import (
    GoogleSheetsConfig,
    ConnectionStatus,
    SyncResult,
    SheetConfig,
)
from .client import GoogleSheetsClient
from .streams import (
    SheetStream,
    SpreadsheetStreamFactory,
    StreamMetadata,
)
from .utils import (
    GoogleSheetsError,
    get_timestamp,
)

logger = logging.getLogger(__name__)


@dataclass
class CatalogEntry:
    """Represents a stream entry in the catalog."""

    stream_name: str
    stream_schema: Dict[str, Any]
    metadata: Dict[str, Any]
    supported_sync_modes: List[str]
    default_cursor_field: Optional[List[str]] = None
    source_defined_primary_key: Optional[List[List[str]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "stream": {
                "name": self.stream_name,
                "json_schema": self.stream_schema,
                "supported_sync_modes": self.supported_sync_modes,
                "source_defined_primary_key": self.source_defined_primary_key,
                "default_cursor_field": self.default_cursor_field,
            },
            "metadata": self.metadata
        }


@dataclass
class Catalog:
    """Represents the full catalog of streams."""

    streams: List[CatalogEntry]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "streams": [entry.to_dict() for entry in self.streams]
        }

    def get_stream(self, name: str) -> Optional[CatalogEntry]:
        """Get a stream entry by name."""
        for entry in self.streams:
            if entry.stream_name == name:
                return entry
        return None


@dataclass
class Record:
    """Represents a single data record."""

    stream: str
    data: Dict[str, Any]
    emitted_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": "RECORD",
            "stream": self.stream,
            "data": self.data,
            "emitted_at": self.emitted_at
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class StateMessage:
    """Represents a state message."""

    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": "STATE",
            "data": self.data
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class GoogleSheetsConnector:
    """
    Google Sheets Source Connector.

    This connector provides methods to:
    - Check connection to a Google Spreadsheet
    - Discover available sheets and their schemas
    - Read data from sheets

    Example usage:
        config = GoogleSheetsConfig(
            spreadsheet_id="your-spreadsheet-id",
            credentials=ServiceAccountCredentials(
                service_account_info='{"type": "service_account", ...}'
            )
        )

        connector = GoogleSheetsConnector(config)

        # Check connection
        status = connector.check()
        if status.connected:
            # Discover streams
            catalog = connector.discover()

            # Read data
            for record in connector.read():
                print(record.to_json())
    """

    def __init__(self, config: Union[GoogleSheetsConfig, Dict[str, Any]]):
        """
        Initialize the connector.

        Args:
            config: Configuration as GoogleSheetsConfig or dictionary
        """
        if isinstance(config, dict):
            self.config = GoogleSheetsConfig(**config)
        else:
            self.config = config

        self.client = GoogleSheetsClient(self.config)
        self.stream_factory = SpreadsheetStreamFactory(
            client=self.client,
            sanitize_names=self.config.sanitize_column_names,
            include_row_numbers=self.config.include_row_numbers,
            batch_size=self.config.batch_size
        )

        self._streams: Optional[List[SheetStream]] = None
        self._catalog: Optional[Catalog] = None

    def check(self) -> ConnectionStatus:
        """
        Check connection to the spreadsheet.

        Returns:
            ConnectionStatus with connection details

        Example:
            status = connector.check()
            if status.connected:
                print(f"Connected to: {status.spreadsheet_title}")
            else:
                print(f"Error: {status.error}")
        """
        logger.info(f"Checking connection to spreadsheet: {self.config.spreadsheet_id}")

        try:
            success, message, metadata = self.client.check_connection()

            if success and metadata:
                return ConnectionStatus(
                    connected=True,
                    message=message,
                    spreadsheet_title=metadata.get("title"),
                    sheet_count=metadata.get("sheet_count"),
                    error=None
                )
            else:
                return ConnectionStatus(
                    connected=False,
                    message=message,
                    error=message
                )

        except GoogleSheetsError as e:
            logger.error(f"Connection check failed: {e}")
            return ConnectionStatus(
                connected=False,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during connection check: {e}")
            return ConnectionStatus(
                connected=False,
                message=f"Unexpected error: {e}",
                error=str(e)
            )

    def discover(self) -> Catalog:
        """
        Discover available streams (sheets) and their schemas.

        Returns:
            Catalog containing all available streams

        Example:
            catalog = connector.discover()
            for entry in catalog.streams:
                print(f"Stream: {entry.stream_name}")
                print(f"Schema: {entry.stream_schema}")
        """
        logger.info("Discovering streams...")

        if self._catalog is not None:
            return self._catalog

        # Get all streams
        streams = self._get_streams()

        catalog_entries = []

        for stream in streams:
            try:
                schema = stream.get_schema()
                metadata = stream.get_stream_metadata()

                entry = CatalogEntry(
                    stream_name=stream.name,
                    stream_schema=schema.to_dict(),
                    metadata={
                        "sheet_id": stream.sheet_id,
                        "row_count": metadata.row_count,
                        "column_count": metadata.column_count,
                        "headers": metadata.headers,
                    },
                    supported_sync_modes=["full_refresh"],
                    source_defined_primary_key=[stream.primary_key] if stream.primary_key else None
                )

                catalog_entries.append(entry)
                logger.debug(f"Discovered stream: {stream.name}")

            except GoogleSheetsError as e:
                logger.warning(f"Failed to discover stream '{stream.name}': {e}")
                continue

        self._catalog = Catalog(streams=catalog_entries)
        logger.info(f"Discovered {len(catalog_entries)} streams")

        return self._catalog

    def read(
        self,
        selected_streams: Optional[List[str]] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> Iterator[Union[Record, StateMessage]]:
        """
        Read data from selected streams.

        Args:
            selected_streams: List of stream names to read (None = all)
            state: Optional state from previous sync (not used for full refresh)

        Yields:
            Record and StateMessage objects

        Example:
            for message in connector.read(selected_streams=["Sheet1"]):
                if isinstance(message, Record):
                    print(message.to_json())
        """
        streams = self._get_streams()

        # Filter streams if selection provided
        if selected_streams:
            streams = [s for s in streams if s.name in selected_streams]
            logger.info(f"Reading from {len(streams)} selected streams")
        else:
            logger.info(f"Reading from all {len(streams)} streams")

        # Also filter by configured sheets if specified
        if self.config.sheets:
            configured_names = {s.name for s in self.config.sheets}
            streams = [s for s in streams if s.name in configured_names]

            # Apply sheet-specific configuration
            for stream in streams:
                sheet_config = next(
                    (s for s in self.config.sheets if s.name == stream.name),
                    None
                )
                if sheet_config:
                    stream.header_row = sheet_config.headers_row
                    stream.skip_rows = sheet_config.skip_rows
                    if sheet_config.range:
                        stream.range_notation = sheet_config.range

        for stream in streams:
            logger.info(f"Reading stream: {stream.name}")

            record_count = 0
            started_at = get_timestamp()

            try:
                for record_data in stream.read_records():
                    record = Record(
                        stream=stream.name,
                        data=record_data,
                        emitted_at=get_timestamp()
                    )
                    yield record
                    record_count += 1

                # Emit state after each stream
                stream_state = {
                    "stream": stream.name,
                    "completed": True,
                    "records_read": record_count,
                    "completed_at": get_timestamp()
                }

                yield StateMessage(data=stream_state)

                logger.info(f"Completed stream '{stream.name}': {record_count} records")

            except GoogleSheetsError as e:
                logger.error(f"Error reading stream '{stream.name}': {e}")
                # Emit error state
                yield StateMessage(data={
                    "stream": stream.name,
                    "error": str(e),
                    "records_read": record_count,
                    "failed_at": get_timestamp()
                })

    def read_stream(
        self,
        stream_name: str
    ) -> Iterator[Dict[str, Any]]:
        """
        Read data from a specific stream.

        Args:
            stream_name: Name of the stream to read

        Yields:
            Dictionary records

        Example:
            for record in connector.read_stream("Sheet1"):
                print(record)
        """
        stream = self.stream_factory.get_stream(stream_name)

        if stream is None:
            raise GoogleSheetsError(f"Stream '{stream_name}' not found")

        yield from stream.read_records()

    def sync(
        self,
        selected_streams: Optional[List[str]] = None
    ) -> List[SyncResult]:
        """
        Perform a full sync of selected streams.

        Args:
            selected_streams: List of stream names to sync (None = all)

        Returns:
            List of SyncResult for each stream

        Example:
            results = connector.sync(selected_streams=["Sheet1", "Sheet2"])
            for result in results:
                print(f"{result.stream_name}: {result.records_count} records")
        """
        results = []
        streams = self._get_streams()

        if selected_streams:
            streams = [s for s in streams if s.name in selected_streams]

        for stream in streams:
            started_at = get_timestamp()
            record_count = 0
            error_message = None

            try:
                for _ in stream.read_records():
                    record_count += 1

                success = True

            except GoogleSheetsError as e:
                success = False
                error_message = str(e)
                logger.error(f"Sync failed for stream '{stream.name}': {e}")

            results.append(SyncResult(
                stream_name=stream.name,
                records_count=record_count,
                success=success,
                error=error_message,
                started_at=started_at,
                completed_at=get_timestamp()
            ))

        return results

    def get_stream_metadata(
        self,
        stream_name: str
    ) -> Optional[StreamMetadata]:
        """
        Get metadata for a specific stream.

        Args:
            stream_name: Name of the stream

        Returns:
            StreamMetadata or None if not found
        """
        stream = self.stream_factory.get_stream(stream_name)

        if stream is None:
            return None

        return stream.get_stream_metadata()

    def get_all_stream_metadata(self) -> List[StreamMetadata]:
        """
        Get metadata for all streams.

        Returns:
            List of StreamMetadata
        """
        streams = self._get_streams()
        return [s.get_stream_metadata() for s in streams]

    def _get_streams(self) -> List[SheetStream]:
        """
        Get all available streams.

        Returns:
            List of SheetStream instances
        """
        if self._streams is None:
            self._streams = self.stream_factory.discover_streams()
        return self._streams


def create_connector(config: Union[Dict[str, Any], str]) -> GoogleSheetsConnector:
    """
    Factory function to create a connector from config.

    Args:
        config: Configuration as dictionary or JSON string

    Returns:
        GoogleSheetsConnector instance

    Example:
        connector = create_connector({
            "spreadsheet_id": "your-id",
            "credentials": {
                "auth_type": "service_account",
                "service_account_info": "..."
            }
        })
    """
    if isinstance(config, str):
        config = json.loads(config)

    sheets_config = GoogleSheetsConfig(**config)
    return GoogleSheetsConnector(sheets_config)


# CLI interface when run as a script
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Google Sheets Source Connector")
    parser.add_argument("command", choices=["check", "discover", "read"])
    parser.add_argument("--config", required=True, help="Path to config file")
    parser.add_argument("--catalog", help="Path to catalog file (for read)")
    parser.add_argument("--state", help="Path to state file (for read)")

    args = parser.parse_args()

    # Load config
    with open(args.config, "r") as f:
        config_data = json.load(f)

    connector = create_connector(config_data)

    if args.command == "check":
        status = connector.check()
        print(json.dumps({
            "type": "CONNECTION_STATUS",
            "connectionStatus": {
                "status": "SUCCEEDED" if status.connected else "FAILED",
                "message": status.message
            }
        }))

    elif args.command == "discover":
        catalog = connector.discover()
        print(json.dumps(catalog.to_dict(), indent=2))

    elif args.command == "read":
        selected = None
        if args.catalog:
            with open(args.catalog, "r") as f:
                catalog_data = json.load(f)
            selected = [
                s["stream"]["name"]
                for s in catalog_data.get("streams", [])
            ]

        state = None
        if args.state:
            with open(args.state, "r") as f:
                state = json.load(f)

        for message in connector.read(selected_streams=selected, state=state):
            print(message.to_json())
