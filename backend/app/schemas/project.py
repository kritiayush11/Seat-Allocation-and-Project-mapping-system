"""
Pydantic schemas for Project entity.

Enum serialisation note:
  Models store UPPERCASE values (matching Neon PostgreSQL enum types).
  API responses serialise them as lowercase for frontend/test consistency.
  Input accepts both cases via field_validator on all input schemas.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_serializer, field_validator
from ..models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Indigo"])
    description: Optional[str] = Field(None, max_length=500)
    manager_name: Optional[str] = Field(None, max_length=150)
    status: ProjectStatus = ProjectStatus.ACTIVE

    @field_validator("status", mode="before")
    @classmethod
    def normalise_status(cls, v: Any) -> Any:
        """Accept 'active', 'ACTIVE', 'archived' etc — normalise to UPPERCASE."""
        if isinstance(v, str):
            return v.upper()
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    manager_name: Optional[str] = None
    status: Optional[ProjectStatus] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalise_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    employee_count: Optional[int] = 0
    occupied_seats: Optional[int] = 0

    @field_serializer("status")
    def serialize_status(self, v: ProjectStatus) -> str:
        return v.value.lower()

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    """Lightweight project reference used inside employee responses."""
    id: int
    name: str
    status: ProjectStatus

    @field_serializer("status")
    def serialize_status(self, v: ProjectStatus) -> str:
        return v.value.lower()

    model_config = {"from_attributes": True}
