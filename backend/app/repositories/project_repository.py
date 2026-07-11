"""
ProjectRepository — Single Responsibility: all project DB queries.
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from .base import BaseRepository
from ..models.project import Project, ProjectStatus
from ..models.employee import Employee
from ..models.seat_allocation import SeatAllocation, AllocationStatus


class ProjectRepository(BaseRepository[Project]):

    def __init__(self, db: Session):
        super().__init__(Project, db)

    def search(
        self,
        query: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Project], int]:
        """Full-text search over project name and description."""
        from sqlalchemy import or_
        q = self.db.query(Project)
        if query:
            q = q.filter(
                or_(
                    Project.name.ilike(f"%{query}%"),
                    Project.description.ilike(f"%{query}%"),
                    Project.manager_name.ilike(f"%{query}%"),
                )
            )
        if status:
            q = q.filter(Project.status == status)
        total = q.count()
        projects = q.order_by(Project.name).offset(skip).limit(limit).all()
        return projects, total

    def get_by_name(self, name: str) -> Optional[Project]:
        return self.db.query(Project).filter(
            func.lower(Project.name) == name.lower()
        ).first()

    def get_all_active(self) -> List[Project]:
        return (
            self.db.query(Project)
            .filter(Project.status == ProjectStatus.ACTIVE)
            .order_by(Project.name)
            .all()
        )

    def get_utilization(self) -> List[dict]:
        """Returns per-project employee count and allocated seat count."""
        results = []
        projects = self.db.query(Project).filter(Project.status == ProjectStatus.ACTIVE).all()

        for project in projects:
            emp_count = (
                self.db.query(func.count(Employee.id))
                .filter(Employee.project_id == project.id)
                .scalar()
            )
            allocated = (
                self.db.query(func.count(SeatAllocation.id))
                .filter(
                    SeatAllocation.project_id == project.id,
                    SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
                )
                .scalar()
            )
            results.append({
                "project_id": project.id,
                "project_name": project.name,
                "total_employees": emp_count or 0,
                "allocated_seats": allocated or 0,
                "unallocated_employees": max(0, (emp_count or 0) - (allocated or 0)),
            })
        return results
