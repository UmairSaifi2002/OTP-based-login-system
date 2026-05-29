"""
Redis Database Module for FastAPI E-Commerce Project.

Provides:
- Redis connection pool (reuses connections, doesn't create new ones per request)
- Async Redis client (for FastAPI async endpoints)
- Sync Redis client (for scripts, tests, and synchronous code)
- FastAPI dependency injection functions

The Professor's Note:
Redis connections are precious. Don't open and close them for every request.
Use a connection pool. The pool keeps connections alive and reuses them.
This is the difference between a bicycle (one connection per request) 
and a bullet train (pool of reusable connections).

The Slang:
Think of the connection pool as a fleet of taxis waiting at the airport.
When a passenger (request) arrives, they don't need to wait for a new taxi 
to be built. They just grab one from the queue. When the ride is done, 
the taxi goes back to the queue for the next passenger.
"""

import redis
import redis.asyncio as aioredis
from typing import Optional
from app.config.v1.settings import settings
from app.utils.v1.loggers import logger


# ═══════════════════════════════════════════════════════════════
# SYNCHRONOUS REDIS CLIENT (for scripts, tests, table creation)
# ═══════════════════════════════════════════════════════════════

# Create a connection pool — this is what makes it fast
sync_pool : Optional[redis.ConnectionPool] = None

def get_sync_redis() -> redis.Redis:
    """
    Returns a synchronous Redis client using the connection pool.
    
    Use this in:
    - Python scripts
    - Testing code
    - Synchronous functions (not FastAPI endpoints)
    - Startup/shutdown events
    
    Example:
        r = get_sync_redis()
        r.set("key", "value", ex=300)
    """
    global sync_pool
    if sync_pool is None:
        sync_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True # 👈 Automatically converts bytes to strings
        )

    return redis.Redis(connection_pool=sync_pool)

# ═══════════════════════════════════════════════════════════════
# ASYNCHRONOUS REDIS CLIENT (for FastAPI async endpoints)
# ═══════════════════════════════════════════════════════════════

# Create an async connection pool
async_pool : Optional[aioredis.ConnectionPool] = None

async def get_async_redis() -> aioredis.Redis:
    """
    Returns an async Redis client. Use this as a FastAPI dependency.
    
    The Professor's Warning:
    This creates a NEW connection from the pool each time.
    For FastAPI dependency injection, use get_redis() below instead.
    This function is for one-off uses where you need direct control.
    """
    global async_pool
    if async_pool is None:
        async_pool = aioredis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True
        )
    return aioredis.Redis(connection_pool = async_pool)


# ═══════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCY INJECTION (The main way you'll use Redis)
# ═══════════════════════════════════════════════════════════════
async def get_redis():
    """
    FastAPI dependency that provides a Redis connection.
    
    How to use in your routers:
    
        @router.get("/some-endpoint")
        async def some_endpoint(redis: aioredis.Redis = Depends(get_redis)):
            value = await redis.get("some_key")
            return {"value": value}
    
    The Magic of Dependency Injection:
    1. FastAPI sees 'Depends(get_redis)'
    2. FastAPI calls get_redis() before your endpoint runs
    3. get_redis() yields a Redis connection from the pool
    4. Your endpoint uses the connection
    5. When your endpoint finishes, the connection returns to the pool
    
    This means you never need to manually open/close connections.
    FastAPI handles the entire lifecycle.
    """
    redis_client = await get_async_redis()
    try:
        yield redis_client
    finally:
        # Connection returns to the pool automatically
        # when the generator is cleaned up
        pass  # The pool handles connection lifecycle


# ═══════════════════════════════════════════════════════════════
# CONNECTION TESTING UTILITY
# ═══════════════════════════════════════════════════════════════

async def test_redis_connection() -> bool:
    """
    Tests that Redis is reachable and responding.
    
    Returns True if Redis says 'PONG', False otherwise.
    
    Call this during startup to verify Redis is online.
    """
    try: 
        r = await get_async_redis()
        result = await r.ping()
        return result is True
    except Exception as e:
        print(f"❌ Redis sync connection failed: {e}")
        return False

def test_sync_redis_connection() -> bool:
    """Synchronous version of the Redis connection test."""
    try:
        r = get_sync_redis()
        result = r.ping()
        return result is True
    except Exception as e:
        print(f"❌ Redis sync connection failed: {e}")
        return False

















