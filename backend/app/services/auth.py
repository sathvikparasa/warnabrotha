"""
Authentication service for UC Davis email verification.

This service handles:
- Validating UC Davis email addresses
- Creating/managing device registrations
- JWT token generation for authenticated requests
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import re

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.database import get_db
from app.models.device import Device


# HTTP Bearer token security scheme
security = HTTPBearer()


class AuthService:
    """
    Service for handling UC Davis email authentication.

    We verify that users have a valid UC Davis email but don't store
    the email itself - only a flag indicating verification status.
    """

    # Regex pattern for UC Davis email addresses
    UCD_EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@" + re.escape(settings.ucd_email_domain) + r"$",
        re.IGNORECASE
    )

    @classmethod
    def is_valid_ucd_email(cls, email: str) -> bool:
        """
        Check if an email address is a valid UC Davis email.

        Args:
            email: Email address to validate

        Returns:
            True if the email ends with @ucdavis.edu
        """
        return bool(cls.UCD_EMAIL_PATTERN.match(email))

    @staticmethod
    def create_access_token(device_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token for a device.

        Args:
            device_id: The device ID to encode in the token
            expires_delta: Optional custom expiration time

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=settings.access_token_expire_hours)

        to_encode = {
            "sub": device_id,
            "exp": expire,
            "type": "access"
        }
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[str]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Device ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            device_id: str = payload.get("sub")
            if device_id is None:
                return None
            return device_id
        except JWTError:
            return None

    @staticmethod
    async def get_or_create_device(
        db: AsyncSession,
        device_id: str,
        push_token: Optional[str] = None
    ) -> Device:
        """
        Get an existing device or create a new one.

        Args:
            db: Database session
            device_id: Unique device identifier
            push_token: Optional APNs push token

        Returns:
            Device model instance
        """
        # Try to find existing device
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()

        if device:
            # Update push token if provided
            if push_token:
                device.push_token = push_token
                device.is_push_enabled = True
            await db.commit()
            await db.refresh(device)
            return device

        # Create new device
        device = Device(
            device_id=device_id,
            push_token=push_token,
            is_push_enabled=push_token is not None,
            email_verified=False,
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def verify_email_for_device(
        db: AsyncSession,
        device_id: str,
        email: str
    ) -> tuple[bool, str]:
        """
        Verify a UC Davis email for a device.

        Args:
            db: Database session
            device_id: Device ID to verify email for
            email: Email address to verify

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate email format
        if not AuthService.is_valid_ucd_email(email):
            return False, f"Email must be a valid {settings.ucd_email_domain} address"

        # Get device
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            return False, "Device not registered"

        # Mark as verified (we don't store the email)
        device.email_verified = True
        await db.commit()

        return True, "Email verified successfully"


async def get_current_device(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Device:
    """
    FastAPI dependency to get the current authenticated device.

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        Device model instance

    Raises:
        HTTPException: If token is invalid or device not found
    """
    token = credentials.credentials
    device_id = AuthService.decode_token(token)

    if device_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get device from database
    result = await db.execute(
        select(Device).where(Device.device_id == device_id)
    )
    device = result.scalar_one_or_none()

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return device


async def require_verified_device(
    device: Device = Depends(get_current_device)
) -> Device:
    """
    FastAPI dependency that requires an email-verified device.

    Args:
        device: Current device from authentication

    Returns:
        Device model instance

    Raises:
        HTTPException: If device email is not verified
    """
    if not device.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return device
