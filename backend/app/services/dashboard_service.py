"""
DashboardService — Single Responsibility: aggregations for the dashboard.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..repositories.seat_repository import SeatRepository
from ..repositories.employee_repository import EmployeeRepository
from ..repositories.project_repository import ProjectRepository
from ..models.employee import Employee, EmployeeStatus
from ..schemas.ai_assistant import DashboardSummary, ProjectUtilization, FloorUtilization


class DashboardService:

    def __init__(self, db: Session):
        self.seat_repo = SeatRepository(db)
        self.emp_repo = EmployeeRepository(db)
        self.proj_repo = ProjectRepository(db)

    def get_summary(self) -> DashboardSummary:
        total_emp = self.emp_repo.count()
        active_emp = (
            self.emp_repo.db.query(func.count(Employee.id))
            .filter(Employee.status == EmployeeStatus.ACTIVE)
            .scalar() or 0
        )
        pending = self.emp_repo.count_pending_allocation()
        seat_counts = self.seat_repo.count_by_status()

        total_seats = sum(seat_counts.values())
        occupied = seat_counts.get("occupied", 0)
        available = seat_counts.get("available", 0)
        reserved = seat_counts.get("reserved", 0)
        maintenance = seat_counts.get("maintenance", 0)

        return DashboardSummary(
            total_employees=total_emp,
            active_employees=active_emp,
            total_seats=total_seats,
            occupied_seats=occupied,
            available_seats=available,
            reserved_seats=reserved,
            maintenance_seats=maintenance,
            pending_allocation=pending,
            utilization_rate=round(occupied / total_seats * 100, 1) if total_seats else 0.0,
        )

    def get_project_utilization(self) -> list[ProjectUtilization]:
        rows = self.proj_repo.get_utilization()
        return [ProjectUtilization(**r) for r in rows]

    def get_floor_utilization(self) -> list[FloorUtilization]:
        rows = self.seat_repo.floor_utilization()
        return [FloorUtilization(**r) for r in rows]
