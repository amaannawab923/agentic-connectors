"""
Stream definitions for Google Sheets connector.

Handles reading data from individual sheets with support for:
- Batched reading for large sheets
- Header normalization
- Row number tracking
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from .client import GoogleSheetsClient
from .utils import normalize_header, build_range_notation

logger = logging.getLogger(__name__)


@dataclass
class StreamMetadata:
    """Metadata about a stream (sheet)."""

    name: str
    sheet_id: int
    row_count: int
    column_count: int
    frozen_row_count: int = 0
    frozen_column_count: int = 0

    @property
    def estimated_record_count(self) -> int:
        """Estimate the number of data records (excluding header)."""
        return max(0, self.row_count - 1)


@dataclass
class StreamSchema:
    """Schema information for a stream."""

    stream_name: str
    json_schema: Dict[str, Any]
    key_properties: List[str]

    @property
    def properties(self) -> Dict[str, Any]:
        """Get the schema properties."""
        return self.json_schema.get("properties", {})

    @property
    def column_names(self) -> List[str]:
        """Get list of column names."""
        return list(self.properties.keys())


class SheetStream:
    """
    Represents a single sheet as a data stream.

    Handles:
    - Reading data in batches to manage memory and API quotas
    - Header normalization (handling duplicates, empty headers)
    - Converting rows to dictionaries with proper column mapping
    """

    def __init__(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        sheet_name: str,
        header_row: int = 1,
        batch_size: int = 1000,
        include_row_number: bool = True,
        max_columns: str = "ZZ",
    ):
        """
        Initialize a sheet stream.

        Args:
            client: Google Sheets API client.
            spreadsheet_id: The spreadsheet ID.
            sheet_name: Name of the sheet to read.
            header_row: Row number containing headers (1-indexed).
            batch_size: Number of rows to fetch per API call.
            include_row_number: Include a '_row_number' field in records.
            max_columns: Maximum column to read (A1 notation, e.g., "ZZ").
        """
        self.client = client
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.header_row = header_row
        self.batch_size = batch_size
        self.include_row_number = include_row_number
        self.max_columns = max_columns

        self._headers: Optional[List[str]] = None
        self._raw_headers: Optional[List[str]] = None

    @property
    def headers(self) -> List[str]:
        """Get normalized column headers, fetching if necessary."""
        if self._headers is None:
            self._fetch_headers()
        return self._headers

    @property
    def raw_headers(self) -> List[str]:
        """Get original column headers without normalization."""
        if self._raw_headers is None:
            self._fetch_headers()
        return self._raw_headers

    def _fetch_headers(self) -> None:
        """Fetch and normalize headers from the spreadsheet."""
        header_range = build_range_notation(
            self.sheet_name,
            start_row=self.header_row,
            end_row=self.header_row,
            end_col=self.max_columns,
        )

        result = self.client.get_values(
            self.spreadsheet_id,
            header_range,
            value_render_option="FORMATTED_VALUE",
        )

        self._raw_headers = result.get("values", [[]])[0] if result.get("values") else []
        self._headers = normalize_header(self._raw_headers)

        logger.debug(f"Fetched {len(self._headers)} headers from '{self.sheet_name}'")

    def _row_to_record(
        self,
        row: List[Any],
        row_number: int,
    ) -> Dict[str, Any]:
        """
        Convert a row to a record dictionary.

        Args:
            row: List of cell values.
            row_number: Original row number in the spreadsheet (1-indexed).

        Returns:
            Dictionary mapping column headers to values.
        """
        record = {}

        # Add row number if configured
        if self.include_row_number:
            record["_row_number"] = row_number

        # Map values to headers
        for i, header in enumerate(self.headers):
            if i < len(row):
                value = row[i]
                # Convert empty strings to None for consistency
                if value == "":
                    value = None
                record[header] = value
            else:
                record[header] = None

        return record

    def read(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read all records from the sheet.

        Yields:
            Dictionary for each row with column headers as keys.
        """
        # Ensure headers are loaded
        headers = self.headers

        if not headers:
            logger.warning(f"No headers found in sheet '{self.sheet_name}'")
            return

        # Start reading from the row after headers
        start_row = self.header_row + 1
        total_records = 0
        empty_batch_count = 0
        max_empty_batches = 3  # Stop after this many consecutive empty batches

        while True:
            end_row = start_row + self.batch_size - 1

            data_range = build_range_notation(
                self.sheet_name,
                start_row=start_row,
                end_row=end_row,
                end_col=self.max_columns,
            )

            logger.debug(f"Fetching batch: {data_range}")

            result = self.client.get_values(
                self.spreadsheet_id,
                data_range,
                value_render_option="UNFORMATTED_VALUE",
                date_time_render_option="FORMATTED_STRING",
            )

            rows = result.get("values", [])

            if not rows:
                empty_batch_count += 1
                if empty_batch_count >= max_empty_batches:
                    logger.debug(
                        f"Stopping after {max_empty_batches} consecutive empty batches"
                    )
                    break
                # Move to next batch in case there's a gap
                start_row = end_row + 1
                continue

            # Reset empty batch counter when we find data
            empty_batch_count = 0

            # Process each row
            for i, row in enumerate(rows):
                row_number = start_row + i

                # Skip completely empty rows
                if not any(cell for cell in row if cell is not None and cell != ""):
                    continue

                record = self._row_to_record(row, row_number)
                total_records += 1
                yield record

            # Check if we've reached the end
            if len(rows) < self.batch_size:
                logger.debug(
                    f"Last batch contained {len(rows)} rows (less than batch size)"
                )
                break

            start_row = end_row + 1

        logger.info(
            f"Read {total_records} records from sheet '{self.sheet_name}'"
        )

    def read_range(
        self,
        start_row: int,
        end_row: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from a specific row range.

        Args:
            start_row: First row to read (1-indexed, data row not header).
            end_row: Last row to read (inclusive).

        Yields:
            Dictionary for each row with column headers as keys.
        """
        # Ensure headers are loaded
        headers = self.headers

        if not headers:
            logger.warning(f"No headers found in sheet '{self.sheet_name}'")
            return

        data_range = build_range_notation(
            self.sheet_name,
            start_row=start_row,
            end_row=end_row,
            end_col=self.max_columns,
        )

        result = self.client.get_values(
            self.spreadsheet_id,
            data_range,
            value_render_option="UNFORMATTED_VALUE",
            date_time_render_option="FORMATTED_STRING",
        )

        rows = result.get("values", [])

        for i, row in enumerate(rows):
            row_number = start_row + i

            # Skip completely empty rows
            if not any(cell for cell in row if cell is not None and cell != ""):
                continue

            yield self._row_to_record(row, row_number)

    def get_record_count(self) -> int:
        """
        Get an estimate of the number of records in the sheet.

        Note: This fetches the first column to count rows, which is
        more efficient than fetching all data.

        Returns:
            Estimated number of data records (excluding header).
        """
        count = self.client.get_sheet_row_count(
            self.spreadsheet_id,
            self.sheet_name,
        )
        # Subtract header row
        return max(0, count - self.header_row)


class MultiSheetReader:
    """
    Reads data from multiple sheets in a spreadsheet.

    Useful for extracting all data from a spreadsheet while maintaining
    stream context.
    """

    def __init__(
        self,
        client: GoogleSheetsClient,
        spreadsheet_id: str,
        sheet_names: Optional[List[str]] = None,
        header_row: int = 1,
        batch_size: int = 1000,
        include_row_number: bool = True,
    ):
        """
        Initialize multi-sheet reader.

        Args:
            client: Google Sheets API client.
            spreadsheet_id: The spreadsheet ID.
            sheet_names: List of sheets to read. If None, reads all sheets.
            header_row: Default header row for all sheets.
            batch_size: Default batch size for all sheets.
            include_row_number: Include row numbers in records.
        """
        self.client = client
        self.spreadsheet_id = spreadsheet_id
        self.sheet_names = sheet_names
        self.header_row = header_row
        self.batch_size = batch_size
        self.include_row_number = include_row_number

    def _discover_sheets(self) -> List[str]:
        """Discover all sheet names in the spreadsheet."""
        metadata = self.client.get_spreadsheet(self.spreadsheet_id)
        return [
            sheet["properties"]["title"]
            for sheet in metadata.get("sheets", [])
        ]

    def read_all(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read all records from all configured sheets.

        Yields:
            Dictionary containing stream name and record data:
            {
                "_stream": "sheet_name",
                ...record_data
            }
        """
        sheets = self.sheet_names or self._discover_sheets()

        for sheet_name in sheets:
            logger.info(f"Reading sheet: {sheet_name}")

            stream = SheetStream(
                client=self.client,
                spreadsheet_id=self.spreadsheet_id,
                sheet_name=sheet_name,
                header_row=self.header_row,
                batch_size=self.batch_size,
                include_row_number=self.include_row_number,
            )

            for record in stream.read():
                yield {"_stream": sheet_name, **record}

    def get_all_headers(self) -> Dict[str, List[str]]:
        """
        Get headers for all configured sheets.

        Returns:
            Dictionary mapping sheet names to their header lists.
        """
        sheets = self.sheet_names or self._discover_sheets()
        headers = {}

        for sheet_name in sheets:
            stream = SheetStream(
                client=self.client,
                spreadsheet_id=self.spreadsheet_id,
                sheet_name=sheet_name,
                header_row=self.header_row,
            )
            headers[sheet_name] = stream.headers

        return headers
