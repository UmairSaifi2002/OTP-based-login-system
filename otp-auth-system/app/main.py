"""
OTP Login System - Main Application Entry Point

This file:
1. Defines the lifespan (startup + shutdown)
2. Creates the FastAPI application
3. Configures middleware (CORS, timing)
4. Registers routers
5. Defines root and health endpoints

To run:
    poetry run uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.v1.settings import settings
from app.utils.v1.loggers import logger
# from app.db import create_tables, sync_engine, async_engine
from app.db.v1.sync import sync_engine, create_tables
from app.db.v1.async_db import async_engine
from app.db.v1 import test_redis_connection


# ============================================
# LIFESPAN (Startup & Shutdown)
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Everything BEFORE yield runs at SERVER STARTUP.
    Everything AFTER yield runs at SERVER SHUTDOWN.
    
    STARTUP:
    - Log application information
    - Create database tables
    
    SHUTDOWN:
    - Close database connections
    """
    
    # ═══════════════════ STARTUP ═══════════════════
    
    logger.info("=" * 60)
    logger.info(f"🚀 STARTING: {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT_TYPE}")
    logger.info(f"📊 Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
    logger.info("=" * 60)
    
    # Create all database tables
    # This is safe to call multiple times - existing tables are skipped
    create_tables()
    logger.info("✅ Database tables ready")
    logger.info(f"📡 API docs: http://127.0.0.1:8000/docs")

    # ── NEW: Redis Health Check ───────────────────────────
    print("🔍 Checking Redis connection...")
    redis_ok = await test_redis_connection()
    if redis_ok:
        print("✅ Redis is connected and responding!")
    else:
        print("⚠️  WARNING: Redis is not available!")
        print("   OTP verification and rate limiting will not work.")
        print("   Make sure Redis server is running on", 
              f"{settings.REDIS_HOST}:{settings.REDIS_PORT}")
    
    # ──────────────────────────────────────────────────────
    
    yield  # ← Server runs here
    
    # ═══════════════════ SHUTDOWN ═══════════════════
    
    logger.info("🛑 Shutting down server...")
    
    # Close all database connections
    sync_engine.dispose()
    await async_engine.dispose()
    
    logger.info("✅ Server shutdown complete")


# ============================================
# APPLICATION FACTORY
# ============================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This pattern (application factory) allows:
    - Multiple app instances for testing
    - Clean configuration before the app runs
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
        ## OTP-Based Login System
        
        A secure authentication API using OTP (One-Time Password).
        
        ### Features
        - **Signup**: Register with email, receive OTP
        - **Login**: Request OTP, verify and receive JWT token
        
        ### Flow
        1. Send your email or phone to `/api/v1/auth/send-otp`
        2. Receive a 6-digit OTP
        3. Verify with `/api/v1/auth/verify-otp`
        4. Get a JWT access token for authenticated requests
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,  # ← Attach startup/shutdown handler
    )
    
    # ============================================
    # CORS MIDDLEWARE
    # ============================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGIN_LIST,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    
    
    # ============================================
    # REGISTER ROUTERS
    # ============================================
    from app.routers.v1 import auth
    app.include_router(auth.router)
    
    return app


# ============================================
# CREATE THE APPLICATION INSTANCE
# ============================================

app = create_app()


# ============================================
# ROOT ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint - API welcome message."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT_TYPE,
        "docs": "/docs",
        "endpoints": {
            "send_otp": "/api/v1/auth/send-otp",
            "verify_otp": "/api/v1/auth/verify-otp",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
    }