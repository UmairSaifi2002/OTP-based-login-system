"""
Authentication Manager

Contains ALL business logic for OTP-based authentication.
The router calls these methods - it never touches the database directly.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import User
from app.models.schemas import TokenResponse, UserResponse
from app.services.otp_services import generate_otp, generate_secure_otp, send_otp_email, send_otp_sms
from app.utils.security import create_access_token
from app.config.v1.settings import settings
from app.utils.loggers import logger


class AuthManager:
    """
    Manager for authentication operations.
    
    All methods are @staticmethod and async.
    They receive a database session as the first parameter.
    """
    
    @staticmethod
    async def send_otp(
        session: AsyncSession,
        email: str | None = None,
        phone_number: str | None = None,
    ) -> dict:
        """
        Generate and send OTP to user.
        
        If user doesn't exist, creates a new user (signup).
        If user exists, updates existing user (login).
        
        Args:
            session: Database session
            email: User's email (optional)
            phone_number: User's phone (optional)
        
        Returns:
            dict with success message
        
        Raises:
            ValueError: If neither email nor phone provided
        """
        # Validate: at least one identifier required
        if not email and not phone_number:
            raise ValueError("Either email or phone_number is required")
        
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
                user = User(email=email, phone_number=phone_number) # Here we are storing an email in the database
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
        
        # otp_code = generate_otp()
        otp_code = generate_secure_otp(settings.OTP_LENGTH)
        otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        
        # Store OTP in user record
        user.otp_code = otp_code
        user.otp_expires_at = otp_expiry
        
        await session.commit()
        await session.refresh(user)
        
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
            await send_otp_sms(phone_number, otp_code)
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
    
    # ============================================
    # VALIDATE OTP
    # ============================================
    
        # Check if OTP exists
        if not user.otp_code:
            raise ValueError("No OTP found. Please request a new OTP.")
    
        # Check if OTP matches
        if user.otp_code != otp:
            raise ValueError("Invalid OTP. Please check and try again.")
    
        # Check if OTP has expired
        if user.otp_expires_at:
            # ✅ FIX: Make the database datetime timezone-aware before comparing
            expiry = user.otp_expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expiry:
                # Clear expired OTP so user can request a new one
                user.otp_code = None
                user.otp_expires_at = None
                await session.commit()
                raise ValueError("OTP has expired. Please request a new OTP.")
    
    # ============================================
    # CLEAR OTP (one-time use)
    # ============================================
        user.otp_code = None
        user.otp_expires_at = None
        await session.commit()
        await session.refresh(user)
    
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



