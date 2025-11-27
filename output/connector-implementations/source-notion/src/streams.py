"""
Data stream definitions for the Notion source connector.

This module defines the available data streams (Users, Databases, Pages, Blocks, Comments)
and provides the schema definitions and read logic for each stream.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional

from .client import NotionClient
from .config import NotionConfig, StreamState
from .utils import (
    extract_plain_text,
    extract_title,
    flatten_properties,
    format_datetime_for_notion,
    extract_block_content,
    get_block_url,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Base Stream
# =============================================================================


class BaseStream(ABC):
    """
    Abstract base class for Notion data streams.

    All streams must implement the read method and define their schema.
    """

    # Stream metadata - override in subclasses
    name: str = "base"
    primary_key: str = "id"
    cursor_field: Optional[str] = None
    supports_incremental: bool = False

    def __init__(self, client: NotionClient, config: NotionConfig):
        """
        Initialize the stream.

        Args:
            client: NotionClient instance
            config: NotionConfig instance
        """
        self.client = client
        self.config = config

    @property
    @abstractmethod
    def json_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for this stream.

        Returns:
            JSON schema dictionary
        """
        pass

    @abstractmethod
    def read(
        self,
        state: Optional[StreamState] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from this stream.

        Args:
            state: Optional state for incremental sync

        Yields:
            Record dictionaries
        """
        pass

    def get_updated_state(
        self,
        current_state: Optional[StreamState],
        latest_record: Dict[str, Any],
    ) -> StreamState:
        """
        Get updated state based on the latest record.

        Args:
            current_state: Current stream state
            latest_record: Most recent record read

        Returns:
            Updated StreamState
        """
        if not self.cursor_field:
            return current_state or StreamState()

        state = current_state or StreamState()
        cursor_value = latest_record.get(self.cursor_field)

        if cursor_value:
            # Update if newer than current state
            if not state.cursor_value or cursor_value > state.cursor_value:
                state.cursor_value = cursor_value

        return state


# =============================================================================
# Users Stream
# =============================================================================


class UsersStream(BaseStream):
    """Stream for Notion workspace users."""

    name = "users"
    primary_key = "id"
    cursor_field = None
    supports_incremental = False

    @property
    def json_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique user identifier"},
                "object": {"type": "string", "description": "Always 'user'"},
                "type": {"type": ["string", "null"], "description": "User type (person or bot)"},
                "name": {"type": ["string", "null"], "description": "User's display name"},
                "avatar_url": {"type": ["string", "null"], "description": "URL of user's avatar"},
                "email": {"type": ["string", "null"], "description": "User's email (for person type)"},
                "is_bot": {"type": "boolean", "description": "Whether user is a bot"},
                "bot_owner_type": {"type": ["string", "null"], "description": "Bot owner type"},
                "bot_workspace_name": {"type": ["string", "null"], "description": "Bot's workspace name"},
            },
            "required": ["id", "object"],
        }

    def read(
        self,
        state: Optional[StreamState] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all users from the workspace.

        Yields:
            User records
        """
        logger.info("Reading users stream")

        for user in self.client.list_users():
            record = {
                "id": user.get("id"),
                "object": user.get("object"),
                "type": user.get("type"),
                "name": user.get("name"),
                "avatar_url": user.get("avatar_url"),
                "email": None,
                "is_bot": False,
                "bot_owner_type": None,
                "bot_workspace_name": None,
            }

            # Handle person-specific fields
            if user.get("type") == "person":
                person = user.get("person", {})
                record["email"] = person.get("email")
                record["is_bot"] = False

            # Handle bot-specific fields
            elif user.get("type") == "bot":
                bot = user.get("bot", {})
                record["is_bot"] = True
                record["bot_workspace_name"] = bot.get("workspace_name")

                owner = bot.get("owner", {})
                record["bot_owner_type"] = owner.get("type")

            yield record


# =============================================================================
# Databases Stream
# =============================================================================


class DatabasesStream(BaseStream):
    """Stream for Notion databases."""

    name = "databases"
    primary_key = "id"
    cursor_field = "last_edited_time"
    supports_incremental = True

    @property
    def json_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique database identifier"},
                "object": {"type": "string", "description": "Always 'database'"},
                "created_time": {"type": ["string", "null"], "description": "ISO 8601 creation timestamp"},
                "last_edited_time": {"type": ["string", "null"], "description": "ISO 8601 last edit timestamp"},
                "created_by_id": {"type": ["string", "null"], "description": "ID of creator"},
                "last_edited_by_id": {"type": ["string", "null"], "description": "ID of last editor"},
                "title": {"type": ["string", "null"], "description": "Database title"},
                "description": {"type": ["string", "null"], "description": "Database description"},
                "icon_type": {"type": ["string", "null"], "description": "Icon type (emoji, file, external)"},
                "icon_value": {"type": ["string", "null"], "description": "Icon value (emoji or URL)"},
                "cover_type": {"type": ["string", "null"], "description": "Cover type"},
                "cover_url": {"type": ["string", "null"], "description": "Cover image URL"},
                "url": {"type": ["string", "null"], "description": "Notion URL"},
                "public_url": {"type": ["string", "null"], "description": "Public URL if published"},
                "is_inline": {"type": ["boolean", "null"], "description": "Whether database is inline"},
                "archived": {"type": ["boolean", "null"], "description": "Whether database is archived"},
                "properties": {"type": ["object", "null"], "description": "Database schema properties"},
                "property_names": {"type": ["array", "null"], "items": {"type": "string"}, "description": "List of property names"},
            },
            "required": ["id", "object"],
        }

    def read(
        self,
        state: Optional[StreamState] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all databases from the workspace.

        Args:
            state: Optional state for incremental sync

        Yields:
            Database records
        """
        logger.info("Reading databases stream")

        # Determine start time for incremental sync
        start_time = None
        if state and state.cursor_value:
            start_time = state.cursor_value
        elif self.config.start_date:
            start_time = format_datetime_for_notion(self.config.start_date)

        for database in self.client.search_databases():
            # Skip if before start time (for incremental sync)
            last_edited = database.get("last_edited_time")
            if start_time and last_edited and last_edited < start_time:
                continue

            # Extract icon
            icon = database.get("icon") or {}
            icon_type = icon.get("type")
            icon_value = None
            if icon_type == "emoji":
                icon_value = icon.get("emoji")
            elif icon_type == "external":
                icon_value = icon.get("external", {}).get("url")
            elif icon_type == "file":
                icon_value = icon.get("file", {}).get("url")

            # Extract cover
            cover = database.get("cover") or {}
            cover_type = cover.get("type")
            cover_url = None
            if cover_type == "external":
                cover_url = cover.get("external", {}).get("url")
            elif cover_type == "file":
                cover_url = cover.get("file", {}).get("url")

            # Extract property names
            properties = database.get("properties", {})
            property_names = list(properties.keys())

            record = {
                "id": database.get("id"),
                "object": database.get("object"),
                "created_time": database.get("created_time"),
                "last_edited_time": database.get("last_edited_time"),
                "created_by_id": database.get("created_by", {}).get("id"),
                "last_edited_by_id": database.get("last_edited_by", {}).get("id"),
                "title": extract_plain_text(database.get("title", [])),
                "description": extract_plain_text(database.get("description", [])),
                "icon_type": icon_type,
                "icon_value": icon_value,
                "cover_type": cover_type,
                "cover_url": cover_url,
                "url": database.get("url"),
                "public_url": database.get("public_url"),
                "is_inline": database.get("is_inline"),
                "archived": database.get("archived"),
                "properties": properties,
                "property_names": property_names,
            }

            yield record


# =============================================================================
# Pages Stream
# =============================================================================


class PagesStream(BaseStream):
    """Stream for Notion pages."""

    name = "pages"
    primary_key = "id"
    cursor_field = "last_edited_time"
    supports_incremental = True

    @property
    def json_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique page identifier"},
                "object": {"type": "string", "description": "Always 'page'"},
                "created_time": {"type": ["string", "null"], "description": "ISO 8601 creation timestamp"},
                "last_edited_time": {"type": ["string", "null"], "description": "ISO 8601 last edit timestamp"},
                "created_by_id": {"type": ["string", "null"], "description": "ID of creator"},
                "last_edited_by_id": {"type": ["string", "null"], "description": "ID of last editor"},
                "parent_type": {"type": ["string", "null"], "description": "Parent type (database_id, page_id, workspace)"},
                "parent_id": {"type": ["string", "null"], "description": "Parent identifier"},
                "title": {"type": ["string", "null"], "description": "Page title"},
                "icon_type": {"type": ["string", "null"], "description": "Icon type"},
                "icon_value": {"type": ["string", "null"], "description": "Icon value"},
                "cover_type": {"type": ["string", "null"], "description": "Cover type"},
                "cover_url": {"type": ["string", "null"], "description": "Cover URL"},
                "url": {"type": ["string", "null"], "description": "Notion URL"},
                "public_url": {"type": ["string", "null"], "description": "Public URL if published"},
                "archived": {"type": ["boolean", "null"], "description": "Whether page is archived"},
                "in_trash": {"type": ["boolean", "null"], "description": "Whether page is in trash"},
                "properties": {"type": ["object", "null"], "description": "Raw page properties"},
                "properties_flat": {"type": ["object", "null"], "description": "Flattened property values"},
            },
            "required": ["id", "object"],
        }

    def read(
        self,
        state: Optional[StreamState] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all pages from the workspace.

        Args:
            state: Optional state for incremental sync

        Yields:
            Page records
        """
        logger.info("Reading pages stream")

        # Determine start time for incremental sync
        start_time = None
        if state and state.cursor_value:
            start_time = state.cursor_value
        elif self.config.start_date:
            start_time = format_datetime_for_notion(self.config.start_date)

        for page in self.client.search_pages():
            # Skip if before start time (for incremental sync)
            last_edited = page.get("last_edited_time")
            if start_time and last_edited and last_edited < start_time:
                continue

            yield self._transform_page(page)

    def _transform_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a raw page object into a record.

        Args:
            page: Raw page object from API

        Returns:
            Transformed page record
        """
        # Extract parent info
        parent = page.get("parent", {})
        parent_type = parent.get("type")
        parent_id = None
        if parent_type == "database_id":
            parent_id = parent.get("database_id")
        elif parent_type == "page_id":
            parent_id = parent.get("page_id")
        elif parent_type == "workspace":
            parent_id = "workspace"

        # Extract icon
        icon = page.get("icon") or {}
        icon_type = icon.get("type")
        icon_value = None
        if icon_type == "emoji":
            icon_value = icon.get("emoji")
        elif icon_type == "external":
            icon_value = icon.get("external", {}).get("url")
        elif icon_type == "file":
            icon_value = icon.get("file", {}).get("url")

        # Extract cover
        cover = page.get("cover") or {}
        cover_type = cover.get("type")
        cover_url = None
        if cover_type == "external":
            cover_url = cover.get("external", {}).get("url")
        elif cover_type == "file":
            cover_url = cover.get("file", {}).get("url")

        # Extract and flatten properties
        properties = page.get("properties", {})
        title = extract_title(properties)
        properties_flat = flatten_properties(properties)

        return {
            "id": page.get("id"),
            "object": page.get("object"),
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
            "created_by_id": page.get("created_by", {}).get("id"),
            "last_edited_by_id": page.get("last_edited_by", {}).get("id"),
            "parent_type": parent_type,
            "parent_id": parent_id,
            "title": title,
            "icon_type": icon_type,
            "icon_value": icon_value,
            "cover_type": cover_type,
            "cover_url": cover_url,
            "url": page.get("url"),
            "public_url": page.get("public_url"),
            "archived": page.get("archived"),
            "in_trash": page.get("in_trash"),
            "properties": properties,
            "properties_flat": properties_flat,
        }


# =============================================================================
# Blocks Stream
# =============================================================================


class BlocksStream(BaseStream):
    """Stream for Notion blocks (page content)."""

    name = "blocks"
    primary_key = "id"
    cursor_field = "last_edited_time"
    supports_incremental = True

    def __init__(
        self,
        client: NotionClient,
        config: NotionConfig,
        page_ids: Optional[List[str]] = None,
    ):
        """
        Initialize the blocks stream.

        Args:
            client: NotionClient instance
            config: NotionConfig instance
            page_ids: Optional list of page IDs to fetch blocks from
        """
        super().__init__(client, config)
        self.page_ids = page_ids

    @property
    def json_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique block identifier"},
                "object": {"type": "string", "description": "Always 'block'"},
                "type": {"type": ["string", "null"], "description": "Block type (paragraph, heading_1, etc.)"},
                "created_time": {"type": ["string", "null"], "description": "ISO 8601 creation timestamp"},
                "last_edited_time": {"type": ["string", "null"], "description": "ISO 8601 last edit timestamp"},
                "created_by_id": {"type": ["string", "null"], "description": "ID of creator"},
                "last_edited_by_id": {"type": ["string", "null"], "description": "ID of last editor"},
                "parent_type": {"type": ["string", "null"], "description": "Parent type"},
                "parent_id": {"type": ["string", "null"], "description": "Parent identifier"},
                "page_id": {"type": ["string", "null"], "description": "ID of containing page"},
                "has_children": {"type": ["boolean", "null"], "description": "Whether block has children"},
                "archived": {"type": ["boolean", "null"], "description": "Whether block is archived"},
                "in_trash": {"type": ["boolean", "null"], "description": "Whether block is in trash"},
                "depth": {"type": ["integer", "null"], "description": "Nesting depth"},
                "content": {"type": ["string", "null"], "description": "Plain text content"},
                "url": {"type": ["string", "null"], "description": "URL if block contains a link"},
                "block_data": {"type": ["object", "null"], "description": "Raw block type-specific data"},
            },
            "required": ["id", "object"],
        }

    def read(
        self,
        state: Optional[StreamState] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read blocks from pages.

        Args:
            state: Optional state for incremental sync

        Yields:
            Block records
        """
        logger.info("Reading blocks stream")

        if not self.config.fetch_page_blocks:
            logger.info("Block fetching is disabled")
            return

        # Determine which pages to fetch blocks from
        page_ids = self.page_ids

        if not page_ids:
            # Fetch all pages first
            logger.info("Fetching page IDs for block extraction")
            page_ids = []
            for page in self.client.search_pages():
                page_ids.append(page.get("id"))

        # Fetch blocks for each page
        for page_id in page_ids:
            logger.debug(f"Fetching blocks for page {page_id}")

            try:
                for block in self.client.get_all_blocks(
                    page_id,
                    max_depth=self.config.max_block_depth,
                ):
                    yield self._transform_block(block, page_id)
            except Exception as e:
                logger.warning(f"Failed to fetch blocks for page {page_id}: {e}")
                continue

    def _transform_block(
        self,
        block: Dict[str, Any],
        page_id: str,
    ) -> Dict[str, Any]:
        """
        Transform a raw block object into a record.

        Args:
            block: Raw block object from API
            page_id: ID of the parent page

        Returns:
            Transformed block record
        """
        block_type = block.get("type")
        block_data = block.get(block_type, {}) if block_type else {}

        # Extract parent info
        parent = block.get("parent", {})
        parent_type = parent.get("type")
        parent_id = None
        if parent_type == "page_id":
            parent_id = parent.get("page_id")
        elif parent_type == "block_id":
            parent_id = parent.get("block_id")

        # Extract content and URL
        content = extract_block_content(block)
        url = get_block_url(block)

        return {
            "id": block.get("id"),
            "object": block.get("object"),
            "type": block_type,
            "created_time": block.get("created_time"),
            "last_edited_time": block.get("last_edited_time"),
            "created_by_id": block.get("created_by", {}).get("id"),
            "last_edited_by_id": block.get("last_edited_by", {}).get("id"),
            "parent_type": parent_type,
            "parent_id": parent_id,
            "page_id": page_id,
            "has_children": block.get("has_children"),
            "archived": block.get("archived"),
            "in_trash": block.get("in_trash"),
            "depth": block.get("_depth", 0),
            "content": content,
            "url": url,
            "block_data": block_data,
        }


# =============================================================================
# Comments Stream
# =============================================================================


class CommentsStream(BaseStream):
    """Stream for Notion comments."""

    name = "comments"
    primary_key = "id"
    cursor_field = "created_time"
    supports_incremental = True

    def __init__(
        self,
        client: NotionClient,
        config: NotionConfig,
        page_ids: Optional[List[str]] = None,
    ):
        """
        Initialize the comments stream.

        Args:
            client: NotionClient instance
            config: NotionConfig instance
            page_ids: Optional list of page IDs to fetch comments from
        """
        super().__init__(client, config)
        self.page_ids = page_ids

    @property
    def json_schema(self) -> Dict[str, Any]:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique comment identifier"},
                "object": {"type": "string", "description": "Always 'comment'"},
                "discussion_id": {"type": ["string", "null"], "description": "Discussion thread ID"},
                "created_time": {"type": ["string", "null"], "description": "ISO 8601 creation timestamp"},
                "last_edited_time": {"type": ["string", "null"], "description": "ISO 8601 last edit timestamp"},
                "created_by_id": {"type": ["string", "null"], "description": "ID of comment author"},
                "parent_type": {"type": ["string", "null"], "description": "Parent type (page_id or block_id)"},
                "parent_id": {"type": ["string", "null"], "description": "Parent identifier"},
                "page_id": {"type": ["string", "null"], "description": "ID of containing page"},
                "content": {"type": ["string", "null"], "description": "Plain text content"},
                "rich_text": {"type": ["array", "null"], "description": "Rich text content array"},
            },
            "required": ["id", "object"],
        }

    def read(
        self,
        state: Optional[StreamState] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read comments from pages.

        Args:
            state: Optional state for incremental sync

        Yields:
            Comment records
        """
        logger.info("Reading comments stream")

        # Determine which pages to fetch comments from
        page_ids = self.page_ids

        if not page_ids:
            # Fetch all pages first
            logger.info("Fetching page IDs for comment extraction")
            page_ids = []
            for page in self.client.search_pages():
                page_ids.append(page.get("id"))

        # Determine start time for incremental sync
        start_time = None
        if state and state.cursor_value:
            start_time = state.cursor_value
        elif self.config.start_date:
            start_time = format_datetime_for_notion(self.config.start_date)

        # Fetch comments for each page
        for page_id in page_ids:
            logger.debug(f"Fetching comments for page {page_id}")

            try:
                for comment in self.client.get_comments(page_id):
                    # Skip if before start time
                    created_time = comment.get("created_time")
                    if start_time and created_time and created_time < start_time:
                        continue

                    yield self._transform_comment(comment, page_id)
            except Exception as e:
                logger.warning(f"Failed to fetch comments for page {page_id}: {e}")
                continue

    def _transform_comment(
        self,
        comment: Dict[str, Any],
        page_id: str,
    ) -> Dict[str, Any]:
        """
        Transform a raw comment object into a record.

        Args:
            comment: Raw comment object from API
            page_id: ID of the parent page

        Returns:
            Transformed comment record
        """
        # Extract parent info
        parent = comment.get("parent", {})
        parent_type = parent.get("type")
        parent_id = None
        if parent_type == "page_id":
            parent_id = parent.get("page_id")
        elif parent_type == "block_id":
            parent_id = parent.get("block_id")

        # Extract content
        rich_text = comment.get("rich_text", [])
        content = extract_plain_text(rich_text)

        return {
            "id": comment.get("id"),
            "object": comment.get("object"),
            "discussion_id": comment.get("discussion_id"),
            "created_time": comment.get("created_time"),
            "last_edited_time": comment.get("last_edited_time"),
            "created_by_id": comment.get("created_by", {}).get("id"),
            "parent_type": parent_type,
            "parent_id": parent_id,
            "page_id": page_id,
            "content": content,
            "rich_text": rich_text,
        }


# =============================================================================
# Database Pages Stream (for specific database)
# =============================================================================


class DatabasePagesStream(BaseStream):
    """Stream for pages within a specific database."""

    primary_key = "id"
    cursor_field = "last_edited_time"
    supports_incremental = True

    def __init__(
        self,
        client: NotionClient,
        config: NotionConfig,
        database_id: str,
        database_name: Optional[str] = None,
    ):
        """
        Initialize the database pages stream.

        Args:
            client: NotionClient instance
            config: NotionConfig instance
            database_id: ID of the database to query
            database_name: Optional name for the stream
        """
        super().__init__(client, config)
        self.database_id = database_id
        self._name = database_name or f"database_{database_id[:8]}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def json_schema(self) -> Dict[str, Any]:
        # Same schema as pages stream
        return PagesStream(self.client, self.config).json_schema

    def read(
        self,
        state: Optional[StreamState] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Read all pages from the database.

        Args:
            state: Optional state for incremental sync

        Yields:
            Page records
        """
        logger.info(f"Reading database pages stream for {self.database_id}")

        # Build filter for incremental sync
        filter_conditions = None
        if state and state.cursor_value:
            filter_conditions = {
                "timestamp": "last_edited_time",
                "last_edited_time": {
                    "on_or_after": state.cursor_value,
                },
            }
        elif self.config.start_date:
            filter_conditions = {
                "timestamp": "last_edited_time",
                "last_edited_time": {
                    "on_or_after": format_datetime_for_notion(self.config.start_date),
                },
            }

        # Sort by last_edited_time for incremental sync
        sorts = [{"timestamp": "last_edited_time", "direction": "ascending"}]

        pages_stream = PagesStream(self.client, self.config)

        for page in self.client.query_database(
            self.database_id,
            filter=filter_conditions,
            sorts=sorts,
        ):
            yield pages_stream._transform_page(page)


# =============================================================================
# Stream Factory
# =============================================================================


def get_all_streams(
    client: NotionClient,
    config: NotionConfig,
) -> List[BaseStream]:
    """
    Get all available streams.

    Args:
        client: NotionClient instance
        config: NotionConfig instance

    Returns:
        List of stream instances
    """
    streams: List[BaseStream] = [
        UsersStream(client, config),
        DatabasesStream(client, config),
        PagesStream(client, config),
    ]

    # Add blocks stream if enabled
    if config.fetch_page_blocks:
        streams.append(BlocksStream(client, config))

    # Add comments stream
    streams.append(CommentsStream(client, config))

    # Add database-specific streams if configured
    if config.database_ids:
        for db_id in config.database_ids:
            streams.append(
                DatabasePagesStream(client, config, db_id)
            )

    return streams


def get_stream_by_name(
    name: str,
    client: NotionClient,
    config: NotionConfig,
) -> Optional[BaseStream]:
    """
    Get a specific stream by name.

    Args:
        name: Stream name
        client: NotionClient instance
        config: NotionConfig instance

    Returns:
        Stream instance or None if not found
    """
    stream_map: Dict[str, type] = {
        "users": UsersStream,
        "databases": DatabasesStream,
        "pages": PagesStream,
        "blocks": BlocksStream,
        "comments": CommentsStream,
    }

    stream_class = stream_map.get(name)
    if stream_class:
        return stream_class(client, config)

    return None
