"""
Database Package

The Base class is the foundation for ALL database models.
Every table class inherits from Base.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Re-export sync engine & table creation
from app.db.sync import sync_engine, create_tables, drop_tables, SyncSessionLocal

# Re-export async engine & sessions
from app.db.async_db import (
    async_engine,
    AsyncSessionLocal,
    get_async_session,
    get_async_session_with_commit,
)

__all__ = [
    "Base",
    "sync_engine",
    "create_tables",
    "drop_tables",
    "SyncSessionLocal",
    "async_engine",
    "AsyncSessionLocal",
    "get_async_session",
    "get_async_session_with_commit",
]