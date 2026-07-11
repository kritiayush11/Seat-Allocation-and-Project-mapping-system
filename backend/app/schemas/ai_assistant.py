"""
Pydantic schemas for AI Assistant endpoint.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


class AIQuery(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=["Where is employee Amit seated?"]
    )
    session_id: Optional[str] = Field(None, description="Optional conversation session ID for memory")


class AIResponse(BaseModel):
    answer: str
    intent: Optional[str] = None
    data: Optional[Any] = None
    confidence: Optional[float] = None
    source: Optional[str] = Field(None, description="'rule_based' or 'openai'")
    session_id: Optional[str] = Field(None, description="The session ID associated with this query")


class DashboardSummary(BaseModel):
    total_employees: int
    active_employees: int
    total_seats: int
    occupied_seats: int
    available_seats: int
    reserved_seats: int
    maintenance_seats: int
    pending_allocation: int
    utilization_rate: float


class ProjectUtilization(BaseModel):
    project_id: int
    project_name: str
    total_employees: int
    allocated_seats: int
    unallocated_employees: int


class FloorUtilization(BaseModel):
    floor: int
    total_seats: int
    occupied: int
    available: int
    reserved: int
    maintenance: int
    occupancy_rate: float
