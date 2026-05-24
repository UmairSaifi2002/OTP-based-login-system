"""
Database Models - SQLAlchemy 2.0 ORM

This defines the structure of our MySQL tables.
Each class with table=True becomes a real database table.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.v1 import Base


# Helper function for UTC timestamps (replaces deprecated datetime.utcnow)
def utcnow():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)

# ============================================
# USER TABLE
# ============================================


class User(Base):
    """
    Users table - stores registered users.
    
    This is our ONLY table. It stores:
    - Basic user info (email, phone, name)
    - OTP code and expiry (for login verification)
    - Account status
    
    MySQL Table Structure:
    ┌──────────────┬──────────────┬──────────────────────────────┐
    │ Column       │ Type         │ Description                  │
    ├──────────────┼──────────────┼──────────────────────────────┤
    │ id           │ INT (PK)     │ Auto-incrementing ID         │
    │ email        │ VARCHAR(255) │ User's email (unique)        │
    │ phone_number │ VARCHAR(20)  │ User's phone (nullable)      │
    │ name         │ VARCHAR(100) │ User's name (nullable)       │
    │ otp_code     │ VARCHAR(6)   │ Current OTP code             │
    │ otp_expires_at│ DATETIME    │ When OTP expires             │
    │ is_active    │ BOOLEAN      │ Account status               │
    │ created_at   │ DATETIME     │ When user was created        │
    │ updated_at   │ DATETIME     │ Last update timestamp        │
    └──────────────┴──────────────┴──────────────────────────────┘
    """

    __tablename__ = "users"

    # ============================================
    # PRIMARY KEY
    # ============================================
    # autoincrement=True: MySQL generates IDs (1, 2, 3, ...)

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key = True,
        autoincrement = True
    )

    # ============================================
    # USER IDENTIFICATION
    # ============================================
    # Email is the primary identifier for signup
    # unique=True: No two users can have the same email
    email: Mapped[str] = mapped_column(
        String(255),
        unique = True,
        nullable = False,
        index = True # Fast Lookup by email
    )

    # Phone number is optional (only used for OTP via SMS)
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique = True,
        nullable = True,
    )

    # # Display name (optional)
    # name: Mapped[Optional[str]] = mapped_column(
    #     String(100),
    #     nullable = True,
    # )

    # ============================================
    # OTP AUTHENTICATION
    # ============================================
    # The current OTP code (6 digits)
    otp_code: Mapped[Optional[str]] = mapped_column(
        String(6),
        nullable = True,
    )

    # When the OTP expires (after this time, OTP is invalid)
    otp_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable = True,
    )

    # ============================================
    # ACCOUNT STATUS
    # ============================================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default = True
    )

    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default = utcnow,
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        default = utcnow,
        onupdate = utcnow,
    )

    def __repr__(self) -> str:
        """String Representation for DEBUGING"""
        return f"<User(id={self.id}, email='{self.email}')>"













