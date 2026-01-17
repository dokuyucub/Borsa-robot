"""
Database connection management for BDK Trading Bot.

This module provides async database connection pooling and session management
using SQLAlchemy with asyncpg for PostgreSQL.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import get_config
from src.core.logger import get_logger

from .models import Base

logger = get_logger("bdk.database")


class DatabaseManager:
    """
    Manages async database connections and sessions.

    Usage:
        >>> db = DatabaseManager()
        >>> await db.initialize()
        >>>
        >>> async with db.session() as session:
        ...     result = await session.execute(query)
        ...     await session.commit()
        >>>
        >>> await db.close()
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize DatabaseManager.

        Args:
            database_url: Optional database URL. If None, loads from config.
        """
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        self.logger = get_logger("bdk.database")

    async def initialize(self) -> None:
        """
        Initialize database connection and create tables.

        This method:
        - Gets database URL from config if not provided
        - Converts postgresql:// to postgresql+asyncpg://
        - Creates async engine with connection pooling
        - Creates session factory
        - Creates all database tables
        """
        # Get database URL from config if not provided
        if self.database_url is None:
            config = get_config()
            self.database_url = config.database_url

        if not self.database_url:
            raise ValueError(
                "Database URL not configured. Please set DATABASE_URL environment variable."
            )

        # Convert postgresql:// to postgresql+asyncpg://
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "Database URL must use PostgreSQL. "
                f"Got: {self.database_url.split('://')[0]}"
            )

        # Get pool settings from config
        config = get_config()
        pool_size = config.database.pool_size
        echo = config.database.echo

        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=pool_size * 2,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.logger.info(
            "Database initialized",
            pool_size=pool_size,
            echo=echo,
        )

    async def close(self) -> None:
        """
        Close database connections and dispose engine.
        """
        if self.engine:
            await self.engine.dispose()
            self.logger.info("Database connections closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async session context manager.

        Usage:
            >>> async with db.session() as session:
            ...     result = await session.execute(query)
            ...     await session.commit()

        Yields:
            AsyncSession: Database session

        Raises:
            RuntimeError: If database not initialized
        """
        if self.session_factory is None:
            raise RuntimeError(
                "Database not initialized. Call initialize() first."
            )

        session: AsyncSession = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            self.logger.error(
                "Database session error",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """
        Check if database is accessible.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            async with self.session() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            self.logger.debug("Database health check passed")
            return True
        except Exception as e:
            self.logger.error(
                "Database health check failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False


# ==================== Singleton Instance ====================

_db_manager: Optional[DatabaseManager] = None


async def get_database() -> DatabaseManager:
    """
    Get or create database manager singleton.

    Returns:
        DatabaseManager: Initialized database manager

    Example:
        >>> db = await get_database()
        >>> async with db.session() as session:
        ...     # Use session
        ...     pass
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    return _db_manager


async def close_database() -> None:
    """
    Close database connection and cleanup singleton.

    Example:
        >>> await close_database()
    """
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None
