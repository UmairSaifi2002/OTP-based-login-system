# """
# Authentication Router

# Handles OTP-based signup and login endpoints.
# """

# from fastapi import APIRouter

# router = APIRouter(
#     prefix="/api/v1/auth",
#     tags=["Authentication"],
# )


# @router.post("/send-otp")
# async def send_otp():
#     """Send OTP to user's email or phone."""
#     return {"message": "OTP sent (endpoint coming in Phase 4)"}


# @router.post("/verify-otp")
# async def verify_otp():
#     """Verify OTP and return JWT token."""
#     return {"message": "OTP verified (endpoint coming in Phase 4)"}

"""
Authentication Router

Handles OTP-based signup and login endpoints.

Endpoints:
    POST /api/v1/auth/send-otp    - Request OTP (signup or login)
    POST /api/v1/auth/verify-otp  - Verify OTP and get JWT token
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.v1 import get_async_session_with_commit
from app.managers.v1.auth_manager import AuthManager
from app.models.v1.schemas import (
    SendOTPRequest,
    VerifyOTPRequest,
    TokenResponse,
    MessageResponse,
)
from app.utils.v1.loggers import logger

from sqlalchemy import select
from app.models.v1.db_models import User



router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

# --------------------------------------------------------------
# Signup endpoint: Request OTP for signup
# --------------------------------------------------------------

@router.post("/signup", response_model = MessageResponse)
async def signup(
    request: SendOTPRequest,
    session: AsyncSession = Depends(get_async_session_with_commit),
):
    """
    Signup - Create a new account and send OTP for verification.
    
    This endpoint ONLY works for NEW users.
    If the email already exists, returns an error.
    
    Flow:
    1. Check if email exists → If yes, reject (use /login instead)
    2. Generate OTP and send to email
    3. Return success message
    
    Example:
        POST /api/v1/auth/signup
        {"email": "newuser@gmail.com"}
    """
    logger.info(f"Signup Request for: {request.email}")
    try:
        # Check if user already exists
        if request.email:
            query = select(User).where(User.email == request.email)
            result = await session.execute(query)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise ValueError("Email already registered. Please use login to request OTP.")

        # If user doesn't exist, proceed to send OTP (which also creates the user)
        result = await AuthManager.send_otp(
            session=session,
            email=request.email,
            phone_number=request.phone_number,
        )

        return MessageResponse(
            message=f"Signup successfully OTP sent to {request.email} and {request.phone_number}",
            detail=f"Please verify your OTP within {result['expires_in_minutes']} minutes.",
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup Failed. Please try again.",
        )


# --------------------------------------------------------------
# Login endpoint: Request OTP for login
# --------------------------------------------------------------

@router.post("/login", response_model = MessageResponse)
async def login(
    request: SendOTPRequest,
    session: AsyncSession = Depends(get_async_session_with_commit)
):
    """
    Login - Send OTP to an existing user.
    
    This endpoint ONLY works for EXISTING users.
    If the email doesn't exist, returns an error.
    
    Flow:
    1. Check if email exists → If no, reject (use /signup instead)
    2. Generate OTP and send to email
    3. Return success message
    
    Example:
        POST /api/v1/auth/login
        {"email": "existinguser@gmail.com"}
    """

    logger.info(f"Login Request for: {request.email}")
    
    try: 
        # Check if user exists
        if request.email:
            query = select(User).where(User.email == request.email)
            result = await session.execute(query)
            existing_user = result.scalar_one_or_none()

            if not existing_user:
                logger.warning(f"Login attempt with non-existent email: {request.email}")
                raise ValueError("Email not found. Please use /signup to create an account.")
            
        # Now using the same send_otp logic to generate OTP and update user record
        result = await AuthManager.send_otp(
            session = session,
            email = request.email,
            phone_number = request.phone_number,
        )

        return MessageResponse(
            message = f"Login OTP sent to {request.email} and {request.phone_number}",
            detail = f"Please verify your OTP within {result['expires_in_minutes']} minutes.",
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = str(e),
        )
    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "Login Failed. Please try again.",
        )




# @router.post("/send-otp", response_model=MessageResponse)
# async def send_otp(
#     request: SendOTPRequest,
#     session: AsyncSession = Depends(get_async_session_with_commit),
# ):
#     """
#     Request an OTP for signup or login.
    
#     If the user doesn't exist, a new account is created (signup).
#     If the user exists, OTP is sent for login.
    
#     Send either email OR phone_number (at least one required).
    
#     Args:
#         request: Contains email and/or phone_number
#         session: Database session
    
#     Returns:
#         MessageResponse with confirmation
    
#     Example:
#         POST /api/v1/auth/send-otp
#         {"email": "user@example.com"}
#     """
#     logger.info(f"OTP requested for: {request.email or request.phone_number}")
    
#     try:
#         result = await AuthManager.send_otp(
#             session=session,
#             email=request.email,
#             phone_number=request.phone_number,
#         )
#         return MessageResponse(
#             message=result["message"],
#             detail=f"OTP expires in {result['expires_in_minutes']} minutes",
#         )
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e),
#         )
#     except Exception as e:
#         logger.error(f"Failed to send OTP: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to send OTP. Please try again.",
#         )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    request: VerifyOTPRequest,
    session: AsyncSession = Depends(get_async_session_with_commit),
):
    """
    Verify OTP and receive JWT access token.
    
    Args:
        request: Contains email/phone and the 6-digit OTP
        session: Database session
    
    Returns:
        TokenResponse with access_token and user data
    
    Example:
        POST /api/v1/auth/verify-otp
        {"email": "user@example.com", "otp": "123456"}
    """
    logger.info(f"OTP verification for: {request.email or request.phone_number}")
    
    try:
        token_response = await AuthManager.verify_otp(
            session=session,
            otp=request.otp,
            email=request.email,
            phone_number=request.phone_number,
        )
        return token_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to verify OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP. Please try again.",
        )