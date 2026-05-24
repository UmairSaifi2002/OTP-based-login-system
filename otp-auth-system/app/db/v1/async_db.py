"""
Asynchronous Database Module

Handles NON-BLOCKING database operations using aiomysql driver.

USE THIS FOR:
- ALL API endpoint database operations
- Any query during request handling

HOW ASYNC WORKS:
1. Endpoint calls: await session.execute(query)
2. Query is sent to MySQL
3. The coroutine YIELDS control (pauses)
4. The event loop handles OTHER requests while waiting
5. MySQL responds → coroutine RESUMES
6. Results are returned

This allows ONE thread to handle THOUSANDS of concurrent requests.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)


from app.config.v1.settings import settings
from app.utils.v1.loggers import logger 


# ============================================
# ASYNCHRONOUS DATABASE URL
# ============================================
# Uses aiomysql driver - NON-BLOCKING
# Format: mysql+aiomysql://user:password@host:port/database

ASYNC_DATABASE_URL = settings.ASYNC_DATABASE_URL


# ============================================
# ASYNCHRONOUS ENGINE
# ============================================

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo = settings.DATABASE_ECHO,
    pool_size = settings.DATABASE_POOL_SIZE,
    pool_recycle = 3600,
    pool_pre_ping = True
)

# ============================================
# ASYNCHRONOUS SESSION FACTORY
# ============================================

"""
AsyncSessionLocal creates AsyncSession objects.

Key difference from sync:
- expire_on_commit=False: Don't expire objects after commit
  (In sync, objects auto-expire. In async, this doesn't work well.)
"""

AsyncSessionLocal = async_sessionmaker(
    bind = async_engine,
    autocommit = False,
    autoflush = False,
    expire_on_commit = False
)

# ============================================
# ASYNC SESSION DEPENDENCY (For GET requests)
# ============================================

async def get_async_session():
    """
    Provide an async database session for READ-ONLY endpoints.
    
    Lifecycle:
    1. Session is created (connection taken from pool)
    2. Session is yielded to the endpoint
    3. Endpoint uses session for queries
    4. After endpoint returns, session is closed
    5. Connection returns to the pool
    
    Used for: GET endpoints (no data modification)
    """
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


# ==================================================
# ASYNC SESSION WITH COMMIT (For POST/PUT/DELETE)
# ==================================================

async def get_async_session_with_commit():
    """
    Provide an async database session for MODIFICATION endpoints.
    
    Lifecycle:
    1. Session is created
    2. Session is yielded to the endpoint
    3. Endpoint modifies data (add, update, delete)
    4. If successful → changes are COMMITTED automatically
    5. If error → changes are ROLLED BACK automatically
    6. Session is closed
    
    Used for: POST, PUT, DELETE endpoints
    """
    session = AsyncSessionLocal()
    try: 
        yield session
        await session.commit()
        logger.debug("Changes Commit")
    except Exception:
        await session.rollback()
        logger.error("Changes Rolled back")
        raise
    finally:
        await session.close()










