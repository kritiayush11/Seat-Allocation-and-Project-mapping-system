"""
Project ORM model.
Single Responsibility: represents the projects table only.

IMPORTANT: Enum values MUST match the Neon PostgreSQL enum type exactly (UPPERCASE).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class ProjectStatus(str, enum.Enum):
    ACTIVE   = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"

    @classmethod
    def _missing_(cls, value):
        """Accept lowercase values like 'active', 'archived' etc."""
        if isinstance(value, str):
            for member in cls:
                if member.value == value.upper():
                    return member
        return None


class Project(Base):
    __tablename__ = "projects"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), unique=True, nullable=False, index=True)
    description  = Column(String(500), nullable=True)
    manager_name = Column(String(150), nullable=True)
    status       = Column(SAEnum(ProjectStatus, create_type=False), default=ProjectStatus.ACTIVE, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employees        = relationship("Employee", back_populates="project", lazy="dynamic")
    seat_allocations = relationship("SeatAllocation", back_populates="project", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name} status={self.status}>"
