"""
EmployeeService — Single Responsibility: employee business logic only.
Depends on repository abstractions (Dependency Inversion Principle).
"""
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..repositories.employee_repository import EmployeeRepository
from ..repositories.project_repository import ProjectRepository
from ..models.employee import Employee, EmployeeStatus
from ..schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse, SeatInfo


class EmployeeService:

    def __init__(self, db: Session):
        self.repo = EmployeeRepository(db)
        self.project_repo = ProjectRepository(db)
        self.db = db

    # ── Create ───────────────────────────────────────────────────────────────

    def create_employee(self, data: EmployeeCreate) -> Employee:
        # Business Rule 6: Duplicate email not allowed
        if self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Employee with email '{data.email}' already exists.",
            )

        # Validate project if provided
        if data.project_id:
            project = self.project_repo.get(data.project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project with id {data.project_id} not found.",
                )

        # Auto-generate employee code if not provided
        employee_code = (data.employee_code or self.repo.generate_next_code()).upper()

        # Ensure code is unique
        if self.repo.get_by_code(employee_code):
            employee_code = self.repo.generate_next_code()

        employee = Employee(
            employee_code=employee_code,
            name=data.name,
            email=data.email.lower(),
            department=data.department,
            role=data.role,
            joining_date=data.joining_date,
            status=data.status,
            project_id=data.project_id,
        )
        return self.repo.create(employee)

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_employee(self, employee_id: int) -> EmployeeResponse:
        emp = self.repo.get_with_details(employee_id)
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {employee_id} not found.",
            )
        return self._to_response(emp)

    def list_employees(
        self,
        query: Optional[str] = None,
        project_id: Optional[int] = None,
        status: Optional[EmployeeStatus] = None,
        department: Optional[str] = None,
        has_seat: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        skip = (page - 1) * page_size
        employees, total = self.repo.search(
            query=query,
            project_id=project_id,
            status=status,
            department=department,
            has_seat=has_seat,
            skip=skip,
            limit=page_size,
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "employees": [self._to_response(e) for e in employees],
        }

    # ── Update ───────────────────────────────────────────────────────────────

    def update_employee(self, employee_id: int, data: EmployeeUpdate) -> EmployeeResponse:
        emp = self.repo.get(employee_id)
        if not emp:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found.")

        if data.email and data.email != emp.email:
            existing = self.repo.get_by_email(data.email)
            if existing and existing.id != employee_id:
                raise HTTPException(
                    status_code=422,
                    detail=f"Email '{data.email}' is already in use.",
                )

        if data.project_id is not None:
            project = self.project_repo.get(data.project_id)
            if not project:
                raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(emp, field, value)

        updated = self.repo.update(emp)
        return self._to_response(updated)

    # ── Delete (soft deactivate) ─────────────────────────────────────────────

    def deactivate_employee(self, employee_id: int) -> dict:
        emp = self.repo.get(employee_id)
        if not emp:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found.")

        emp.status = EmployeeStatus.INACTIVE
        self.repo.update(emp)
        return {"message": f"Employee {employee_id} deactivated successfully."}

    # ── Helper ───────────────────────────────────────────────────────────────

    def _to_response(self, emp: Employee) -> EmployeeResponse:
        """Build EmployeeResponse including active seat info."""
        active_alloc = self.repo.get_active_allocation(emp.id)
        seat_info = None
        if active_alloc and active_alloc.seat:
            seat = active_alloc.seat
            seat_info = SeatInfo(
                seat_id=seat.id,
                floor=seat.floor,
                zone=seat.zone,
                bay=seat.bay,
                seat_number=seat.seat_number,
                allocation_date=active_alloc.allocation_date,
            )

        return EmployeeResponse(
            id=emp.id,
            employee_code=emp.employee_code,
            name=emp.name,
            email=emp.email,
            department=emp.department,
            role=emp.role,
            joining_date=emp.joining_date,
            status=emp.status,
            project_id=emp.project_id,
            created_at=emp.created_at,
            project=emp.project,
            seat=seat_info,
        )
