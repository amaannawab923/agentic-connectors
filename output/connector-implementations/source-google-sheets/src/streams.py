"""
Data stream definitions for Google Sheets connector.

This module defines stream classes for extracting data from Google Sheets,
including schema inference and record transformation.
"""

from typing import Any, Dict, Iterator, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

from .client import GoogleSheetsClient
from .utils import (
    sanitize_column_name,
    infer_schema_from_data,
    normalize_row,
    GoogleSheetsError,
)

logger = logging.getLogger(__name__)


@dataclass
class StreamSchema:
    """JSON Schema representation for a stream."""

    type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    additional_properties: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON schema dictionary."""
        return {
            "type": self.type,
            "properties": self.properties,
            "required": self.required,
            "additionalProperties": self.additional_properties
        }

    @classmethod
    def from_headers(
        cls,
        headers: List[str],
        sample_data: Optional[List[List[Any]]] = None,
        sanitize: bool = True
    ) -> "StreamSchema":
        """
        Create schema from headers and optional sample data.

        Args:
            headers: List of column headers
            sample_data: Optional sample data for type inference
            sanitize: Whether to sanitize column names

        Returns:
            StreamSchema instance
        """
        properties = {}

        if sample_data:
            # Infer types from sample data
            inferred = infer_schema_from_data(headers, sample_data)
            for header in headers:
                field_name = sanitize_column_name(header) if sanitize else header
                if field_name in inferred.get("properties", {}):
                    properties[field_name] = inferred["properties"][field_name]
                else:
                    properties[field_name] = {
                        "type": ["null", "string"],
                        "original_name": header
                    }
        else:
            # Default to string type
            for header in headers:
                field_name = sanitize_column_name(header) if sanitize else header
                properties[field_name] = {
                    "type": ["null", "string"],
                    "original_name": header
                }

        # Add _row_number field
        properties["_row_number"] = {
            "type": "integer",
            "description": "1-indexed row number in the sheet"
        }

        return cls(properties=properties)


@dataclass
class StreamMetadata:
    """Metadata for a stream."""

    name: str
    sheet_id: int
    row_count: int
    column_count: int
    schema: StreamSchema
    headers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "sheet_id": self.sheet_id,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "schema": self.schema.to_dict(),
            "headers": self.headers
        }


class BaseStream(ABC):
    """Abstract base class for data streams."""

    def __init__(
        self,
        name: str,
        client: GoogleSheetsClient,
        sanitize_names: bool = True,
        include_row_numbers: bool = True
    ):
        """
        Initialize base stream.

        Args:
            name: Stream name
            client: Google Sheets client
            sanitize_names: Whether to sanitize column names
            include_row_numbers: Whether to include row numbers
        """
        self.name = name
        self.client = client
        self.sanitize_names = sanitize_names
        self.include_row_numbers = include_row_numbers
        self._schema: Optional[StreamSchema] = None
        self._headers: Optional[List[str]] = None

    @property
    @abstractmethod
    def primary_key(self) -> Optional[List[str]]:
        """Get the primary key fields for this stream."""
        pass

    @property
    @abstractmethod
    def replication_method(self) -> str:
        """Get the replication method (FULL_REFRESH or INCREMENTAL)."""
        pass

    @abstractmethod
    def get_schema(self) -> StreamSchema:
        """Get the schema for this stream."""
        pass

    @abstractmethod
    def read_records(self) -> Iterator[Dict[str, Any]]:
        """Read records from the stream."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get stream metadata."""
        return {
            "name": self.name,
            "primary_key": self.primary_key,
            "replication_method": self.replication_method,
            "schema": self.get_schema().to_dict()
        }


class SheetStream(BaseStream):
    """
    Stream for a single sheet in a spreadsheet.

    This stream reads data from a specific sheet, treating the first row
    as headers and subsequent rows as data records.
    """

    def __init__(
        self,
        name: str,
        client: GoogleSheetsClient,
        sheet_id: int,
        header_row: int = 1,
        skip_rows: int = 0,
        range_notation: Optional[str] = None,
        sanitize_names: bool = True,
        include_row_numbers: bool = True,
        batch_size: int = 200
    ):
        """
        Initialize sheet stream.

        Args:
            name: Sheet name (also used as stream name)
            client: Google Sheets client
            sheet_id: Sheet ID within the spreadsheet
            header_row: Row number containing headers (1-indexed)
            skip_rows: Number of rows to skip after headers
            range_notation: Optional specific range to read
            sanitize_names: Whether to sanitize column names
            include_row_numbers: Whether to include row numbers
            batch_size: Number of rows to read per API call
        """
        super().__init__(name, client, sanitize_names, include_row_numbers)
        self.sheet_id = sheet_id
        self.header_row = header_row
        self.skip_rows = skip_rows
        self.range_notation = range_notation
        self.batch_size = batch_size
        self._row_count: Optional[int] = None
        self._column_count: Optional[int] = None

    @property
    def primary_key(self) -> Optional[List[str]]:
        """
        Get primary key for this stream.

        Uses _row_number as the primary key since Google Sheets
        doesn't have a native primary key concept.
        """
        if self.include_row_numbers:
            return ["_row_number"]
        return None

    @property
    def replication_method(self) -> str:
        """
        Get replication method.

        Google Sheets doesn't support change tracking,
        so we use FULL_REFRESH.
        """
        return "FULL_REFRESH"

    @property
    def row_count(self) -> int:
        """Get the row count for this sheet."""
        if self._row_count is None:
            self._row_count = self.client.get_row_count(self.name)
        return self._row_count

    @property
    def column_count(self) -> int:
        """Get the column count for this sheet."""
        if self._column_count is None:
            self._column_count = self.client.get_column_count(self.name)
        return self._column_count

    def get_headers(self) -> List[str]:
        """
        Get column headers for this sheet.

        Returns:
            List of header strings
        """
        if self._headers is None:
            self._headers = self.client.get_headers(self.name, self.header_row)
        return self._headers

    def get_schema(self) -> StreamSchema:
        """
        Get the schema for this sheet.

        Infers schema from headers and optional sample data.

        Returns:
            StreamSchema instance
        """
        if self._schema is not None:
            return self._schema

        headers = self.get_headers()

        if not headers:
            self._schema = StreamSchema()
            return self._schema

        # Get sample data for type inference
        start_row = self.header_row + 1 + self.skip_rows
        try:
            sample_data = []
            for batch in self.client.read_sheet_in_batches(
                self.name,
                start_row=start_row,
                batch_size=min(100, self.batch_size)
            ):
                sample_data.extend(batch)
                if len(sample_data) >= 100:
                    break
        except GoogleSheetsError:
            sample_data = []

        self._schema = StreamSchema.from_headers(
            headers,
            sample_data[:100] if sample_data else None,
            sanitize=self.sanitize_names
        )

        return self._schema

    def read_records(self) -> Iterator[Dict[str, Any]]:
        """
        Read all records from the sheet.

        Yields:
            Dictionary records with column names as keys
        """
        headers = self.get_headers()

        if not headers:
            logger.warning(f"No headers found in sheet '{self.name}'")
            return

        # Calculate start row (header row + 1 + skip rows)
        start_row = self.header_row + 1 + self.skip_rows

        logger.info(f"Starting to read records from sheet '{self.name}'")

        record_count = 0

        for batch in self.client.read_sheet_in_batches(
            self.name,
            start_row=start_row,
            batch_size=self.batch_size
        ):
            for row_offset, row in enumerate(batch):
                row_number = start_row + record_count

                record = self._transform_row(row, headers, row_number)
                yield record

                record_count += 1

        logger.info(f"Read {record_count} records from sheet '{self.name}'")

    def _transform_row(
        self,
        row: List[Any],
        headers: List[str],
        row_number: int
    ) -> Dict[str, Any]:
        """
        Transform a row into a record dictionary.

        Args:
            row: List of cell values
            headers: List of column headers
            row_number: 1-indexed row number

        Returns:
            Dictionary record
        """
        record = {}

        # Add row number if configured
        if self.include_row_numbers:
            record["_row_number"] = row_number

        # Add column values
        for col_idx, header in enumerate(headers):
            if not header:
                continue

            field_name = sanitize_column_name(header) if self.sanitize_names else header

            if col_idx < len(row):
                value = row[col_idx]
                # Convert empty strings to None
                record[field_name] = value if value != "" else None
            else:
                record[field_name] = None

        return record

    def get_stream_metadata(self) -> StreamMetadata:
        """
        Get complete metadata for this stream.

        Returns:
            StreamMetadata instance
        """
        return StreamMetadata(
            name=self.name,
            sheet_id=self.sheet_id,
            row_count=self.row_count,
            column_count=self.column_count,
            schema=self.get_schema(),
            headers=self.get_headers()
        )


class SpreadsheetStreamFactory:
    """
    Factory for creating streams from a spreadsheet.

    Discovers all sheets in a spreadsheet and creates
    corresponding stream objects.
    """

    def __init__(
        self,
        client: GoogleSheetsClient,
        sanitize_names: bool = True,
        include_row_numbers: bool = True,
        batch_size: int = 200
    ):
        """
        Initialize stream factory.

        Args:
            client: Google Sheets client
            sanitize_names: Whether to sanitize column names
            include_row_numbers: Whether to include row numbers
            batch_size: Batch size for reading
        """
        self.client = client
        self.sanitize_names = sanitize_names
        self.include_row_numbers = include_row_numbers
        self.batch_size = batch_size

    def discover_streams(self) -> List[SheetStream]:
        """
        Discover all sheets and create stream objects.

        Returns:
            List of SheetStream instances
        """
        metadata = self.client.get_spreadsheet_metadata()
        streams = []

        for sheet in metadata.get("sheets", []):
            props = sheet.get("properties", {})
            sheet_name = props.get("title")
            sheet_id = props.get("sheetId")

            if sheet_name is None:
                continue

            stream = SheetStream(
                name=sheet_name,
                client=self.client,
                sheet_id=sheet_id,
                sanitize_names=self.sanitize_names,
                include_row_numbers=self.include_row_numbers,
                batch_size=self.batch_size
            )

            streams.append(stream)

        logger.info(f"Discovered {len(streams)} streams in spreadsheet")
        return streams

    def get_stream(self, sheet_name: str) -> Optional[SheetStream]:
        """
        Get a specific stream by sheet name.

        Args:
            sheet_name: Name of the sheet

        Returns:
            SheetStream instance or None if not found
        """
        metadata = self.client.get_spreadsheet_metadata()

        for sheet in metadata.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == sheet_name:
                return SheetStream(
                    name=sheet_name,
                    client=self.client,
                    sheet_id=props.get("sheetId"),
                    sanitize_names=self.sanitize_names,
                    include_row_numbers=self.include_row_numbers,
                    batch_size=self.batch_size
                )

        return None
