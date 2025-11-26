"""
Data stream definitions for Google Sheets connector.

Each sheet in a spreadsheet becomes a stream that can be read.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, Iterator, List, Optional

from src.client import GoogleSheetsClient
from src.utils import normalize_header, sanitize_sheet_name


class SyncMode(str, Enum):
    """Supported synchronization modes."""

    FULL_REFRESH = "full_refresh"
    # Note: Google Sheets doesn't have a built-in change tracking mechanism,
    # so incremental sync would require external state management


@dataclass
class StreamSchema:
    """
    Schema definition for a stream.

    Represents the structure of records from a sheet.
    """

    name: str
    properties: Dict[str, Dict[str, Any]]
    primary_key: Optional[List[str]] = None
    required: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary representation."""
        schema = {
            "type": "object",
            "properties": self.properties,
        }
        if self.required:
            schema["required"] = self.required
        return schema

    @classmethod
    def from_headers(
        cls,
        stream_name: str,
        headers: List[str],
        primary_key: Optional[List[str]] = None,
    ) -> "StreamSchema":
        """
        Create schema from header row.

        All columns are typed as strings since Google Sheets
        doesn't provide type information.

        Args:
            stream_name: Name of the stream/sheet.
            headers: List of column headers.
            primary_key: Optional list of primary key columns.

        Returns:
            StreamSchema instance.
        """
        properties = {}
        for header in headers:
            normalized = normalize_header(header)
            properties[normalized] = {
                "type": ["string", "null"],
                "description": f"Column: {header}",
            }

        return cls(
            name=stream_name,
            properties=properties,
            primary_key=primary_key,
        )


@dataclass
class StreamConfig:
    """Configuration for a data stream."""

    name: str
    sync_mode: SyncMode = SyncMode.FULL_REFRESH
    cursor_field: Optional[str] = None
    primary_key: Optional[List[str]] = None
    selected: bool = True


class SheetStream:
    """
    Represents a single sheet as a data stream.

    Handles reading data from a Google Sheets sheet and
    converting rows to records.
    """

    def __init__(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        sheet_name: str,
        config: Optional[StreamConfig] = None,
        include_row_number: bool = False,
    ):
        """
        Initialize a sheet stream.

        Args:
            client: Google Sheets API client.
            spreadsheet_id: ID of the spreadsheet.
            sheet_name: Name of the sheet.
            config: Optional stream configuration.
            include_row_number: Whether to include row number in records.
        """
        self._client = client
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._config = config or StreamConfig(name=sheet_name)
        self._include_row_number = include_row_number
        self._headers: Optional[List[str]] = None
        self._schema: Optional[StreamSchema] = None

    @property
    def name(self) -> str:
        """Get the stream name (sanitized sheet name)."""
        return sanitize_sheet_name(self._sheet_name)

    @property
    def raw_name(self) -> str:
        """Get the original sheet name."""
        return self._sheet_name

    @property
    def sync_mode(self) -> SyncMode:
        """Get the sync mode for this stream."""
        return self._config.sync_mode

    @property
    def primary_key(self) -> Optional[List[str]]:
        """Get the primary key columns."""
        return self._config.primary_key

    @property
    def headers(self) -> List[str]:
        """
        Get headers for this sheet.

        Fetches from API if not already cached.

        Returns:
            List of column headers.
        """
        if self._headers is None:
            self._headers = self._client.get_headers(
                self._spreadsheet_id, self._sheet_name
            )
        return self._headers

    @property
    def normalized_headers(self) -> List[str]:
        """Get normalized headers (safe for use as field names)."""
        return [normalize_header(h) for h in self.headers]

    @property
    def schema(self) -> StreamSchema:
        """
        Get the schema for this stream.

        Generates schema from headers if not already cached.

        Returns:
            StreamSchema instance.
        """
        if self._schema is None:
            self._schema = StreamSchema.from_headers(
                stream_name=self.name,
                headers=self.headers,
                primary_key=self._config.primary_key,
            )
            # Add row number field if configured
            if self._include_row_number:
                self._schema.properties["_row_number"] = {
                    "type": "integer",
                    "description": "Row number in the spreadsheet",
                }
        return self._schema

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for this stream.

        Returns:
            JSON Schema dictionary.
        """
        return {
            "name": self.name,
            "json_schema": self.schema.to_dict(),
            "supported_sync_modes": [SyncMode.FULL_REFRESH.value],
            "source_defined_cursor": False,
            "default_cursor_field": [],
            "source_defined_primary_key": self.primary_key or [],
        }

    def _row_to_record(
        self,
        row: List[Any],
        row_number: int,
    ) -> Dict[str, Any]:
        """
        Convert a row to a record dictionary.

        Args:
            row: List of cell values.
            row_number: 1-indexed row number in spreadsheet.

        Returns:
            Dictionary with normalized header keys and cell values.
        """
        headers = self.normalized_headers
        record: Dict[str, Any] = {}

        # Pad row if it has fewer columns than headers
        padded_row = list(row) + [""] * (len(headers) - len(row))

        for i, header in enumerate(headers):
            value = padded_row[i] if i < len(padded_row) else ""
            # Convert empty strings to None for cleaner data
            record[header] = value if value != "" else None

        if self._include_row_number:
            record["_row_number"] = row_number

        return record

    def read_records(
        self,
        batch_size: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all records from the sheet.

        Yields records one at a time, fetching data in batches
        from the API for efficiency.

        Args:
            batch_size: Optional override for batch size.

        Yields:
            Record dictionaries.
        """
        # Ensure headers are loaded
        headers = self.headers
        if not headers:
            return

        client_batch_size = batch_size or self._client.batch_size
        start_row = 2  # Skip header row (row 1)
        row_number = 2  # Track actual row number for records

        while True:
            rows = self._client.get_rows_batch(
                spreadsheet_id=self._spreadsheet_id,
                sheet_name=self._sheet_name,
                start_row=start_row,
                batch_size=client_batch_size,
            )

            if not rows:
                break

            for row in rows:
                yield self._row_to_record(row, row_number)
                row_number += 1

            # If we got fewer rows than requested, we've reached the end
            if len(rows) < client_batch_size:
                break

            start_row += client_batch_size

    def count_rows(self) -> int:
        """
        Count the number of data rows (excluding header).

        Note: This requires fetching all data, which can be expensive
        for large sheets. Use with caution.

        Returns:
            Number of data rows.
        """
        count = 0
        for _ in self.read_records():
            count += 1
        return count

    def read_sample(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Read a sample of records from the sheet.

        Args:
            n: Number of records to sample.

        Returns:
            List of sample records.
        """
        records = []
        for i, record in enumerate(self.read_records()):
            if i >= n:
                break
            records.append(record)
        return records


class StreamCatalog:
    """
    Catalog of available streams from a spreadsheet.

    Manages discovery and access to all sheet streams.
    """

    def __init__(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        include_row_number: bool = False,
    ):
        """
        Initialize the stream catalog.

        Args:
            client: Google Sheets API client.
            spreadsheet_id: ID of the spreadsheet.
            include_row_number: Whether to include row number in records.
        """
        self._client = client
        self._spreadsheet_id = spreadsheet_id
        self._include_row_number = include_row_number
        self._streams: Optional[Dict[str, SheetStream]] = None

    def _discover_streams(self) -> Dict[str, SheetStream]:
        """
        Discover all streams from the spreadsheet.

        Returns:
            Dictionary mapping sheet names to SheetStream instances.
        """
        sheet_names = self._client.get_sheet_names(self._spreadsheet_id)
        streams = {}

        for sheet_name in sheet_names:
            stream = SheetStream(
                client=self._client,
                spreadsheet_id=self._spreadsheet_id,
                sheet_name=sheet_name,
                include_row_number=self._include_row_number,
            )
            streams[sheet_name] = stream

        return streams

    @property
    def streams(self) -> Dict[str, SheetStream]:
        """
        Get all available streams.

        Returns:
            Dictionary mapping sheet names to streams.
        """
        if self._streams is None:
            self._streams = self._discover_streams()
        return self._streams

    def get_stream(self, sheet_name: str) -> Optional[SheetStream]:
        """
        Get a specific stream by sheet name.

        Args:
            sheet_name: Name of the sheet.

        Returns:
            SheetStream if found, None otherwise.
        """
        return self.streams.get(sheet_name)

    def get_stream_names(self) -> List[str]:
        """
        Get list of available stream names.

        Returns:
            List of sheet names.
        """
        return list(self.streams.keys())

    def get_catalog(self) -> Dict[str, Any]:
        """
        Get the full catalog in standard format.

        Returns:
            Catalog dictionary with stream definitions.
        """
        streams_list = []
        for stream in self.streams.values():
            try:
                streams_list.append(stream.get_json_schema())
            except Exception:
                # Skip streams that fail to generate schema
                continue

        return {"streams": streams_list}

    def select_streams(
        self,
        sheet_names: Optional[List[str]] = None,
        exclude_sheets: Optional[List[str]] = None,
    ) -> List[SheetStream]:
        """
        Select streams based on inclusion/exclusion lists.

        Args:
            sheet_names: List of sheets to include (None = all).
            exclude_sheets: List of sheets to exclude.

        Returns:
            List of selected SheetStream instances.
        """
        selected = []

        for name, stream in self.streams.items():
            # Check exclusion list
            if exclude_sheets and name in exclude_sheets:
                continue

            # Check inclusion list
            if sheet_names is not None and name not in sheet_names:
                continue

            selected.append(stream)

        return selected

    def __iter__(self) -> Iterator[SheetStream]:
        """Iterate over all streams."""
        return iter(self.streams.values())

    def __len__(self) -> int:
        """Get number of streams."""
        return len(self.streams)
