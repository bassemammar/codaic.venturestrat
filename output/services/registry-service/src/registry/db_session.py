"""Async database session management for registry service.

This module provides async SQLAlchemy session management with proper
connection pooling and transaction handling.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """Manages async database sessions and connection pooling."""

    def __init__(self, database_url: str):
        """Initialize the session manager with a database URL.

        Args:
            database_url: PostgreSQL connection URL (will be converted to async)
        """
        # Extract search_path from options if present
        self.search_path = "public"
        if "?options=" in database_url:
            # Extract search_path from options
            import re

            match = re.search(r"search_path=([^&\s]+)", database_url)
            if match:
                self.search_path = match.group(1)
            # Remove options parameter for asyncpg compatibility
            database_url = database_url.split("?")[0]

        # Convert postgresql:// to postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must start with postgresql:// or postgresql+asyncpg://")

        self.database_url = database_url
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def init(self) -> None:
        """Initialize the database engine and session factory."""
        if self._engine is not None:
            logger.warning("Database already initialized")
            return

        # Create async engine with proper pool settings
        self._engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,  # Test connections before using
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,  # Recycle connections after 1 hour
            connect_args={"server_settings": {"search_path": self.search_path}},
        )

        # Create session factory
        self._sessionmaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flush control
            autocommit=False,  # Explicit transaction control
        )

        logger.info("Database session manager initialized", extra={"url": self.database_url})

    async def close(self) -> None:
        """Close the database engine and all connections."""
        if self._engine is None:
            return

        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None
        logger.info("Database session manager closed")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Create a new async database session context.

        Yields:
            AsyncSession: Database session with automatic transaction management

        Example:
            async with db_manager.session() as session:
                result = await session.execute(select(Model))
                await session.commit()
        """
        if self._sessionmaker is None:
            raise RuntimeError("DatabaseSessionManager not initialized. Call init() first.")

        session = self._sessionmaker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Global session manager instance
_session_manager: DatabaseSessionManager | None = None


def init_db(database_url: str) -> None:
    """Initialize the global database session manager.

    Args:
        database_url: PostgreSQL connection URL
    """
    global _session_manager
    if _session_manager is not None:
        logger.warning("Database already initialized globally")
        return

    _session_manager = DatabaseSessionManager(database_url)
    _session_manager.init()
    logger.info("Global database session manager initialized")


async def close_db() -> None:
    """Close the global database session manager."""
    global _session_manager
    if _session_manager is not None:
        await _session_manager.close()
        _session_manager = None
        logger.info("Global database session manager closed")


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Get a database session from the global session manager.

    Yields:
        AsyncSession: Database session

    Raises:
        RuntimeError: If database not initialized
    """
    if _session_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_manager.session() as session:
        yield session
