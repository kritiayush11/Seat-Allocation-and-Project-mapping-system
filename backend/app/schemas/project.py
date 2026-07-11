"""
Pydantic schemas for Project entity.
Separates API contract from ORM model (ISP — callers only see what they need).
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from ..models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Indigo"])
    description: Optional[str] = Field(None, max_length=500)
    manager_name: Optional[str] = Field(None, max_length=150)
    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    manager_name: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    employee_count: Optional[int] = 0
    occupied_seats: Optional[int] = 0

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    """Lightweight project reference used inside employee responses."""
    id: int
    name: str
    status: ProjectStatus

    model_config = {"from_attributes": True}
