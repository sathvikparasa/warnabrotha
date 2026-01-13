"""
Notifications API endpoints.

Handles in-app notification polling and management.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.notification import (
    NotificationResponse,
    NotificationList,
    MarkReadRequest,
)
from app.models.device import Device
from app.services.auth import get_current_device
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationList,
    summary="Get notifications",
    description="Get all notifications for the current device."
)
async def get_notifications(
    limit: int = 100,
    offset: int = 0,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all notifications for this device.

    Supports pagination with limit and offset.

    - **limit**: Maximum number of notifications to return
    - **offset**: Number of notifications to skip
    """
    notifications, unread_count, total = await NotificationService.get_all_notifications(
        db=db,
        device=device,
        limit=limit,
        offset=offset,
    )

    return NotificationList(
        notifications=[
            NotificationResponse(
                id=n.id,
                notification_type=n.notification_type.value,
                title=n.title,
                message=n.message,
                parking_lot_id=n.parking_lot_id,
                created_at=n.created_at,
                read_at=n.read_at,
                is_read=n.is_read,
            )
            for n in notifications
        ],
        unread_count=unread_count,
        total=total,
    )


@router.get(
    "/unread",
    response_model=NotificationList,
    summary="Get unread notifications",
    description="Get only unread notifications for the current device."
)
async def get_unread_notifications(
    limit: int = 50,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Get unread notifications for this device.

    This endpoint is optimized for polling - call it periodically
    to check for new TAPS alerts or reminders.
    """
    notifications = await NotificationService.get_unread_notifications(
        db=db,
        device=device,
        limit=limit,
    )

    return NotificationList(
        notifications=[
            NotificationResponse(
                id=n.id,
                notification_type=n.notification_type.value,
                title=n.title,
                message=n.message,
                parking_lot_id=n.parking_lot_id,
                created_at=n.created_at,
                read_at=n.read_at,
                is_read=n.is_read,
            )
            for n in notifications
        ],
        unread_count=len(notifications),
        total=len(notifications),
    )


@router.post(
    "/read",
    summary="Mark notifications as read",
    description="Mark one or more notifications as read."
)
async def mark_notifications_read(
    request: MarkReadRequest,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark notifications as read.

    - **notification_ids**: List of notification IDs to mark as read
    """
    marked_count = await NotificationService.mark_notifications_read(
        db=db,
        device=device,
        notification_ids=request.notification_ids,
    )

    return {
        "success": True,
        "marked_count": marked_count,
    }


@router.post(
    "/read/all",
    summary="Mark all notifications as read",
    description="Mark all unread notifications as read."
)
async def mark_all_notifications_read(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all notifications as read for this device.
    """
    # Get all unread notification IDs
    notifications = await NotificationService.get_unread_notifications(
        db=db,
        device=device,
        limit=1000,  # High limit to get all
    )

    if not notifications:
        return {
            "success": True,
            "marked_count": 0,
        }

    notification_ids = [n.id for n in notifications]
    marked_count = await NotificationService.mark_notifications_read(
        db=db,
        device=device,
        notification_ids=notification_ids,
    )

    return {
        "success": True,
        "marked_count": marked_count,
    }
