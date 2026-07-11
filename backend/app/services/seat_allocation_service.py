"""
SeatAllocationService — Single Responsibility: all seat allocation business logic.

Algorithm: Proximity-Based Greedy with Zone Fallback
  1. If specific seat_id given → validate and allocate directly
  2. Otherwise → score available seats by project proximity
     - +3 same zone as team, +2 same floor as team
  3. Fallback: any available seat if no team seated yet
  4. Guard: SELECT FOR UPDATE prevents concurrent double-booking (PostgreSQL)

Business Rules enforced here:
  - Rule 1: One employee → one active seat
  - Rule 2: One seat → one active employee  
  - Rule 4: Reserved seats cannot be allocated unless status changed
  - Rule 3: Released seats become available again
"""
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..repositories.seat_repository import SeatRepository
from ..repositories.employee_repository import EmployeeRepository
from ..repositories.project_repository import ProjectRepository
from ..models.seat import Seat, SeatStatus
from ..models.seat_allocation import SeatAllocation, AllocationStatus
from ..schemas.seat import AllocateRequest, ReleaseRequest, SeatAllocationResponse, SeatResponse


class SeatAllocationService:

    def __init__(self, db: Session):
        self.seat_repo = SeatRepository(db)
        self.emp_repo = EmployeeRepository(db)
        self.proj_repo = ProjectRepository(db)
        self.db = db

    # ── Allocate ─────────────────────────────────────────────────────────────

    def allocate_seat(self, request: AllocateRequest) -> SeatAllocationResponse:
        # Validate employee exists
        employee = self.emp_repo.get(request.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail=f"Employee {request.employee_id} not found.")

        # Business Rule 1: Employee already has active seat
        existing_alloc = self.seat_repo.get_active_allocation_for_employee(request.employee_id)
        if existing_alloc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Employee {request.employee_id} already has an active seat allocation "
                    f"(seat_id={existing_alloc.seat_id}). Release it first."
                ),
            )

        project_id = request.project_id or employee.project_id

        if request.seat_id:
            seat = self._validate_specific_seat(request.seat_id)
        else:
            seat = self._find_best_seat(project_id)

        allocation = self.seat_repo.create_allocation(
            employee_id=request.employee_id,
            seat_id=seat.id,
            project_id=project_id,
        )
        return self._to_response(allocation)

    def _validate_specific_seat(self, seat_id: int) -> Seat:
        seat = self.seat_repo.get(seat_id)
        if not seat:
            raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found.")

        # Business Rule 4: Cannot allocate reserved seats
        if seat.status == SeatStatus.RESERVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Seat {seat_id} is RESERVED and cannot be allocated. Change status first.",
            )
        if seat.status == SeatStatus.MAINTENANCE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Seat {seat_id} is under MAINTENANCE and cannot be allocated.",
            )

        # Business Rule 2: Seat already occupied
        active = self.seat_repo.get_active_allocation_for_seat(seat_id)
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Seat {seat_id} is already occupied by employee {active.employee_id}.",
            )
        return seat

    def _find_best_seat(self, project_id: Optional[int]) -> Seat:
        if project_id:
            candidates = self.seat_repo.find_seats_near_project(project_id, limit=1)
        else:
            candidates = self.seat_repo.get_available()[:1]

        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No available seats found. All seats are occupied, reserved, or under maintenance.",
            )
        return candidates[0]

    # ── Release ──────────────────────────────────────────────────────────────

    def release_seat(self, request: ReleaseRequest) -> dict:
        employee = self.emp_repo.get(request.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail=f"Employee {request.employee_id} not found.")

        allocation = self.seat_repo.get_active_allocation_for_employee(request.employee_id)
        if not allocation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee {request.employee_id} has no active seat allocation to release.",
            )

        self.seat_repo.release_allocation(allocation)
        return {
            "message": f"Seat {allocation.seat_id} released successfully for employee {request.employee_id}.",
            "seat_id": allocation.seat_id,
            "employee_id": request.employee_id,
        }

    # ── Seat CRUD ────────────────────────────────────────────────────────────

    def create_seat(self, floor: int, zone: str, bay: str, seat_number: str, seat_status: SeatStatus = SeatStatus.AVAILABLE) -> Seat:
        # Business Rule 7: Duplicate seat on same floor/zone not allowed (also enforced by DB constraint)
        existing = self.seat_repo.get_by_location(floor, zone, bay, seat_number)
        if existing:
            raise HTTPException(
                status_code=422,
                detail=f"Seat {seat_number} on Floor {floor}, Zone {zone}, Bay {bay} already exists.",
            )
        seat = Seat(floor=floor, zone=zone, bay=bay, seat_number=seat_number, status=seat_status)
        return self.seat_repo.create(seat)

    def list_seats(
        self,
        floor: Optional[int] = None,
        zone: Optional[str] = None,
        seat_status: Optional[SeatStatus] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        skip = (page - 1) * page_size
        seats, total = self.seat_repo.search(
            floor=floor, zone=zone, status=seat_status, skip=skip, limit=page_size
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "seats": seats,
        }

    def get_available_seats(self, floor: Optional[int] = None, zone: Optional[str] = None) -> List[Seat]:
        return self.seat_repo.get_available(floor=floor, zone=zone)

    def suggest_seats(self, project_id: int, count: int = 5) -> List[Seat]:
        """Return top N suggested seats for a new joiner in a project."""
        return self.seat_repo.find_seats_near_project(project_id, limit=count)

    # ── Helper ───────────────────────────────────────────────────────────────

    def _to_response(self, allocation: SeatAllocation) -> SeatAllocationResponse:
        seat = self.seat_repo.get(allocation.seat_id)
        seat_resp = None
        if seat:
            seat_resp = SeatResponse(
                id=seat.id,
                floor=seat.floor,
                zone=seat.zone,
                bay=seat.bay,
                seat_number=seat.seat_number,
                status=seat.status,
                created_at=seat.created_at,
            )
        return SeatAllocationResponse(
            id=allocation.id,
            employee_id=allocation.employee_id,
            seat_id=allocation.seat_id,
            project_id=allocation.project_id,
            allocation_status=allocation.allocation_status,
            allocation_date=allocation.allocation_date,
            released_date=allocation.released_date,
            seat=seat_resp,
        )
