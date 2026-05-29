"""
OTP Service

Handles OTP generation and delivery (email/SMS).

In production, you would integrate with:
- Email: SendGrid, AWS SES, SMTP
- SMS: Twilio, AWS SNS, MSG91

For now, we generate OTP and log it (simulating sending).
"""

import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.v1.settings import settings
from app.utils.v1.loggers import logger
# import httpx
import secrets # this is for generating a secure random otp
from app.services.v1.twilio_service import send_otp_sms as send_twilio


def generate_secure_otp(length: int = 6) -> str:
    """
    Generates a cryptographically secure numeric OTP.
    
    Why secrets and not random?
    - secrets uses the OS's entropy pool (truly random noise from hardware)
    - random uses a deterministic algorithm (Mersenne Twister)
    - Given enough OTPs from random, an attacker can predict the next one
    
    Why return a string?
    - OTPs are identifiers, not numbers to do math with
    - Leading zeros matter! "012345" as int becomes 12345 (5 digits)
    - String comparison avoids integer overflow edge cases
    - Redis stores everything as strings anyway
    """
    if length <= 0:
        raise ValueError("OTP length must be positive and can't be zero, my friend!")
    
    # secrets.randbelow(n) returns a random integer in [0, n)
    # For 6-digit OTP: 100000 to 999999
    lower_bound = 10 ** (length -1) # e.g., 100000 for length=6
    upper_bound = (10 ** length) -1 # e.g., 999999 for length=6

    otp = secrets.randbelow(upper_bound - lower_bound +1) + lower_bound
    return str(otp)


def generate_otp() -> str:
    """
    Generate a random 6-digit OTP.
    
    Returns:
        str: 6-digit OTP code
    
    HOW IT WORKS:
    random.randint(100000, 999999) generates a number between 100000 and 999999.
    This guarantees a 6-digit number.
    """
    otp = str(random.randint(100000, 999999))
    logger.debug(f"Generated OTP: {otp}")
    return otp


async def send_otp_email(email: str, otp: str) -> bool:
    """
    Send OTP to user's email address.
    """
    try:
        # Create email message
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = email
        msg["Subject"] = f"Your OTP Code - {settings.APP_NAME}"
        
        body = f"""
        Hello,
        
        Your OTP code is: {otp}
        
        This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.
        
        If you did not request this code, please ignore this email.
        
        Thank you,
        {settings.APP_NAME}
        """
        
        msg.attach(MIMEText(body, "plain"))
        
        # Connect and send
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            logger.info("✅ Login Successfully")
            server.sendmail(settings.SMTP_USERNAME, email, msg.as_string())
            logger.info("✅ Email Sent")
        
        logger.info(f"✅ Email sent successfully to {email}")
        return True
        
    except Exception as e:
        # Log the ACTUAL error
        logger.error(f"❌ Failed to send email: {type(e).__name__}: {str(e)}")
        logger.info(f"📧 [DEV MODE] OTP for {email}: {otp}")
        return True  # Return True so the API flow continues


async def send_otp_sms(phone_number: str, otp: str) -> bool:
    """
    Send OTP via SMS using Twilio.
    Falls back to console logging if Twilio is not configured.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("⚠️  Twilio not configured.")
        logger.info(f"📱 [DEV MODE] OTP for {phone_number}: {otp}")
        return True
    
    try:
        await send_twilio(phone_number, otp)
        return True
    except Exception as e:
        logger.error(f"❌ SMS failed: {str(e)}")
        logger.info(f"📱 [FALLBACK] OTP for {phone_number}: {otp}")
        return True

# async def send_otp_whatsapp(phone_number: str, otp: str) -> bool:
#     """
#     Send OTP to user's WhatsApp using Whapi.Cloud.
    
#     Falls back to console logging if WHAPI_TOKEN is not configured.
    
#     Args:
#         phone_number: Phone number with country code (e.g., 919876543210)
#         otp: The OTP code to send
    
#     Returns:
#         bool: True if sent successfully
#     """
#     # Check if Whapi is configured
#     if not settings.WHAPI_TOKEN:
#         logger.warning("⚠️  Whapi.Cloud not configured. Logging OTP instead.")
#         logger.info(f"📱 [DEV MODE] WhatsApp OTP for {phone_number}: {otp}")
#         return True  # Return True so the API flow continues
    
#     try:
#         # Whapi expects Chat ID format: {phone}@s.whatsapp.net
#         # Remove any '+' or spaces from the phone number
#         clean_phone = phone_number.replace("+", "").replace(" ", "").replace("-", "")
#         chat_id = f"{clean_phone}@s.whatsapp.net"
        
#         # Whapi REST API endpoint for sending text messages
#         url = "https://gate.whapi.cloud/messages/text"
        
#         # Authorization header with Bearer token
#         headers = {
#             "Authorization": f"Bearer {settings.WHAPI_TOKEN}",
#             "Content-Type": "application/json",
#         }
        
#         # Message body - uses WhatsApp markup for formatting
#         payload = {
#             "to": chat_id,
#             "body": f"*{settings.APP_NAME}*\n\n"
#                     f"Your OTP code is: *{otp}*\n\n"
#                     f"This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.\n\n"
#                     f"If you did not request this code, please ignore this message.",
#         }

#         # Send the request
#         async with httpx.AsyncClient() as client:
#             response = await client.post(url, json=payload, headers=headers)
            
#             if response.status_code == 200:
#                 logger.info(f"📱 WhatsApp OTP sent to {phone_number}")
#                 return True
#             else:
#                 logger.error(f"❌ Whapi error: {response.status_code} - {response.text}")
#                 logger.info(f"📱 [FALLBACK] OTP for {phone_number}: {otp}")
#                 return True
                
#     except Exception as e:
#         logger.error(f"❌ WhatsApp send failed: {type(e).__name__}: {str(e)}")
#         logger.info(f"📱 [FALLBACK] OTP for {phone_number}: {otp}")
#         return True








