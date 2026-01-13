"""
ParkingLot model representing parking structures on campus.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class ParkingLot(Base):
    """
    Represents a parking structure or lot on campus.

    Attributes:
        id: Primary key
        name: Human-readable name (e.g., "Hutchinson Parking Structure")
        code: Short code for the lot (e.g., "HUTCH")
        latitude: GPS latitude coordinate
        longitude: GPS longitude coordinate
        is_active: Whether this lot is currently being tracked
    """

    __tablename__ = "parking_lots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    parking_sessions = relationship("ParkingSession", back_populates="parking_lot")
    taps_sightings = relationship("TapsSighting", back_populates="parking_lot")

    def __repr__(self):
        return f"<ParkingLot(id={self.id}, name='{self.name}', code='{self.code}')>"
