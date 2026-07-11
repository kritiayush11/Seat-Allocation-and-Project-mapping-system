"""
Seats router — all /seats endpoints.
Includes seat CRUD, allocation, release, and suggestion endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.seat_allocation_service import SeatAllocationService
from ..schemas.seat import (
    SeatCreate, SeatUpdate, SeatResponse, SeatListResponse,
    AllocateRequest, ReleaseRequest, SeatAllocationResponse,
)
from ..models.seat import SeatStatus
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/seats",
    tags=["Seats"],
    dependencies=[Depends(get_current_user)]
)


def get_service(db: Session = Depends(get_db)) -> SeatAllocationService:
    return SeatAllocationService(db)


@router.post(
    "",
    response_model=SeatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new seat",
)
def create_seat(
    data: SeatCreate,
    service: SeatAllocationService = Depends(get_service),
):
    """
    Create a seat. floor/zone/bay/seat_number combination must be unique.
    """
    seat = service.create_seat(
        floor=data.floor,
        zone=data.zone,
        bay=data.bay,
        seat_number=data.seat_number,
        seat_status=data.status,
    )
    return _seat_response(seat, service)


@router.get(
    "",
    response_model=SeatListResponse,
    summary="List seats with optional filters",
)
def list_seats(
    floor: Optional[int] = Query(None, ge=1),
    zone: Optional[str] = Query(None, max_length=10),
    seat_status: Optional[SeatStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SeatAllocationService = Depends(get_service),
):
    result = service.list_seats(
        floor=floor, zone=zone, seat_status=seat_status, page=page, page_size=page_size
    )
    return SeatListResponse(
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        seats=[_seat_response(s, service) for s in result["seats"]],
    )


@router.get(
    "/available",
    response_model=List[SeatResponse],
    summary="List available seats (optionally filtered by floor/zone)",
)
def get_available_seats(
    floor: Optional[int] = Query(None, ge=1),
    zone: Optional[str] = Query(None),
    service: SeatAllocationService = Depends(get_service),
):
    seats = service.get_available_seats(floor=floor, zone=zone)
    return [_seat_response(s, service) for s in seats]


@router.get(
    "/suggest",
    response_model=List[SeatResponse],
    summary="Suggest best seats for a new joiner based on project proximity",
)
def suggest_seats(
    project_id: int = Query(..., description="Project ID to base proximity scoring on"),
    count: int = Query(5, ge=1, le=20),
    service: SeatAllocationService = Depends(get_service),
):
    seats = service.suggest_seats(project_id=project_id, count=count)
    return [_seat_response(s, service) for s in seats]


@router.get(
    "/{seat_id}",
    response_model=SeatResponse,
    summary="Get seat details including current occupant",
)
def get_seat(
    seat_id: int,
    service: SeatAllocationService = Depends(get_service),
):
    seat = service.seat_repo.get(seat_id)
    if not seat:
        raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found.")
    return _seat_response(seat, service)


@router.put(
    "/{seat_id}",
    response_model=SeatResponse,
    summary="Update seat details or status",
)
def update_seat(
    seat_id: int,
    data: SeatUpdate,
    service: SeatAllocationService = Depends(get_service),
):
    seat = service.seat_repo.get(seat_id)
    if not seat:
        raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found.")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(seat, field, value)
    updated = service.seat_repo.update(seat)
    return _seat_response(updated, service)


@router.post(
    "/allocate",
    response_model=SeatAllocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate a seat to an employee",
)
def allocate_seat(
    request: AllocateRequest,
    service: SeatAllocationService = Depends(get_service),
):
    """
    Allocate a seat to an employee.
    - If **seat_id** is provided, that specific seat is assigned (must be available).
    - If **seat_id** is omitted, the system auto-assigns the best seat using proximity scoring.
    - Raises 409 if employee already has a seat or seat is already occupied.
    - Raises 403 if seat is reserved or under maintenance.
    """
    return service.allocate_seat(request)


@router.post(
    "/release",
    summary="Release an employee's current seat",
)
def release_seat(
    request: ReleaseRequest,
    service: SeatAllocationService = Depends(get_service),
):
    """
    Release a seat. The seat status returns to 'available'.
    Raises 400 if the employee has no active allocation.
    """
    return service.release_seat(request)


# ── Helper ───────────────────────────────────────────────────────────────────

def _seat_response(seat, service: SeatAllocationService) -> SeatResponse:
    from ..schemas.seat import AllocationSummary
    active = service.seat_repo.get_active_allocation_for_seat(seat.id)
    alloc_summary = None
    if active:
        emp = service.emp_repo.get(active.employee_id)
        proj = service.proj_repo.get(active.project_id) if active.project_id else None
        alloc_summary = AllocationSummary(
            id=active.id,
            employee_id=active.employee_id,
            employee_name=emp.name if emp else None,
            employee_code=emp.employee_code if emp else None,
            project_id=active.project_id,
            project_name=proj.name if proj else None,
            allocation_date=active.allocation_date,
            allocation_status=active.allocation_status,
        )
    return SeatResponse(
        id=seat.id,
        floor=seat.floor,
        zone=seat.zone,
        bay=seat.bay,
        seat_number=seat.seat_number,
        status=seat.status,
        created_at=seat.created_at,
        current_allocation=alloc_summary,
    )
