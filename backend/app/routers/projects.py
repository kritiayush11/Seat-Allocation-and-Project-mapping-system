"""
Projects router — all /projects endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories.project_repository import ProjectRepository
from ..repositories.employee_repository import EmployeeRepository
from ..services.employee_service import EmployeeService
from ..schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from ..schemas.employee import EmployeeResponse
from ..models.project import Project, ProjectStatus
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    dependencies=[Depends(get_current_user)]
)


def get_project_repo(db: Session = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    data: ProjectCreate,
    repo: ProjectRepository = Depends(get_project_repo),
):
    existing = repo.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=422, detail=f"Project '{data.name}' already exists.")

    project = Project(
        name=data.name,
        description=data.description,
        manager_name=data.manager_name,
        status=data.status,
    )
    created = repo.create(project)
    return _project_response(created, repo)


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List all projects",
)
def list_projects(
    active_only: bool = True,
    repo: ProjectRepository = Depends(get_project_repo),
):
    if active_only:
        projects = repo.get_all_active()
    else:
        projects = repo.get_all()
    return [_project_response(p, repo) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
)
def get_project(
    project_id: int,
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")
    return _project_response(project, repo)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    if data.name and data.name != project.name:
        existing = repo.get_by_name(data.name)
        if existing:
            raise HTTPException(status_code=422, detail=f"Project name '{data.name}' already in use.")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    updated = repo.update(project)
    return _project_response(updated, repo)


@router.get(
    "/{project_id}/employees",
    response_model=List[EmployeeResponse],
    summary="List all employees in a project",
)
def get_project_employees(
    project_id: int,
    db: Session = Depends(get_db),
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    service = EmployeeService(db)
    result = service.list_employees(project_id=project_id, page_size=200)
    return result["employees"]


# ── Helper ───────────────────────────────────────────────────────────────────

def _project_response(project: Project, repo: ProjectRepository) -> ProjectResponse:
    from sqlalchemy import func
    from ..models.employee import Employee
    from ..models.seat_allocation import SeatAllocation, AllocationStatus

    emp_count = (
        repo.db.query(func.count(Employee.id))
        .filter(Employee.project_id == project.id)
        .scalar() or 0
    )
    occ_count = (
        repo.db.query(func.count(SeatAllocation.id))
        .filter(
            SeatAllocation.project_id == project.id,
            SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
        )
        .scalar() or 0
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        manager_name=project.manager_name,
        status=project.status,
        created_at=project.created_at,
        employee_count=emp_count,
        occupied_seats=occ_count,
    )
