"""
Pydantic Schemas (Request/Response Models)

These define the SHAPE of data coming IN and going OUT of our API.

Every schema is a contract:
- Request schemas: What the CLIENT must send
- Response schemas: What the SERVER will return

Pydantic automatically:
1. Validates data types (str, int, EmailStr)
2. Validates constraints (min_length, max_length)
3. Generates JSON Schema for OpenAPI documentation
4. Returns clear error messages for invalid data
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ============================================
# AUTHENTICATION SCHEMAS
# ============================================

class SendOTPRequest(BaseModel):
    """
    Schema for requesting an OTP.
    
    Used at: POST /api/v1/auth/send-otp
    
    The client sends either email OR phone_number.
    At least one is required.
    """
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address for receiving OTP"
    )
    phone_number: Optional[str] = Field(
        None,
        min_length=10,
        max_length=15,
        description="User's phone number for receiving OTP"
    )


class VerifyOTPRequest(BaseModel):
    """
    Schema for verifying an OTP.
    
    Used at: POST /api/v1/auth/verify-otp
    
    The client sends their identifier (email or phone)
    and the OTP they received.
    """
    email: Optional[EmailStr] = Field(
        None,
        description="Email used to receive OTP"
    )
    phone_number: Optional[str] = Field(
        None,
        description="Phone number used to receive OTP"
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The 6-digit OTP code"
    )


# ============================================
# RESPONSE SCHEMAS
# ============================================

class TokenResponse(BaseModel):
    """
    Schema for login/signup response.
    
    Returned after successful OTP verification.
    Contains the JWT access token.
    """
    access_token: str = Field(
        ...,
        description="JWT access token for authentication"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    user: "UserResponse"


class UserResponse(BaseModel):
    """
    Schema for user data in responses.
    
    NEVER includes sensitive fields like otp_code.
    """
    id: int
    email: str
    phone_number: Optional[str] # = None
    # name: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    # This allows Pydantic to read ORM objects directly
    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """
    Generic message response.
    
    Used for simple success/error messages.
    """
    message: str = Field(..., description="Response message")
    detail: Optional[str] = Field(None, description="Additional details")


# ============================================
# UPDATE SCHEMA (forward reference fix)
# ============================================

# This must be after TokenResponse because TokenResponse references UserResponse
TokenResponse.model_rebuild()




