"""
Authentication Manager

Contains ALL business logic for OTP-based authentication.
The router calls these methods - it never touches the database directly.
"""

from datetime import datetime, timedelta, timezone
import email

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.v1.db_models import User
from app.models.v1.schemas import TokenResponse, UserResponse
from app.services.v1.otp_services import generate_otp, generate_secure_otp, send_otp_email, send_otp_sms
from app.utils.v1.security import create_access_token
from app.config.v1.settings import settings
from app.utils.v1.loggers import logger
from app.utils.v1.validators import validate_request_inputs
from app.db.v1.redis_db import get_async_redis
import redis.asyncio as aioredis



class AuthManager:
    """
    Manager for authentication operations.
    
    All methods are @staticmethod and async.
    They receive a database session as the first parameter.
    """

    # ── RATE LIMITING HELPERS ─────────────────────────────
    @staticmethod
    def _rate_limit_key(identifier: str) -> str:
        """Create a Redis key for the failed attempt counter."""
        return f"otp_attempts: {identifier}"
    
    @staticmethod
    async def _check_rate_limit(redis: aioredis.Redis, identifier: str) -> None:
        """
        Raise ValueError if the user has exceeded max attempts.
        Otherwise, do nothing.
        """
        key = AuthManager._rate_limit_key(identifier)
        attempt_str = await redis.get(key)
        attempts = int(attempt_str) if attempt_str else 0
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            raise ValueError("Too many failed OTP attempts. Please request a new OTP.")
        
    @staticmethod
    async def _increment_failed_attempts(redis: aioredis.Redis, identifier: str) -> None:
        """Record a failed OTP attempt in Redis with a 5-minute expiry."""
        key = AuthManager._rate_limit_key(identifier)
        # INCR is atomic – no race conditions
        await redis.incr(key)
        # Ensure the key expires with the OTP (5 minutes)
        await redis.expire(key, settings.OTP_EXPIRY_MINUTES * 60)

    @staticmethod
    async def _reset_attempts(redis: aioredis.Redis, identifier: str) -> None:
        """Reset the attempt counter (called when a new OTP is sent)."""
        key = AuthManager._rate_limit_key(identifier)
        await redis.delete(key)

    # -------------------------------------------------------

    # ==========================================================
    # OTP AUTHENTICATION METHODS by Redis

    @staticmethod
    def _otp_key(identifier: str) -> str:
        """Create a Redis key for storing OTP data."""
        return f"otp :{identifier}"
    
    @staticmethod
    async def _store_otp_in_redis(redis: aioredis.Redis, identifier: str, otp_code: str, ttl_minutes: int) -> None:
        """Store OTP in Redis with automatic expiry."""
        key = AuthManager._otp_key(identifier)
        await redis.set(key, otp_code, ex=ttl_minutes * 60)

    @staticmethod
    async def _get_otp_from_redis(redis: aioredis.Redis, identifier: str) -> Optional[str]:
        """Retrieve OTP from Redis. Returns None if expired or not found."""
        key = AuthManager._otp_key(identifier)
        return await redis.get(key)
    
    @staticmethod
    async def _delete_otp_from_redis(redis: aioredis.Redis, identifier: str) -> None:
        """Delete OTP from Redis after successful verification."""
        key = AuthManager._otp_key(identifier)
        await redis.delete(key)


    # ----------------------------------------------------------
    
    @staticmethod
    async def send_otp(
        session: AsyncSession,
        redis: aioredis.Redis,
        email: str | None = None,
        country_code: str | None = None,
        phone_number: str | None = None,
    ) -> dict:
        """
        Generate and send OTP to user.
        
        If user doesn't exist, creates a new user (signup).
        If user exists, updates existing user (login).
        
        Args:
            session: Database session
            email: User's email (optional)
            country_code: Country code with + prefix (Optional)
            phone_number: User's phone (optional)
        
        Returns:
            dict with success message
        
        Raises:
            ValueError: If neither email nor phone provided
        """
        # Validate: at least one identifier required
        # if not email and not phone_number:
        #     raise ValueError("Either email or phone_number is required")

        # Comprehensive validation
        validate_request_inputs(email=email, country_code=country_code, phone_number=phone_number)
        
        # ============================================
        # FIND OR CREATE USER
        # ============================================
        
        user = None
        
        # Try to find user by email
        if email: 
            query = select(User).where(User.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                logger.info(f"Existing user found: {email}")
                # ← THIS IS LOGIN: User already exists
            else:
                # Signup Funcctionality
                # Create new user
                user = User(email=email, country_code=country_code, phone_number=phone_number) # Here we are storing an email in the database
                session.add(user)
                await session.flush()  # Get the ID without committing
                logger.info(f"New user created: {email}")
                # ← THIS IS SIGNUP: User didn't exist, so we created them
        
        # Try to find user by phone (if not found by email)
        # if not user and phone_number:
        #     query = select(User).where(User.phone_number == phone_number)
        #     result = await session.execute(query)
        #     user = result.scalar_one_or_none()
            
        #     if user:
        #         logger.info(f"Existing user found: {phone_number}")
        #     else:
        #         user = User(phone_number=phone_number)
        #         session.add(user)
        #         await session.flush()
        #         logger.info(f"New user created: {phone_number}")
        
        # ============================================
        # GENERATE AND STORE OTP
        # ============================================
        
        # old way to geenerate OTP
        # # otp_code = generate_otp()
        # otp_code = generate_secure_otp(settings.OTP_LENGTH)
        # otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        # Generate OTP and store in Redis
        # Generate OTP
        otp_code = generate_secure_otp(settings.OTP_LENGTH)

        # ── NEW: Store OTP in Redis ──────────────────────
        identifier = email or phone_number
        await AuthManager._store_otp_in_redis(
            redis,
            identifier,
            otp_code,
            settings.OTP_EXPIRY_MINUTES
        )

        # Redis
        await AuthManager._reset_attempts(redis, email or phone_number)  # Reset failed attempts when a new OTP is sent
        
        # Store OTP in user record
        # user.otp_code = otp_code
        # user.otp_expires_at = otp_expiry
        
        # await session.commit()
        # await session.refresh(user)
        
        # ============================================
        # SEND OTP
        # ============================================
        
        if email:
            await send_otp_email(email, otp_code)
            # return {
            #     "message": f"OTP sent to {email}",
            #     "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
            # }
        
        if phone_number:
            full_number = f"{country_code}{phone_number}"   # ← The combination!
            await send_otp_sms(full_number, otp_code)
            # return {
            #     "message": f"OTP sent to {phone_number} via SMS",
            #     "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
            # }
        
        return {
            "message": f"OTP sent to {email or phone_number}",
            "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
        }
    
    @staticmethod
    async def verify_otp(
        session: AsyncSession,
        redis: aioredis.Redis,
        otp: str,
        email: str | None = None,
        phone_number: str | None = None,
    ) -> TokenResponse:
        """Verify OTP and return JWT token."""
    
    # ============================================
    # FIND USER
    # ============================================
        user = None
    
        if email:
            query = select(User).where(User.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
    
        # if not user and phone_number:
        #     query = select(User).where(User.phone_number == phone_number)
        #     result = await session.execute(query)
        #     user = result.scalar_one_or_none()
    
        if not user:
            raise ValueError("User not found. Please request OTP first.")
        
        identifier = email or phone_number  # For rate limiting

        # ── GUARD 1: RATE LIMIT ──────────────────────────
        await AuthManager._check_rate_limit(redis, identifier)

        # if not user.otp_code:
        #     raise ValueError("No OTP found. Please request a new OTP.")

        # if user.otp_code != otp:
        #     # ── GUARD 2: INCREMENT FAILURE ──────────────
        #     await AuthManager._increment_failed_attempts(redis, identifier)
        #     raise ValueError("Invalid OTP. Please check and try again.")
    
    # ============================================
    # VALIDATE OTP
    # ============================================
    
        # Check if OTP exists
        # if not user.otp_code:
        #     raise ValueError("No OTP found. Please request a new OTP.")
    
        # # Check if OTP matches
        # if user.otp_code != otp:
        #     raise ValueError("Invalid OTP. Please check and try again.")
    
        # # Check if OTP has expired
        # if user.otp_expires_at:
        #     # ✅ FIX: Make the database datetime timezone-aware before comparing
        #     expiry = user.otp_expires_at.replace(tzinfo=timezone.utc)
        #     if datetime.now(timezone.utc) > expiry:
        #         # Clear expired OTP so user can request a new one
        #         user.otp_code = None
        #         user.otp_expires_at = None
        #         await session.commit()
        #         raise ValueError("OTP has expired. Please request a new OTP.")

        # ── RETRIEVE OTP FROM REDIS ───────────────────
        stored_otp = await AuthManager._get_otp_from_redis(redis, identifier)
        if not stored_otp:
            raise ValueError("No OTP found or OTP has expired. Please request a new OTP.")

        if stored_otp != otp:
            await AuthManager._increment_failed_attempts(redis, identifier)
            raise ValueError("Invalid OTP. Please check and try again.")
    
    # ============================================
    # CLEAR OTP (one-time use)
    # ============================================
        # user.otp_code = None
        # user.otp_expires_at = None
        # await AuthManager._reset_attempts(redis, identifier)  # Reset failed attempts on successful verification
        # await session.commit()
        # await session.refresh(user)

        # ── SUCCESS: DELETE OTP, RESET ATTEMPTS, ISSUE JWT ─
        await AuthManager._delete_otp_from_redis(redis, identifier)
        await AuthManager._reset_attempts(redis, identifier)
     
    # ============================================
    # GENERATE JWT TOKEN
    # ============================================
    # ------------- # This is the ONLY line that calls security.py right now: ---------------------------------
        access_token = create_access_token(data={"sub": str(user.id)})
    
        logger.info(f"User authenticated: {user.email or user.phone_number}")
    
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )   



