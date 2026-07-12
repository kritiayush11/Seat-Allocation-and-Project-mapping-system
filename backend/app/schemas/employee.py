"""
Pydantic schemas for Employee entity.

Enum serialisation note:
  Models store UPPERCASE values (matching Neon PostgreSQL enum types).
  API responses serialise them as lowercase for frontend/test consistency.
  Input accepts both cases ('active' and 'ACTIVE') via field_validator.
"""
from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator
from ..models.employee import EmployeeStatus
from .project import ProjectSummary
from .seat import SeatResponse


class EmployeeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, examples=["Amit Kumar"])
    email: EmailStr = Field(..., examples=["amit@ethara.ai"])
    department: Optional[str] = Field(None, max_length=100, examples=["Engineering"])
    role: Optional[str] = Field(None, max_length=100, examples=["Software Engineer"])
    joining_date: date = Field(default_factory=date.today)
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    project_id: Optional[int] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalise_status(cls, v: Any) -> Any:
        """Accept 'active', 'ACTIVE', 'inactive' etc — normalise to UPPERCASE."""
        if isinstance(v, str):
            return v.upper()
        return v


class EmployeeCreate(EmployeeBase):
    employee_code: Optional[str] = Field(
        None, max_length=20,
        description="Auto-generated if not provided (ETH-XXXXX)"
    )


class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    role: Optional[str] = None
    joining_date: Optional[date] = None
    status: Optional[EmployeeStatus] = None
    project_id: Optional[int] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalise_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v


class SeatInfo(BaseModel):
    """Compact seat info embedded in employee response."""
    seat_id: int
    floor: int
    zone: str
    bay: str
    seat_number: str
    allocation_date: date

    model_config = {"from_attributes": True}


class EmployeeResponse(EmployeeBase):
    id: int
    employee_code: str
    created_at: datetime
    project: Optional[ProjectSummary] = None
    seat: Optional[SeatInfo] = None

    @field_serializer("status")
    def serialize_status(self, v: EmployeeStatus) -> str:
        return v.value.lower()

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    employees: list[EmployeeResponse]
