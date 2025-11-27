"""
Main Notion source connector class.

This module provides the primary interface for the Notion connector,
implementing the standard check/discover/read operations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

from .auth import create_authenticator
from .client import NotionClient
from .config import NotionConfig, ConnectorState, StreamState
from .streams import (
    BaseStream,
    UsersStream,
    DatabasesStream,
    PagesStream,
    BlocksStream,
    CommentsStream,
    DatabasePagesStream,
    get_all_streams,
    get_stream_by_name,
)
from .utils import NotionError, AuthenticationError, setup_logging

logger = logging.getLogger(__name__)


# =============================================================================
# Connector Output Types
# =============================================================================


class AirbyteMessage:
    """Base class for connector output messages."""
    pass


class ConnectionStatus:
    """Connection check result."""

    def __init__(self, status: str, message: Optional[str] = None):
        self.status = status
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        result = {"status": self.status}
        if self.message:
            result["message"] = self.message
        return result


class StreamSchema:
    """Stream schema definition."""

    def __init__(
        self,
        name: str,
        json_schema: Dict[str, Any],
        supported_sync_modes: List[str],
        source_defined_cursor: bool = False,
        default_cursor_field: Optional[List[str]] = None,
        source_defined_primary_key: Optional[List[List[str]]] = None,
    ):
        self.name = name
        self.json_schema = json_schema
        self.supported_sync_modes = supported_sync_modes
        self.source_defined_cursor = source_defined_cursor
        self.default_cursor_field = default_cursor_field
        self.source_defined_primary_key = source_defined_primary_key

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "json_schema": self.json_schema,
            "supported_sync_modes": self.supported_sync_modes,
            "source_defined_cursor": self.source_defined_cursor,
            "default_cursor_field": self.default_cursor_field,
            "source_defined_primary_key": self.source_defined_primary_key,
        }


class Catalog:
    """Catalog of available streams."""

    def __init__(self, streams: List[StreamSchema]):
        self.streams = streams

    def to_dict(self) -> Dict[str, Any]:
        return {
            "streams": [s.to_dict() for s in self.streams]
        }


class Record:
    """A data record from a stream."""

    def __init__(
        self,
        stream: str,
        data: Dict[str, Any],
        emitted_at: int,
    ):
        self.stream = stream
        self.data = data
        self.emitted_at = emitted_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "RECORD",
            "record": {
                "stream": self.stream,
                "data": self.data,
                "emitted_at": self.emitted_at,
            }
        }


class StateMessage:
    """State checkpoint message."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "STATE",
            "state": {
                "data": self.data
            }
        }


# =============================================================================
# Main Connector Class
# =============================================================================


class NotionSourceConnector:
    """
    Notion source connector for extracting data from Notion workspaces.

    This connector supports:
    - Users: All users in the workspace
    - Databases: All accessible databases
    - Pages: All accessible pages
    - Blocks: Page content blocks
    - Comments: Page and block comments

    Features:
    - Internal integration token and OAuth 2.0 authentication
    - Rate limiting with exponential backoff
    - Incremental sync support
    - Comprehensive error handling
    """

    def __init__(self, config: NotionConfig):
        """
        Initialize the connector.

        Args:
            config: NotionConfig instance with credentials and settings
        """
        self.config = config
        self.client = NotionClient(config)
        self._state = ConnectorState()

    @classmethod
    def from_config_dict(cls, config_dict: Dict[str, Any]) -> "NotionSourceConnector":
        """
        Create a connector from a configuration dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            NotionSourceConnector instance
        """
        config = NotionConfig(**config_dict)
        return cls(config)

    @classmethod
    def from_config_file(cls, config_path: str) -> "NotionSourceConnector":
        """
        Create a connector from a configuration file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            NotionSourceConnector instance
        """
        with open(config_path, "r") as f:
            config_dict = json.load(f)
        return cls.from_config_dict(config_dict)

    # =========================================================================
    # Connection Check
    # =========================================================================

    def check(self) -> ConnectionStatus:
        """
        Check the connection to Notion.

        Validates the authentication credentials and verifies
        that the connector can access the Notion API.

        Returns:
            ConnectionStatus with success/failure information
        """
        logger.info("Checking connection to Notion")

        try:
            success, error = self.client.check_connection()

            if success:
                workspace_info = self.client.get_workspace_info()
                workspace_name = workspace_info.get("workspace_name", "Unknown")
                bot_name = workspace_info.get("bot_name", "Unknown")

                return ConnectionStatus(
                    status="SUCCEEDED",
                    message=f"Connected to workspace '{workspace_name}' as '{bot_name}'",
                )
            else:
                return ConnectionStatus(
                    status="FAILED",
                    message=error or "Unknown connection error",
                )

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return ConnectionStatus(
                status="FAILED",
                message=f"Authentication failed: {e.message}",
            )

        except NotionError as e:
            logger.error(f"Notion API error: {e}")
            return ConnectionStatus(
                status="FAILED",
                message=f"API error: {e.message}",
            )

        except Exception as e:
            logger.exception("Unexpected error during connection check")
            return ConnectionStatus(
                status="FAILED",
                message=f"Unexpected error: {str(e)}",
            )

    # =========================================================================
    # Schema Discovery
    # =========================================================================

    def discover(self) -> Catalog:
        """
        Discover available streams and their schemas.

        Returns:
            Catalog of available streams
        """
        logger.info("Discovering available streams")

        streams = get_all_streams(self.client, self.config)
        stream_schemas = []

        for stream in streams:
            # Determine supported sync modes
            sync_modes = ["full_refresh"]
            if stream.supports_incremental:
                sync_modes.append("incremental")

            # Determine cursor field
            cursor_field = None
            if stream.cursor_field:
                cursor_field = [stream.cursor_field]

            # Determine primary key
            primary_key = None
            if stream.primary_key:
                primary_key = [[stream.primary_key]]

            stream_schema = StreamSchema(
                name=stream.name,
                json_schema=stream.json_schema,
                supported_sync_modes=sync_modes,
                source_defined_cursor=stream.cursor_field is not None,
                default_cursor_field=cursor_field,
                source_defined_primary_key=primary_key,
            )
            stream_schemas.append(stream_schema)

        return Catalog(streams=stream_schemas)

    # =========================================================================
    # Data Reading
    # =========================================================================

    def read(
        self,
        stream_names: Optional[List[str]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read data from specified streams.

        Args:
            stream_names: List of stream names to read (None for all)
            state: Optional state dictionary for incremental sync

        Yields:
            Record and state messages as dictionaries
        """
        logger.info(f"Starting read operation for streams: {stream_names or 'all'}")

        # Load state if provided
        if state:
            self._state = ConnectorState(**state)

        # Get streams to read
        all_streams = get_all_streams(self.client, self.config)

        if stream_names:
            streams_to_read = [
                s for s in all_streams
                if s.name in stream_names and self.config.is_stream_enabled(s.name)
            ]
        else:
            streams_to_read = [
                s for s in all_streams
                if self.config.is_stream_enabled(s.name)
            ]

        # Read each stream
        for stream in streams_to_read:
            logger.info(f"Reading stream: {stream.name}")

            try:
                yield from self._read_stream(stream)
            except Exception as e:
                logger.error(f"Error reading stream {stream.name}: {e}")
                # Continue with other streams
                continue

        # Emit final state
        yield StateMessage(data=self._state.model_dump()).to_dict()

    def _read_stream(
        self,
        stream: BaseStream,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read data from a single stream.

        Args:
            stream: Stream instance to read

        Yields:
            Record messages
        """
        stream_state = self._state.get_stream_state(stream.name)
        records_count = 0
        latest_cursor_value = stream_state.cursor_value

        for record in stream.read(state=stream_state):
            # Emit record
            yield Record(
                stream=stream.name,
                data=record,
                emitted_at=int(datetime.utcnow().timestamp() * 1000),
            ).to_dict()

            records_count += 1

            # Track cursor value for incremental sync
            if stream.cursor_field and stream.cursor_field in record:
                cursor_value = record[stream.cursor_field]
                if cursor_value and (
                    not latest_cursor_value or cursor_value > latest_cursor_value
                ):
                    latest_cursor_value = cursor_value

            # Emit state checkpoint periodically
            if records_count % 100 == 0:
                self._state.update_stream_state(
                    stream.name,
                    cursor_value=latest_cursor_value,
                    records_synced=100,
                )
                yield StateMessage(data=self._state.model_dump()).to_dict()

        # Update final state for this stream
        self._state.update_stream_state(
            stream.name,
            cursor_value=latest_cursor_value,
            records_synced=records_count % 100,
        )

        logger.info(f"Completed reading stream {stream.name}: {records_count} records")

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def read_users(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read all users from the workspace.

        Yields:
            User records
        """
        stream = UsersStream(self.client, self.config)
        yield from stream.read()

    def read_databases(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read all databases from the workspace.

        Yields:
            Database records
        """
        stream = DatabasesStream(self.client, self.config)
        yield from stream.read()

    def read_pages(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read all pages from the workspace.

        Yields:
            Page records
        """
        stream = PagesStream(self.client, self.config)
        yield from stream.read()

    def read_blocks(
        self,
        page_ids: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read blocks from pages.

        Args:
            page_ids: Optional list of page IDs (None for all pages)

        Yields:
            Block records
        """
        stream = BlocksStream(self.client, self.config, page_ids=page_ids)
        yield from stream.read()

    def read_comments(
        self,
        page_ids: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read comments from pages.

        Args:
            page_ids: Optional list of page IDs (None for all pages)

        Yields:
            Comment records
        """
        stream = CommentsStream(self.client, self.config, page_ids=page_ids)
        yield from stream.read()

    def read_database(
        self,
        database_id: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all pages from a specific database.

        Args:
            database_id: Notion database ID

        Yields:
            Page records
        """
        stream = DatabasePagesStream(
            self.client,
            self.config,
            database_id=database_id,
        )
        yield from stream.read()

    # =========================================================================
    # State Management
    # =========================================================================

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current connector state.

        Returns:
            State dictionary
        """
        return self._state.model_dump()

    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Set the connector state.

        Args:
            state: State dictionary
        """
        self._state = ConnectorState(**state)


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """Command-line interface for the connector."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Notion Source Connector")
    parser.add_argument(
        "command",
        choices=["check", "discover", "read"],
        help="Command to run",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--state",
        help="Path to state file (for incremental sync)",
    )
    parser.add_argument(
        "--catalog",
        help="Path to catalog file (for read command)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)

    try:
        # Create connector
        connector = NotionSourceConnector.from_config_file(args.config)

        if args.command == "check":
            result = connector.check()
            print(json.dumps({"connectionStatus": result.to_dict()}))

        elif args.command == "discover":
            catalog = connector.discover()
            print(json.dumps({"catalog": catalog.to_dict()}))

        elif args.command == "read":
            # Load state if provided
            state = None
            if args.state:
                with open(args.state, "r") as f:
                    state = json.load(f)

            # Load catalog if provided to determine which streams to read
            stream_names = None
            if args.catalog:
                with open(args.catalog, "r") as f:
                    catalog_data = json.load(f)
                    stream_names = [
                        s["stream"]["name"]
                        for s in catalog_data.get("streams", [])
                        if s.get("sync_mode") in ["full_refresh", "incremental"]
                    ]

            # Read data
            for message in connector.read(stream_names=stream_names, state=state):
                print(json.dumps(message))

    except Exception as e:
        logger.exception("Error running connector")
        print(json.dumps({
            "type": "LOG",
            "log": {
                "level": "ERROR",
                "message": str(e),
            }
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
