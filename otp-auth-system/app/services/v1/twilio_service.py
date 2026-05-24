"""
Twilio SMS Service

Handles sending OTP via SMS using Twilio.
Uses a singleton client pattern for efficiency.
Runs blocking Twilio calls in a thread pool to avoid blocking async.
"""

import asyncio
from fastapi import HTTPException, status
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.config.v1.settings import settings
from app.utils.v1.loggers import logger

# Singleton client - created once, reused for all calls
_client: Client | None = None


def _get_client() -> Client:
    """
    Get or create the Twilio client.
    
    Uses singleton pattern:
    - First call: Creates the client
    - Subsequent calls: Returns the same client
    """
    global _client
    
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("⚠️  Twilio credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twilio credentials are not configured.",
        )
    
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        logger.info("✅ Twilio client initialized")
    
    return _client


async def send_otp_sms(phone_number: str, otp: str) -> None:
    """
    Send OTP via SMS using Twilio.
    
    Args:
        phone_number: Phone number in E.164 format (+919876543210)
        otp: The 6-digit OTP code
    
    Raises:
        HTTPException: If SMS fails to send
    """
    try:
        client = _get_client()
        
        # Twilio's API is synchronous (blocking)
        # run_in_executor runs it in a separate thread
        # so it doesn't block the async event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                body=(
                    f"[{settings.APP_NAME}] Your OTP is {otp}. "
                    f"Valid for {settings.OTP_TTL_SECONDS // 60} minutes. "
                    f"Do not share with anyone."
                ),
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number,
            ),
        )
        
        logger.info(f"📱 SMS sent to {phone_number}")
        
    except HTTPException:
        raise
    except TwilioRestException as e:
        logger.error(f"❌ Twilio error: {e.msg}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SMS delivery failed: {e.msg}",
        )
    except Exception as e:
        logger.error(f"❌ SMS error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected SMS error: {str(e)}",
        )