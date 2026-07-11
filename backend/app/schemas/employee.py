"""
Pydantic schemas for Employee entity.
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
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

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    employees: list[EmployeeResponse]
