"""
Security Utilities

Handles JWT (JSON Web Token) creation and verification.

WHAT IS JWT?
A JWT is a secure way to transmit information between parties as a JSON object.
It's digitally signed, so it can be verified and trusted.

JWT STRUCTURE:
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.Rq8LxQyaYh... 

Header.Payload.Signature

- Header: Algorithm (HS256)
- Payload: Data (user_id, expiry time)
- Signature: Verifies the token hasn't been tampered with
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from app.config.v1.settings import settings


# This function is used in the auth manager to create a JWT token after successful OTP verification
# Makes a new TOken
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token (e.g., {"sub": user_id})
        expires_delta: Optional custom expiry time
    
    Returns:
        str: Encoded JWT token
    
    HOW IT WORKS:
    1. Takes the data you want to store (usually user_id as "sub")
    2. Adds an expiration time (default: 24 hours)
    3. Encodes everything with a secret key
    4. Returns the token string
    
    Example token payload:
    {
        "sub": "1",                    # User ID
        "exp": 1747564200,             # Expiration timestamp
        "iat": 1747477800              # Issued at timestamp
    }
    """
    # Copy the data so we don't modify the original
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default: 24 hours from now
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    
    # Add expiration and issued-at timestamps
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    })
    
    # Encode the token with our secret key
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


# This function is used in the authentication middleware to verify the token and extract its payload
# Check if a token is valid
# def verify_access_token(token: str) -> Optional[dict]:
#     """
#     Verify a JWT token and return its payload.
    
#     Args:
#         token: The JWT token to verify
    
#     Returns:
#         dict with token payload if valid, None if invalid/expired
    
#     HOW IT WORKS:
#     1. Decodes the token using the secret key
#     2. Checks the signature (has it been tampered with?)
#     3. Checks the expiration time (has it expired?)
#     4. Returns the payload if everything is valid
#     """
#     try:
#         payload = jwt.decode(
#             token,
#             settings.JWT_SECRET_KEY,
#             algorithms=[settings.JWT_ALGORITHM],
#         )
#         return payload
#     except JWTError:
#         # Token is invalid (expired, wrong signature, etc.)
#         return None


# This function is used in the authentication middleware to extract the user ID from the token
# Reads who the token belongs to
# def get_user_id_from_token(token: str) -> Optional[int]:
#     """
#     Extract user ID from a JWT token.
    
#     Args:
#         token: The JWT token
    
#     Returns:
#         int: User ID if valid, None if invalid
#     """
#     payload = verify_access_token(token)
#     if payload and "sub" in payload:
#         return int(payload["sub"])
#     return None

