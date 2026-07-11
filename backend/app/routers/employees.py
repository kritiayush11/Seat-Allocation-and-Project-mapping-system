"""
Employee router — all /employees endpoints.
Single Responsibility: HTTP layer only. Business logic lives in EmployeeService.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.employee_service import EmployeeService
from ..schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse
from ..models.employee import EmployeeStatus
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
    dependencies=[Depends(get_current_user)]
)


def get_service(db: Session = Depends(get_db)) -> EmployeeService:
    return EmployeeService(db)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new employee",
)
def create_employee(
    data: EmployeeCreate,
    service: EmployeeService = Depends(get_service),
):
    """
    Create a new employee record.
    - **email** must be unique across all employees.
    - **employee_code** is auto-generated (ETH-XXXXX) if not provided.
    - **project_id** must reference an existing project.
    """
    return service.create_employee(data)


@router.get(
    "",
    response_model=EmployeeListResponse,
    summary="List employees with optional filters",
)
def list_employees(
    q: Optional[str] = Query(None, description="Search by name, email, or employee code"),
    project_id: Optional[int] = Query(None),
    emp_status: Optional[EmployeeStatus] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    has_seat: Optional[bool] = Query(None, description="Filter by seat allocation status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: EmployeeService = Depends(get_service),
):
    return service.list_employees(
        query=q,
        project_id=project_id,
        status=emp_status,
        department=department,
        has_seat=has_seat,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get employee details including seat and project",
)
def get_employee(
    employee_id: int,
    service: EmployeeService = Depends(get_service),
):
    return service.get_employee(employee_id)


@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee details",
)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    service: EmployeeService = Depends(get_service),
):
    return service.update_employee(employee_id, data)


@router.delete(
    "/{employee_id}",
    summary="Deactivate employee (soft delete)",
    status_code=status.HTTP_200_OK,
)
def deactivate_employee(
    employee_id: int,
    service: EmployeeService = Depends(get_service),
):
    return service.deactivate_employee(employee_id)
