"""
Dashboard router — aggregation endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.dashboard_service import DashboardService
from ..schemas.ai_assistant import DashboardSummary, ProjectUtilization, FloorUtilization
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)


def get_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Overall dashboard summary: employee counts, seat counts, utilization rate",
)
def get_summary(service: DashboardService = Depends(get_service)):
    return service.get_summary()


@router.get(
    "/project-utilization",
    response_model=List[ProjectUtilization],
    summary="Per-project employee count, allocated seats, and pending allocations",
)
def get_project_utilization(service: DashboardService = Depends(get_service)):
    return service.get_project_utilization()


@router.get(
    "/floor-utilization",
    response_model=List[FloorUtilization],
    summary="Per-floor seat occupancy breakdown with utilization rate",
)
def get_floor_utilization(service: DashboardService = Depends(get_service)):
    return service.get_floor_utilization()
