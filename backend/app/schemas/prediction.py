"""
Pydantic schemas for TAPS probability prediction.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PredictionRequest(BaseModel):
    """
    Schema for requesting a TAPS probability prediction.
    If timestamp is not provided, uses current time.
    """
    parking_lot_id: int = Field(..., description="ID of the parking lot")
    timestamp: Optional[datetime] = Field(None, description="Time to predict for (defaults to now)")

    class Config:
        json_schema_extra = {
            "example": {
                "parking_lot_id": 1,
                "timestamp": "2024-01-15T14:30:00Z"
            }
        }


class PredictionFactors(BaseModel):
    """
    Schema detailing the factors that contributed to the prediction.
    Helps users understand why the probability is what it is.
    """
    time_of_day_factor: float = Field(..., ge=0.0, le=1.0, description="Contribution from time of day")
    day_of_week_factor: float = Field(..., ge=0.0, le=1.0, description="Contribution from day of week")
    historical_factor: float = Field(..., ge=0.0, le=1.0, description="Contribution from historical sightings")
    recent_sightings_factor: float = Field(..., ge=0.0, le=1.0, description="Contribution from recent sightings")
    academic_calendar_factor: float = Field(..., ge=0.0, le=1.0, description="Contribution from academic calendar")
    weather_factor: Optional[float] = Field(None, ge=0.0, le=1.0, description="Contribution from weather")


class PredictionResponse(BaseModel):
    """Schema for TAPS probability prediction response."""
    parking_lot_id: int
    parking_lot_name: str
    parking_lot_code: str
    probability: float = Field(..., ge=0.0, le=1.0, description="Predicted probability (0-1) of TAPS presence")
    risk_level: str = Field(..., description="Human-readable risk level (LOW, MEDIUM, HIGH)")
    predicted_for: datetime = Field(..., description="Timestamp the prediction is for")
    factors: PredictionFactors = Field(..., description="Factors contributing to the prediction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in the prediction")

    class Config:
        json_schema_extra = {
            "example": {
                "parking_lot_id": 1,
                "parking_lot_name": "Hutchinson Parking Structure",
                "parking_lot_code": "HUTCH",
                "probability": 0.65,
                "risk_level": "MEDIUM",
                "predicted_for": "2024-01-15T14:30:00Z",
                "factors": {
                    "time_of_day_factor": 0.7,
                    "day_of_week_factor": 0.8,
                    "historical_factor": 0.5,
                    "recent_sightings_factor": 0.6,
                    "academic_calendar_factor": 0.7,
                    "weather_factor": 0.3
                },
                "confidence": 0.75
            }
        }
