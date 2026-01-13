"""
TAPS probability prediction service.

Uses a combination of:
- Time of day patterns
- Day of week patterns
- Historical sighting data
- Recent sighting activity
- Academic calendar (quarters, finals, breaks)
- Weather data (optional)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.taps_sighting import TapsSighting
from app.models.parking_lot import ParkingLot
from app.schemas.prediction import PredictionFactors, PredictionResponse

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Service for predicting TAPS presence probability.

    The model combines multiple factors with learned weights to produce
    a probability estimate. Without ML training data, we use heuristic
    weights based on common parking enforcement patterns.
    """

    # Weight factors for combining predictions (sum to 1.0)
    WEIGHTS = {
        "time_of_day": 0.25,
        "day_of_week": 0.20,
        "historical": 0.20,
        "recent_sightings": 0.20,
        "academic_calendar": 0.15,
    }

    # UC Davis academic calendar approximate dates (2024-2025)
    # In production, this would be fetched from an API or database
    ACADEMIC_CALENDAR = {
        "fall_start": (9, 25),  # September 25
        "fall_end": (12, 13),   # December 13
        "winter_start": (1, 6),  # January 6
        "winter_end": (3, 21),   # March 21
        "spring_start": (3, 31), # March 31
        "spring_end": (6, 13),   # June 13
        # Finals weeks (high enforcement)
        "fall_finals": ((12, 7), (12, 13)),
        "winter_finals": ((3, 15), (3, 21)),
        "spring_finals": ((6, 7), (6, 13)),
    }

    @classmethod
    def _calculate_time_of_day_factor(cls, dt: datetime) -> float:
        """
        Calculate probability factor based on time of day.

        TAPS typically operates during business hours, with peak
        enforcement during late morning and early afternoon.

        Args:
            dt: Datetime to evaluate

        Returns:
            Factor between 0.0 and 1.0
        """
        hour = dt.hour

        # TAPS typically doesn't operate at night or very early morning
        if hour < 6 or hour >= 22:
            return 0.05

        # Early morning ramp-up (6-8 AM)
        if 6 <= hour < 8:
            return 0.2 + (hour - 6) * 0.15

        # Peak enforcement hours (8 AM - 5 PM)
        if 8 <= hour < 17:
            # Slight dip during lunch
            if 12 <= hour < 13:
                return 0.7
            return 0.85

        # Evening wind-down (5-10 PM)
        return 0.6 - (hour - 17) * 0.11

    @classmethod
    def _calculate_day_of_week_factor(cls, dt: datetime) -> float:
        """
        Calculate probability factor based on day of week.

        TAPS operates Monday-Friday primarily, with reduced
        weekend enforcement.

        Args:
            dt: Datetime to evaluate

        Returns:
            Factor between 0.0 and 1.0
        """
        day = dt.weekday()  # 0 = Monday, 6 = Sunday

        # Weekday patterns
        weekday_factors = {
            0: 0.85,  # Monday - high enforcement
            1: 0.90,  # Tuesday - highest
            2: 0.85,  # Wednesday
            3: 0.80,  # Thursday
            4: 0.70,  # Friday - reduced
            5: 0.15,  # Saturday - minimal
            6: 0.10,  # Sunday - minimal
        }

        return weekday_factors.get(day, 0.5)

    @classmethod
    async def _calculate_historical_factor(
        cls,
        db: AsyncSession,
        parking_lot_id: int,
        dt: datetime
    ) -> float:
        """
        Calculate probability factor based on historical sighting patterns.

        Looks at sightings from the past 90 days at similar times.

        Args:
            db: Database session
            parking_lot_id: Parking lot ID
            dt: Datetime to evaluate

        Returns:
            Factor between 0.0 and 1.0
        """
        # Get sightings from the past 90 days at similar time (+/- 2 hours)
        start_date = dt - timedelta(days=90)
        hour_start = (dt.hour - 2) % 24
        hour_end = (dt.hour + 2) % 24

        result = await db.execute(
            select(func.count(TapsSighting.id))
            .where(
                TapsSighting.parking_lot_id == parking_lot_id,
                TapsSighting.reported_at >= start_date,
                func.extract('dow', TapsSighting.reported_at) == dt.weekday(),
            )
        )
        count = result.scalar() or 0

        # Normalize: 0 sightings = 0.3 (baseline), 10+ sightings = 0.95
        if count == 0:
            return 0.3
        return min(0.3 + (count * 0.065), 0.95)

    @classmethod
    async def _calculate_recent_sightings_factor(
        cls,
        db: AsyncSession,
        parking_lot_id: int,
        dt: datetime
    ) -> float:
        """
        Calculate probability factor based on recent sighting activity.

        Recent sightings (last 24-48 hours) indicate TAPS activity in the area.

        Args:
            db: Database session
            parking_lot_id: Parking lot ID
            dt: Datetime to evaluate

        Returns:
            Factor between 0.0 and 1.0
        """
        # Sightings in last 2 hours suggest TAPS is still around
        two_hours_ago = dt - timedelta(hours=2)
        result = await db.execute(
            select(func.count(TapsSighting.id))
            .where(
                TapsSighting.parking_lot_id == parking_lot_id,
                TapsSighting.reported_at >= two_hours_ago,
            )
        )
        very_recent = result.scalar() or 0

        if very_recent > 0:
            return 0.95  # TAPS was just seen, very high probability

        # Sightings in last 24 hours
        one_day_ago = dt - timedelta(hours=24)
        result = await db.execute(
            select(func.count(TapsSighting.id))
            .where(
                TapsSighting.parking_lot_id == parking_lot_id,
                TapsSighting.reported_at >= one_day_ago,
            )
        )
        recent = result.scalar() or 0

        if recent == 0:
            return 0.4  # No recent activity
        return min(0.5 + (recent * 0.1), 0.85)

    @classmethod
    def _calculate_academic_calendar_factor(cls, dt: datetime) -> float:
        """
        Calculate probability factor based on academic calendar.

        Higher enforcement during active quarters, especially finals.
        Lower during breaks and summer.

        Args:
            dt: Datetime to evaluate

        Returns:
            Factor between 0.0 and 1.0
        """
        month, day = dt.month, dt.day

        def in_range(start: Tuple[int, int], end: Tuple[int, int]) -> bool:
            """Check if date is within range."""
            start_m, start_d = start
            end_m, end_d = end
            if start_m <= end_m:
                if month < start_m or month > end_m:
                    return False
                if month == start_m and day < start_d:
                    return False
                if month == end_m and day > end_d:
                    return False
                return True
            else:  # Spans year boundary (e.g., fall to winter break)
                if month >= start_m or month <= end_m:
                    if month == start_m and day < start_d:
                        return False
                    if month == end_m and day > end_d:
                        return False
                    return True
                return False

        # Check finals weeks (highest enforcement)
        for finals_key in ["fall_finals", "winter_finals", "spring_finals"]:
            start, end = cls.ACADEMIC_CALENDAR[finals_key]
            if in_range(start, end):
                return 0.95

        # Check active quarter periods
        quarters = [
            ("fall_start", "fall_end"),
            ("winter_start", "winter_end"),
            ("spring_start", "spring_end"),
        ]

        for start_key, end_key in quarters:
            start = cls.ACADEMIC_CALENDAR[start_key]
            end = cls.ACADEMIC_CALENDAR[end_key]
            if in_range(start, end):
                return 0.75

        # Summer or break period
        return 0.35

    @classmethod
    def _get_risk_level(cls, probability: float) -> str:
        """
        Convert probability to human-readable risk level.

        Args:
            probability: Probability value (0.0 - 1.0)

        Returns:
            Risk level string
        """
        if probability < 0.3:
            return "LOW"
        elif probability < 0.6:
            return "MEDIUM"
        else:
            return "HIGH"

    @classmethod
    def _calculate_confidence(
        cls,
        historical_count: int,
        recent_count: int
    ) -> float:
        """
        Calculate model confidence based on available data.

        More historical data = higher confidence in predictions.

        Args:
            historical_count: Number of historical sightings
            recent_count: Number of recent sightings

        Returns:
            Confidence value (0.0 - 1.0)
        """
        # Base confidence
        base = 0.4

        # Historical data contribution
        historical_contrib = min(historical_count * 0.02, 0.3)

        # Recent data contribution
        recent_contrib = min(recent_count * 0.05, 0.2)

        return min(base + historical_contrib + recent_contrib, 0.95)

    @classmethod
    async def predict(
        cls,
        db: AsyncSession,
        parking_lot_id: int,
        timestamp: Optional[datetime] = None
    ) -> PredictionResponse:
        """
        Generate TAPS probability prediction for a parking lot.

        Args:
            db: Database session
            parking_lot_id: ID of the parking lot
            timestamp: Time to predict for (defaults to now)

        Returns:
            PredictionResponse with probability and factors

        Raises:
            ValueError: If parking lot not found
        """
        # Get parking lot
        result = await db.execute(
            select(ParkingLot).where(ParkingLot.id == parking_lot_id)
        )
        parking_lot = result.scalar_one_or_none()

        if parking_lot is None:
            raise ValueError(f"Parking lot {parking_lot_id} not found")

        # Use current time if not specified
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Calculate individual factors
        time_factor = cls._calculate_time_of_day_factor(timestamp)
        day_factor = cls._calculate_day_of_week_factor(timestamp)
        historical_factor = await cls._calculate_historical_factor(db, parking_lot_id, timestamp)
        recent_factor = await cls._calculate_recent_sightings_factor(db, parking_lot_id, timestamp)
        calendar_factor = cls._calculate_academic_calendar_factor(timestamp)

        # Combine factors using weights
        probability = (
            time_factor * cls.WEIGHTS["time_of_day"] +
            day_factor * cls.WEIGHTS["day_of_week"] +
            historical_factor * cls.WEIGHTS["historical"] +
            recent_factor * cls.WEIGHTS["recent_sightings"] +
            calendar_factor * cls.WEIGHTS["academic_calendar"]
        )

        # Clamp probability to valid range
        probability = max(0.0, min(1.0, probability))

        # Get counts for confidence calculation
        ninety_days_ago = timestamp - timedelta(days=90)
        hist_result = await db.execute(
            select(func.count(TapsSighting.id))
            .where(
                TapsSighting.parking_lot_id == parking_lot_id,
                TapsSighting.reported_at >= ninety_days_ago,
            )
        )
        historical_count = hist_result.scalar() or 0

        one_day_ago = timestamp - timedelta(hours=24)
        recent_result = await db.execute(
            select(func.count(TapsSighting.id))
            .where(
                TapsSighting.parking_lot_id == parking_lot_id,
                TapsSighting.reported_at >= one_day_ago,
            )
        )
        recent_count = recent_result.scalar() or 0

        confidence = cls._calculate_confidence(historical_count, recent_count)

        # Build response
        factors = PredictionFactors(
            time_of_day_factor=round(time_factor, 3),
            day_of_week_factor=round(day_factor, 3),
            historical_factor=round(historical_factor, 3),
            recent_sightings_factor=round(recent_factor, 3),
            academic_calendar_factor=round(calendar_factor, 3),
            weather_factor=None,  # Not implemented yet
        )

        return PredictionResponse(
            parking_lot_id=parking_lot.id,
            parking_lot_name=parking_lot.name,
            parking_lot_code=parking_lot.code,
            probability=round(probability, 3),
            risk_level=cls._get_risk_level(probability),
            predicted_for=timestamp,
            factors=factors,
            confidence=round(confidence, 3),
        )
