"""
Synchronous Database Module

Handles BLOCKING database operations using pymysql driver.

USE THIS FOR:
- Creating tables (DDL operations are inherently synchronous)
- Database migrations
- Scripts and management commands

DO NOT USE FOR:
- API request handling (use async_db.py instead)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.v1.settings import settings
from app.db.v1 import Base
from app.utils.v1.loggers import logger


# ============================================
# SYNCHRONOUS DATABASE URL
# ============================================
# Uses pymysql driver - BLOCKING (each query freezes the thread)
# Format: mysql+pymysql://user:password@host:port/database

SYNC_DATABASE_URL = settings.SYNC_DATABASE_URL


# ============================================
# SYNCHRONOUS ENGINE
# ============================================

"""
The engine is a CONNECTION POOL manager.

Think of it like a car rental company:
- It maintains a fleet of connections (cars)
- When you need one, you take one from the pool
- When you're done, you return it
- No need to create/destroy connections constantly

Parameters:
- echo=True: Print every SQL query to console (great for learning!)
- pool_size: How many connections to keep ready
- pool_recycle: Close connections after N seconds (prevents stale connections)
- pool_pre_ping: Test connection before using it (catches dead connections)
"""

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo = settings.DATABASE_ECHO,            # Show SQL in Consol
    pool_size = settings.DATABASE_POOL_SIZE,  # Max Connections in Pool
    pool_recycle = 3600,                      # Recycle after 1 hour
    pool_pre_ping = True                      # Test before use
)


# ============================================
# SYNCHRONOUS SESSION FACTORY
# ============================================

"""
SessionLocal is a FACTORY that creates Session objects.

A Session is a "unit of work" - it tracks:
- What objects you've added
- What objects you've modified
- What objects you've deleted

When you call session.commit():
- All changes are sent to MySQL as a TRANSACTION
- If anything fails, everything is rolled back

Parameters:
- autocommit=False: We control when commits happen
- autoflush=False: We control when SQL is sent to MySQL
"""

SyncSessionLocal = sessionmaker(
    bind = sync_engine,
    autocommit = False,
    autoflush = False
)


# ============================================
# TABLE CREATION
# ============================================

def create_tables():
    """
    Create ALL database tables defined in our models.
    
    HOW IT WORKS:
    1. Import all model classes (they register with Base.metadata)
    2. Base.metadata.create_all() generates CREATE TABLE SQL
    3. Executes the SQL against MySQL
    
    SAFE TO CALL MULTIPLE TIMES:
    - Tables that already exist are SKIPPED
    - No data is lost
    - This is called on every server startup
    """
    # Import models so they register with Base.metadata
    # If imported at the top, might cause circular imports
    from app.models.v1 import db_models

    logger.info("📊 Creating database tables...")
    Base.metadata.create_all(bind = sync_engine)
    logger.info("✅ Database tables ready")


def drop_tables():
    """
    Drop ALL tables. DELETES ALL DATA.
    Only use during development.
    """
    from app.models import db_models

    logger.warning("⚠️  Dropping all tables!")
    Base.metadata.drop_all(bind = sync_engine)
     








