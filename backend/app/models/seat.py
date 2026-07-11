"""
Seat ORM model.
Single Responsibility: represents the seats table only.
Business Rule: unique constraint on (floor, zone, bay, seat_number) prevents duplicates.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    floor = Column(Integer, nullable=False, index=True)
    zone = Column(String(10), nullable=False, index=True)
    bay = Column(String(20), nullable=False)
    seat_number = Column(String(30), nullable=False, index=True)
    status = Column(SAEnum(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Composite unique: no duplicate seat on same floor/zone/bay
    __table_args__ = (
        UniqueConstraint("floor", "zone", "bay", "seat_number", name="uq_seat_location"),
    )

    # Relationships
    allocations = relationship("SeatAllocation", back_populates="seat", lazy="dynamic")

    @property
    def current_allocation(self):
        """Returns the active allocation for this seat, if any."""
        return self.allocations.filter_by(allocation_status="active").first()

    def __repr__(self) -> str:
        return f"<Seat id={self.id} floor={self.floor} zone={self.zone} seat={self.seat_number} status={self.status}>"
