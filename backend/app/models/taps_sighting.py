"""
TapsSighting model recording when TAPS is spotted at a parking lot.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TapsSighting(Base):
    """
    Records a TAPS sighting at a parking lot.

    Each sighting triggers notifications to all users currently
    parked at that lot.

    Attributes:
        id: Primary key
        parking_lot_id: FK to the lot where TAPS was spotted
        reported_by_device_id: FK to the device that reported (nullable for anonymous)
        reported_at: When the sighting was reported
        notes: Optional notes about the sighting
    """

    __tablename__ = "taps_sightings"

    id = Column(Integer, primary_key=True, index=True)
    parking_lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False, index=True)
    reported_by_device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    notes = Column(String(500), nullable=True)

    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="taps_sightings")
    reported_by_device = relationship("Device", back_populates="taps_sightings")
    votes = relationship("Vote", back_populates="sighting", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TapsSighting(id={self.id}, lot_id={self.parking_lot_id}, at={self.reported_at})>"
