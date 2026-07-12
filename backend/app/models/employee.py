"""
Employee ORM model.
Single Responsibility: represents the employees table only.
Business Rule: email must be unique, one active seat per employee enforced at service layer.

IMPORTANT: Enum values MUST match the Neon PostgreSQL enum type exactly (UPPERCASE).
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class EmployeeStatus(str, enum.Enum):
    ACTIVE     = "ACTIVE"
    INACTIVE   = "INACTIVE"
    ON_LEAVE   = "ON_LEAVE"
    TERMINATED = "TERMINATED"

    @classmethod
    def _missing_(cls, value):
        """Accept lowercase values like 'active', 'inactive', 'on_leave' etc."""
        if isinstance(value, str):
            for member in cls:
                if member.value == value.upper():
                    return member
        return None


class Employee(Base):
    __tablename__ = "employees"

    id            = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String(20), unique=True, nullable=False, index=True)
    name          = Column(String(150), nullable=False, index=True)
    email         = Column(String(200), unique=True, nullable=False, index=True)
    department    = Column(String(100), nullable=True)
    role          = Column(String(100), nullable=True)
    joining_date  = Column(Date, default=date.today, nullable=False)
    status        = Column(SAEnum(EmployeeStatus, create_type=False), default=EmployeeStatus.ACTIVE, nullable=False)
    project_id    = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="employees")
    seat_allocations = relationship(
        "SeatAllocation",
        back_populates="employee",
        lazy="dynamic",
        foreign_keys="SeatAllocation.employee_id"
    )

    @property
    def active_allocation(self):
        return self.seat_allocations.filter_by(allocation_status="ACTIVE").first()

    def __repr__(self) -> str:
        return f"<Employee id={self.id} code={self.employee_code} name={self.name}>"
