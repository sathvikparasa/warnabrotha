"""
Vote model for tracking user votes on TAPS sightings.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class VoteType(str, enum.Enum):
    """Types of votes users can cast."""
    UPVOTE = "upvote"      # Confirms the sighting is accurate
    DOWNVOTE = "downvote"  # Indicates sighting may be inaccurate


class Vote(Base):
    """
    Represents a user's vote on a TAPS sighting.

    Each device can only vote once per sighting (enforced by unique constraint).
    Users can change their vote by updating the vote_type.

    Attributes:
        id: Primary key
        device_id: FK to the device that cast the vote
        sighting_id: FK to the sighting being voted on
        vote_type: UPVOTE or DOWNVOTE
        created_at: When the vote was initially cast
        updated_at: When the vote was last modified
    """

    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    sighting_id = Column(Integer, ForeignKey("taps_sightings.id"), nullable=False, index=True)
    vote_type = Column(Enum(VoteType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Ensure one vote per device per sighting
    __table_args__ = (
        UniqueConstraint('device_id', 'sighting_id', name='unique_device_sighting_vote'),
    )

    # Relationships
    device = relationship("Device", back_populates="votes")
    sighting = relationship("TapsSighting", back_populates="votes")

    def __repr__(self):
        return f"<Vote(id={self.id}, device_id={self.device_id}, sighting_id={self.sighting_id}, type={self.vote_type})>"
