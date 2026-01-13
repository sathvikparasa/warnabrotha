"""
Parking sessions API endpoints.

Handles checking in (parking) and checking out (leaving).
"""

from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.parking_session import (
    ParkingSessionCreate,
    ParkingSessionResponse,
    CheckoutResponse,
)
from app.models.parking_session import ParkingSession
from app.models.parking_lot import ParkingLot
from app.models.device import Device
from app.services.auth import require_verified_device

router = APIRouter(prefix="/sessions", tags=["Parking Sessions"])


@router.post(
    "/checkin",
    response_model=ParkingSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Check in (park)",
    description="Register that you are parking at a lot. You will receive TAPS notifications."
)
async def check_in(
    session_data: ParkingSessionCreate,
    device: Device = Depends(require_verified_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Check in to a parking lot.

    Creates a new parking session, adding you to the notification list
    for TAPS sightings at this lot.

    - **parking_lot_id**: ID of the parking lot you're parking at
    """
    # Verify parking lot exists and is active
    result = await db.execute(
        select(ParkingLot).where(ParkingLot.id == session_data.parking_lot_id)
    )
    lot = result.scalar_one_or_none()

    if lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking lot {session_data.parking_lot_id} not found"
        )

    if not lot.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parking lot {lot.name} is not currently active"
        )

    # Check if device already has an active session
    existing_result = await db.execute(
        select(ParkingSession)
        .where(
            ParkingSession.device_id == device.id,
            ParkingSession.checked_out_at.is_(None)
        )
    )
    existing_session = existing_result.scalar_one_or_none()

    if existing_session is not None:
        # Get the lot name for the error message
        existing_lot_result = await db.execute(
            select(ParkingLot).where(ParkingLot.id == existing_session.parking_lot_id)
        )
        existing_lot = existing_lot_result.scalar_one()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an active parking session at {existing_lot.name}. "
                   f"Please check out first."
        )

    # Create new parking session
    session = ParkingSession(
        device_id=device.id,
        parking_lot_id=lot.id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ParkingSessionResponse.from_session(session, lot.name, lot.code)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Check out (leave)",
    description="Register that you are leaving the parking lot."
)
async def check_out(
    device: Device = Depends(require_verified_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Check out from your current parking session.

    Marks your parking session as complete and removes you from
    the TAPS notification list for that lot.
    """
    # Find active session for this device
    result = await db.execute(
        select(ParkingSession)
        .where(
            ParkingSession.device_id == device.id,
            ParkingSession.checked_out_at.is_(None)
        )
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You don't have an active parking session to check out from"
        )

    # Mark as checked out
    checkout_time = datetime.now(timezone.utc)
    session.checked_out_at = checkout_time
    await db.commit()

    return CheckoutResponse(
        success=True,
        message="Successfully checked out",
        session_id=session.id,
        checked_out_at=checkout_time,
    )


@router.get(
    "/current",
    response_model=Optional[ParkingSessionResponse],
    summary="Get current session",
    description="Get your current active parking session, if any."
)
async def get_current_session(
    device: Device = Depends(require_verified_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current active parking session for this device.

    Returns null if you don't have an active session.
    """
    # Find active session for this device
    result = await db.execute(
        select(ParkingSession)
        .where(
            ParkingSession.device_id == device.id,
            ParkingSession.checked_out_at.is_(None)
        )
    )
    session = result.scalar_one_or_none()

    if session is None:
        return None

    # Get lot details
    lot_result = await db.execute(
        select(ParkingLot).where(ParkingLot.id == session.parking_lot_id)
    )
    lot = lot_result.scalar_one()

    return ParkingSessionResponse.from_session(session, lot.name, lot.code)


@router.get(
    "/history",
    response_model=list[ParkingSessionResponse],
    summary="Get session history",
    description="Get your parking session history."
)
async def get_session_history(
    limit: int = 20,
    device: Device = Depends(require_verified_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Get parking session history for this device.

    - **limit**: Maximum number of sessions to return (default 20)
    """
    # Get sessions ordered by most recent first
    result = await db.execute(
        select(ParkingSession)
        .where(ParkingSession.device_id == device.id)
        .order_by(ParkingSession.checked_in_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()

    # Get lot details for all sessions
    lot_ids = {s.parking_lot_id for s in sessions}
    lots_result = await db.execute(
        select(ParkingLot).where(ParkingLot.id.in_(lot_ids))
    )
    lots = {lot.id: lot for lot in lots_result.scalars().all()}

    return [
        ParkingSessionResponse.from_session(
            session,
            lots[session.parking_lot_id].name,
            lots[session.parking_lot_id].code
        )
        for session in sessions
    ]
