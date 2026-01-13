"""
Tests for TAPS probability prediction endpoints and services.
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parking_lot import ParkingLot
from app.models.taps_sighting import TapsSighting
from app.services.prediction import PredictionService


class TestPredictionService:
    """Tests for PredictionService class."""

    def test_time_of_day_factor_night(self):
        """Test that nighttime has low probability."""
        # 2 AM - should be very low
        dt = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
        factor = PredictionService._calculate_time_of_day_factor(dt)
        assert factor < 0.1

    def test_time_of_day_factor_peak(self):
        """Test that peak hours have high probability."""
        # 10 AM - peak enforcement
        dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        factor = PredictionService._calculate_time_of_day_factor(dt)
        assert factor > 0.7

    def test_day_of_week_factor_weekday(self):
        """Test that weekdays have higher probability."""
        # Tuesday
        dt = datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc)
        factor = PredictionService._calculate_day_of_week_factor(dt)
        assert factor > 0.8

    def test_day_of_week_factor_weekend(self):
        """Test that weekends have lower probability."""
        # Saturday
        dt = datetime(2024, 1, 13, 10, 0, 0, tzinfo=timezone.utc)
        factor = PredictionService._calculate_day_of_week_factor(dt)
        assert factor < 0.2

    def test_academic_calendar_factor_during_quarter(self):
        """Test higher probability during active quarter."""
        # October - fall quarter
        dt = datetime(2024, 10, 15, 10, 0, 0, tzinfo=timezone.utc)
        factor = PredictionService._calculate_academic_calendar_factor(dt)
        assert factor > 0.5

    def test_academic_calendar_factor_summer(self):
        """Test lower probability during summer."""
        # July - summer
        dt = datetime(2024, 7, 15, 10, 0, 0, tzinfo=timezone.utc)
        factor = PredictionService._calculate_academic_calendar_factor(dt)
        assert factor < 0.5

    def test_risk_level_low(self):
        """Test LOW risk level for low probability."""
        assert PredictionService._get_risk_level(0.1) == "LOW"
        assert PredictionService._get_risk_level(0.29) == "LOW"

    def test_risk_level_medium(self):
        """Test MEDIUM risk level for medium probability."""
        assert PredictionService._get_risk_level(0.3) == "MEDIUM"
        assert PredictionService._get_risk_level(0.59) == "MEDIUM"

    def test_risk_level_high(self):
        """Test HIGH risk level for high probability."""
        assert PredictionService._get_risk_level(0.6) == "HIGH"
        assert PredictionService._get_risk_level(0.9) == "HIGH"

    @pytest.mark.asyncio
    async def test_predict(
        self,
        db_session: AsyncSession,
        test_parking_lot: ParkingLot
    ):
        """Test full prediction."""
        prediction = await PredictionService.predict(
            db=db_session,
            parking_lot_id=test_parking_lot.id,
        )

        assert prediction.parking_lot_id == test_parking_lot.id
        assert prediction.parking_lot_name == test_parking_lot.name
        assert 0.0 <= prediction.probability <= 1.0
        assert prediction.risk_level in ["LOW", "MEDIUM", "HIGH"]
        assert prediction.factors is not None
        assert 0.0 <= prediction.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_predict_nonexistent_lot(self, db_session: AsyncSession):
        """Test prediction for non-existent lot raises error."""
        with pytest.raises(ValueError):
            await PredictionService.predict(
                db=db_session,
                parking_lot_id=99999,
            )

    @pytest.mark.asyncio
    async def test_recent_sightings_increase_probability(
        self,
        db_session: AsyncSession,
        test_parking_lot: ParkingLot
    ):
        """Test that recent sightings increase probability."""
        # Get baseline prediction
        baseline = await PredictionService.predict(
            db=db_session,
            parking_lot_id=test_parking_lot.id,
        )

        # Add a recent sighting
        sighting = TapsSighting(
            parking_lot_id=test_parking_lot.id,
        )
        db_session.add(sighting)
        await db_session.commit()

        # Get new prediction
        after_sighting = await PredictionService.predict(
            db=db_session,
            parking_lot_id=test_parking_lot.id,
        )

        # Probability should increase with recent sighting
        assert after_sighting.factors.recent_sightings_factor > baseline.factors.recent_sightings_factor


class TestPredictionEndpoints:
    """Tests for prediction API endpoints."""

    @pytest.mark.asyncio
    async def test_get_prediction(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_parking_lot: ParkingLot
    ):
        """Test getting a prediction."""
        response = await client.get(
            f"/api/v1/predictions/{test_parking_lot.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["parking_lot_id"] == test_parking_lot.id
        assert "probability" in data
        assert "risk_level" in data
        assert "factors" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_get_prediction_invalid_lot(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting prediction for non-existent lot."""
        response = await client.get(
            "/api/v1/predictions/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_predict_for_specific_time(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_parking_lot: ParkingLot
    ):
        """Test predicting for a specific time."""
        response = await client.post(
            "/api/v1/predictions",
            headers=auth_headers,
            json={
                "parking_lot_id": test_parking_lot.id,
                "timestamp": "2024-10-15T10:00:00Z"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["predicted_for"] == "2024-10-15T10:00:00Z"

    @pytest.mark.asyncio
    async def test_predict_for_current_time(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_parking_lot: ParkingLot
    ):
        """Test predicting for current time (no timestamp)."""
        response = await client.post(
            "/api/v1/predictions",
            headers=auth_headers,
            json={
                "parking_lot_id": test_parking_lot.id
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "predicted_for" in data
