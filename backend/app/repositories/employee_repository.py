"""
EmployeeRepository — Single Responsibility: all employee DB queries live here.
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from .base import BaseRepository
from ..models.employee import Employee, EmployeeStatus
from ..models.seat_allocation import SeatAllocation, AllocationStatus


class EmployeeRepository(BaseRepository[Employee]):

    def __init__(self, db: Session):
        super().__init__(Employee, db)

    # ── Lookup helpers ──────────────────────────────────────────────────────

    def get_by_email(self, email: str) -> Optional[Employee]:
        return self.db.query(Employee).filter(
            func.lower(Employee.email) == email.lower()
        ).first()

    def get_by_code(self, employee_code: str) -> Optional[Employee]:
        return self.db.query(Employee).filter(
            Employee.employee_code == employee_code.upper()
        ).first()

    def get_with_details(self, employee_id: int) -> Optional[Employee]:
        """Eager-load project and active allocation."""
        return (
            self.db.query(Employee)
            .options(joinedload(Employee.project))
            .filter(Employee.id == employee_id)
            .first()
        )

    # ── Search & filter ─────────────────────────────────────────────────────

    def search(
        self,
        query: Optional[str] = None,
        project_id: Optional[int] = None,
        status: Optional[EmployeeStatus] = None,
        department: Optional[str] = None,
        has_seat: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Employee], int]:
        q = self.db.query(Employee).options(joinedload(Employee.project))

        if query:
            q = q.filter(
                or_(
                    Employee.name.ilike(f"%{query}%"),
                    Employee.email.ilike(f"%{query}%"),
                    Employee.employee_code.ilike(f"%{query}%"),
                )
            )
        if project_id:
            q = q.filter(Employee.project_id == project_id)
        if status:
            q = q.filter(Employee.status == status)
        if department:
            q = q.filter(Employee.department.ilike(f"%{department}%"))

        if has_seat is True:
            q = q.join(SeatAllocation, (
                SeatAllocation.employee_id == Employee.id) &
                (SeatAllocation.allocation_status == AllocationStatus.ACTIVE)
            )
        elif has_seat is False:
            subq = (
                self.db.query(SeatAllocation.employee_id)
                .filter(SeatAllocation.allocation_status == AllocationStatus.ACTIVE)
                .subquery()
            )
            q = q.filter(~Employee.id.in_(subq))

        total = q.count()
        employees = q.order_by(Employee.name).offset(skip).limit(limit).all()
        return employees, total

    def get_by_project(self, project_id: int) -> List[Employee]:
        return (
            self.db.query(Employee)
            .filter(Employee.project_id == project_id, Employee.status == EmployeeStatus.ACTIVE)
            .all()
        )

    def count_pending_allocation(self) -> int:
        """Active employees with no active seat allocation."""
        subq = (
            self.db.query(SeatAllocation.employee_id)
            .filter(SeatAllocation.allocation_status == AllocationStatus.ACTIVE)
            .subquery()
        )
        return (
            self.db.query(Employee)
            .filter(
                Employee.status == EmployeeStatus.ACTIVE,
                ~Employee.id.in_(subq)
            )
            .count()
        )

    def generate_next_code(self) -> str:
        """Generate ETH-XXXXX employee code."""
        last = (
            self.db.query(Employee)
            .order_by(Employee.id.desc())
            .first()
        )
        next_id = (last.id + 1) if last else 1
        return f"ETH-{next_id:05d}"

    def get_active_allocation(self, employee_id: int) -> Optional[SeatAllocation]:
        return (
            self.db.query(SeatAllocation)
            .filter(
                SeatAllocation.employee_id == employee_id,
                SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
            )
            .first()
        )
