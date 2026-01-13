"""
TAPS probability prediction API endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.models.device import Device
from app.services.auth import get_current_device
from app.services.prediction import PredictionService

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get(
    "/{lot_id}",
    response_model=PredictionResponse,
    summary="Get TAPS probability",
    description="Get the predicted probability of TAPS presence at a parking lot."
)
async def get_prediction(
    lot_id: int,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Get TAPS probability prediction for a parking lot.

    Uses current time for the prediction. Returns:
    - Probability (0.0 - 1.0)
    - Risk level (LOW, MEDIUM, HIGH)
    - Contributing factors with their weights
    - Model confidence
    """
    try:
        prediction = await PredictionService.predict(
            db=db,
            parking_lot_id=lot_id,
            timestamp=datetime.now(timezone.utc),
        )
        return prediction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "",
    response_model=PredictionResponse,
    summary="Get TAPS probability for specific time",
    description="Get the predicted probability of TAPS presence at a specific time."
)
async def predict_for_time(
    request: PredictionRequest,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    """
    Get TAPS probability prediction for a specific time.

    Useful for planning when to park - check probability at different times.

    - **parking_lot_id**: ID of the parking lot
    - **timestamp**: Time to predict for (defaults to now)
    """
    try:
        prediction = await PredictionService.predict(
            db=db,
            parking_lot_id=request.parking_lot_id,
            timestamp=request.timestamp or datetime.now(timezone.utc),
        )
        return prediction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
