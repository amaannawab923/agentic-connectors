"""Database engine and session management for Labrynth."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

# Environment variable for custom database path
LABRYNTH_DB_PATH_ENV = "LABRYNTH_DB_PATH"


def get_db_path() -> Path:
    """Get database file path."""
    custom_path = os.environ.get(LABRYNTH_DB_PATH_ENV)
    if custom_path:
        return Path(custom_path)
    return Path.home() / ".labrynth" / "labrynth.db"


def get_database_url(db_path: Optional[Path] = None) -> str:
    """Get async SQLite URL."""
    path = db_path or get_db_path()
    return f"sqlite+aiosqlite:///{path}"


# Global engine and session maker (lazy initialized)
_engine = None
_session_maker = None


def get_engine(db_path: Optional[Path] = None):
    """Get or create database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(db_path),
            echo=False,
            future=True,
        )
    return _engine


def get_session_maker(db_path: Optional[Path] = None) -> async_sessionmaker[AsyncSession]:
    """Get session maker."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(db_path),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_maker


async def init_database(db_path: Optional[Path] = None) -> None:
    """Initialize database (create directory and tables)."""
    # Get path
    path = db_path or get_db_path()

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Import models to register them with SQLModel
    from labrynth.database import models  # noqa: F401

    # Create tables
    engine = get_engine(db_path)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session(db_path: Optional[Path] = None) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session as async context manager."""
    session_maker = get_session_maker(db_path)
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def reset_engine() -> None:
    """Reset global engine and session maker (for testing)."""
    global _engine, _session_maker
    _engine = None
    _session_maker = None
