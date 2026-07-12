"""
SeatAllocation ORM model — junction table between Employee and Seat.
Tracks current and historical allocations.
Business Rule: Only one 'ACTIVE' allocation per seat and per employee enforced here + at service layer.

IMPORTANT: Enum values MUST match the Neon PostgreSQL enum type exactly (UPPERCASE).
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Date, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class AllocationStatus(str, enum.Enum):
    ACTIVE      = "ACTIVE"
    RELEASED    = "RELEASED"
    TRANSFERRED = "TRANSFERRED"

    @classmethod
    def _missing_(cls, value):
        """Accept lowercase values like 'active', 'released' etc."""
        if isinstance(value, str):
            for member in cls:
                if member.value == value.upper():
                    return member
        return None


class SeatAllocation(Base):
    __tablename__ = "seat_allocations"

    id                = Column(Integer, primary_key=True, index=True)
    employee_id       = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    seat_id           = Column(Integer, ForeignKey("seats.id"), nullable=False, index=True)
    project_id        = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    allocation_status = Column(SAEnum(AllocationStatus, create_type=False), default=AllocationStatus.ACTIVE, nullable=False, index=True)
    allocation_date   = Column(Date, default=date.today, nullable=False)
    released_date     = Column(Date, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = relationship("Employee", back_populates="seat_allocations", foreign_keys=[employee_id])
    seat     = relationship("Seat", back_populates="allocations")
    project  = relationship("Project", back_populates="seat_allocations")

    __table_args__ = (
        Index("idx_active_employee_allocation", "employee_id", "allocation_status"),
        Index("idx_active_seat_allocation", "seat_id", "allocation_status"),
    )

    def __repr__(self) -> str:
        return f"<SeatAllocation id={self.id} emp={self.employee_id} seat={self.seat_id} status={self.allocation_status}>"
