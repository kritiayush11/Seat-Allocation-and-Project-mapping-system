"""
Pydantic schemas for Seat and SeatAllocation entities.

Enum serialisation note:
  Models store UPPERCASE values (matching Neon PostgreSQL enum types).
  API responses serialise them as lowercase so the frontend and existing
  tests can rely on consistent lowercase strings.
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, field_serializer
from ..models.seat import SeatStatus
from ..models.seat_allocation import AllocationStatus


class SeatBase(BaseModel):
    floor: int = Field(..., ge=1, le=20, examples=[2])
    zone: str = Field(..., min_length=1, max_length=10, examples=["B"])
    bay: str = Field(..., min_length=1, max_length=20, examples=["Bay-4"])
    seat_number: str = Field(..., min_length=1, max_length=30, examples=["B4-23"])


class SeatCreate(SeatBase):
    status: SeatStatus = SeatStatus.AVAILABLE


class SeatUpdate(BaseModel):
    status: Optional[SeatStatus] = None
    floor: Optional[int] = Field(None, ge=1, le=20)
    zone: Optional[str] = Field(None, max_length=10)
    bay: Optional[str] = Field(None, max_length=20)
    seat_number: Optional[str] = Field(None, max_length=30)


class AllocationSummary(BaseModel):
    """Embedded allocation info inside SeatResponse."""
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    allocation_date: date
    allocation_status: AllocationStatus

    @field_serializer("allocation_status")
    def serialize_allocation_status(self, v: AllocationStatus) -> str:
        return v.value.lower()

    model_config = {"from_attributes": True}


class SeatResponse(SeatBase):
    id: int
    status: SeatStatus
    created_at: datetime
    current_allocation: Optional[AllocationSummary] = None

    @field_serializer("status")
    def serialize_status(self, v: SeatStatus) -> str:
        return v.value.lower()

    model_config = {"from_attributes": True}


class SeatListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    seats: list[SeatResponse]


class AllocateRequest(BaseModel):
    employee_id: int = Field(..., description="Employee to allocate seat to")
    seat_id: Optional[int] = Field(None, description="Specific seat ID; if None, auto-assign by proximity")
    project_id: Optional[int] = Field(None, description="Override project for allocation record")


class ReleaseRequest(BaseModel):
    employee_id: int = Field(..., description="Employee whose seat to release")


class SeatAllocationResponse(BaseModel):
    id: int
    employee_id: int
    seat_id: int
    project_id: Optional[int]
    allocation_status: AllocationStatus
    allocation_date: date
    released_date: Optional[date]
    seat: Optional[SeatResponse] = None

    @field_serializer("allocation_status")
    def serialize_allocation_status(self, v: AllocationStatus) -> str:
        return v.value.lower()

    model_config = {"from_attributes": True}
