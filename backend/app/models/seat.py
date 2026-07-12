"""
Seat ORM model.
Single Responsibility: represents the seats table only.
Business Rule: unique constraint on (floor, zone, bay, seat_number) prevents duplicates.

IMPORTANT: Enum values MUST match the Neon PostgreSQL enum type exactly (UPPERCASE).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class SeatStatus(str, enum.Enum):
    AVAILABLE   = "AVAILABLE"
    OCCUPIED    = "OCCUPIED"
    RESERVED    = "RESERVED"
    MAINTENANCE = "MAINTENANCE"

    @classmethod
    def _missing_(cls, value):
        """Accept lowercase values like 'available', 'occupied' etc."""
        if isinstance(value, str):
            for member in cls:
                if member.value == value.upper():
                    return member
        return None


class Seat(Base):
    __tablename__ = "seats"

    id          = Column(Integer, primary_key=True, index=True)
    floor       = Column(Integer, nullable=False, index=True)
    zone        = Column(String(10), nullable=False, index=True)
    bay         = Column(String(20), nullable=False)
    seat_number = Column(String(30), nullable=False, index=True)
    status      = Column(SAEnum(SeatStatus, create_type=False), default=SeatStatus.AVAILABLE, nullable=False, index=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("floor", "zone", "bay", "seat_number", name="uq_seat_location"),
    )

    allocations = relationship("SeatAllocation", back_populates="seat", lazy="dynamic")

    @property
    def current_allocation(self):
        return self.allocations.filter_by(allocation_status="ACTIVE").first()

    def __repr__(self) -> str:
        return f"<Seat id={self.id} floor={self.floor} zone={self.zone} seat={self.seat_number} status={self.status}>"
