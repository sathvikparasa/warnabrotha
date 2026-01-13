"""
Authentication API endpoints.

Handles device registration and UC Davis email verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    TokenResponse,
)
from app.services.auth import AuthService, get_current_device
from app.models.device import Device
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a device",
    description="Register a new device and receive an access token."
)
async def register_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new device or get existing device's token.

    - **device_id**: Unique device identifier (UUID from iOS)
    - **push_token**: Optional APNs push notification token
    """
    device = await AuthService.get_or_create_device(
        db=db,
        device_id=device_data.device_id,
        push_token=device_data.push_token,
    )

    # Generate access token
    access_token = AuthService.create_access_token(device.device_id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_hours * 3600,
    )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
    summary="Verify UC Davis email",
    description="Verify a UC Davis email address for the device."
)
async def verify_email(
    verification: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify a UC Davis email address.

    The email must end with @ucdavis.edu to be valid.
    We only store that verification was successful, not the email itself.
    """
    success, message = await AuthService.verify_email_for_device(
        db=db,
        device_id=verification.device_id,
        email=verification.email,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return EmailVerificationResponse(
        success=True,
        message=message,
        email_verified=True,
    )


@router.get(
    "/me",
    response_model=DeviceResponse,
    summary="Get current device info",
    description="Get information about the currently authenticated device."
)
async def get_device_info(
    device: Device = Depends(get_current_device)
):
    """Get the current device's information."""
    return DeviceResponse.model_validate(device)


@router.patch(
    "/me",
    response_model=DeviceResponse,
    summary="Update device settings",
    description="Update the current device's settings."
)
async def update_device(
    updates: DeviceUpdate,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Update device settings.

    - **push_token**: Update APNs push notification token
    - **is_push_enabled**: Enable/disable push notifications
    """
    if updates.push_token is not None:
        device.push_token = updates.push_token

    if updates.is_push_enabled is not None:
        device.is_push_enabled = updates.is_push_enabled

    await db.commit()
    await db.refresh(device)

    return DeviceResponse.model_validate(device)
