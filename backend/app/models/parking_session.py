"""
ParkingSession model tracking when users park at and leave lots.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ParkingSession(Base):
    """
    Represents a parking session - from when a user parks until they leave.

    A session is "active" if checked_out_at is NULL, meaning the user
    is still parked and should receive TAPS notifications.

    Attributes:
        id: Primary key
        device_id: FK to the device that created this session
        parking_lot_id: FK to the parking lot
        checked_in_at: When the user parked
        checked_out_at: When the user left (NULL if still parked)
        reminder_sent: Whether the 3-hour reminder was sent
        is_active: Computed property - True if user is still parked
    """

    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    parking_lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False, index=True)
    checked_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent = Column(Boolean, default=False, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="parking_sessions")
    parking_lot = relationship("ParkingLot", back_populates="parking_sessions")

    @property
    def is_active(self) -> bool:
        """Returns True if the user is still parked (hasn't checked out)."""
        return self.checked_out_at is None

    def __repr__(self):
        status = "active" if self.is_active else "checked_out"
        return f"<ParkingSession(id={self.id}, lot_id={self.parking_lot_id}, status={status})>"
