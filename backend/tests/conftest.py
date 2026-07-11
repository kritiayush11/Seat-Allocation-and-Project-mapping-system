"""
Pytest fixtures — shared test infrastructure.
Uses a file-based SQLite test database per test function for isolation.
SQLite :memory: creates a separate DB per connection, which breaks
the test client pattern — a named temp file ensures all connections
share the same schema.
"""
import os
import pytest
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.project import Project, ProjectStatus
from app.models.employee import Employee, EmployeeStatus
from app.models.seat import Seat, SeatStatus
from app.models.seat_allocation import SeatAllocation, AllocationStatus
from datetime import date


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Reset slowapi in-memory counters before every test so rate limit state
    from one test never bleeds into another.
    """
    try:
        from app.limiter import limiter
        limiter.reset()
    except Exception:
        pass
    yield


@pytest.fixture(scope="function")
def db_engine():
    # Use a temp file so all connections within a test see the same DB
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    yield session
    session.close()


from app.dependencies import get_current_user
from app.models.user import User


def mock_get_current_user():
    return User(id=999, username="test_admin", email="test_admin@ethara.ai", is_admin=True)


@pytest.fixture(scope="function")
def client(db_engine, db_session):
    """Test client with DB dependency overridden.
    The override yields the SAME db_session used by seed fixtures,
    so data created by fixtures is immediately visible to route handlers.
    """
    def override_get_db():
        # Yield the shared session so fixture data is visible
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_project(db_session) -> Project:
    project = Project(name="TestProject", description="Test", status=ProjectStatus.ACTIVE)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_employee(db_session, sample_project) -> Employee:
    emp = Employee(
        employee_code="ETH-00001",
        name="Test User",
        email="test@ethara.ai",
        department="Engineering",
        role="Engineer",
        joining_date=date(2024, 1, 1),
        status=EmployeeStatus.ACTIVE,
        project_id=sample_project.id,
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)
    return emp


@pytest.fixture
def sample_seat(db_session) -> Seat:
    seat = Seat(floor=2, zone="B", bay="Bay-4", seat_number="B4-23", status=SeatStatus.AVAILABLE)
    db_session.add(seat)
    db_session.commit()
    db_session.refresh(seat)
    return seat


@pytest.fixture
def reserved_seat(db_session) -> Seat:
    seat = Seat(floor=1, zone="A", bay="Bay-1", seat_number="A1-01", status=SeatStatus.RESERVED)
    db_session.add(seat)
    db_session.commit()
    db_session.refresh(seat)
    return seat


@pytest.fixture
def occupied_seat(db_session, sample_employee, sample_seat) -> tuple[Seat, SeatAllocation]:
    """Returns a seat that is already occupied by sample_employee."""
    alloc = SeatAllocation(
        employee_id=sample_employee.id,
        seat_id=sample_seat.id,
        project_id=sample_employee.project_id,
        allocation_status=AllocationStatus.ACTIVE,
        allocation_date=date.today(),
    )
    sample_seat.status = SeatStatus.OCCUPIED
    db_session.add(alloc)
    db_session.add(sample_seat)
    db_session.commit()
    db_session.refresh(alloc)
    db_session.refresh(sample_seat)
    return sample_seat, alloc
