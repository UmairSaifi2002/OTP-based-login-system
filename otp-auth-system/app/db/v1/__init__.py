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
from app.db.v1.sync import sync_engine, create_tables, drop_tables, SyncSessionLocal

# Re-export async engine & sessions
from app.db.v1.async_db import (
    async_engine,
    AsyncSessionLocal,
    get_async_session,
    get_async_session_with_commit,
)

# ── NEW: Redis exports ───────────────────────────────────────
from app.db.v1.redis_db import (
    get_redis,                    # FastAPI dependency for async endpoints
    get_sync_redis,               # For synchronous code
    get_async_redis,              # For direct async access
    test_redis_connection,        # Startup health check
    test_sync_redis_connection,   # Script health check
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
    "get_redis",
    "get_sync_redis",
    "get_async_redis",
    "test_redis_connection",
    "test_sync_redis_connection"
]