"""
TDD: Seat allocation tests.
FALSE/EDGE CASES FIRST — core business rules tested before happy path.

Business Rules Under Test:
  Rule 1: One employee → one active seat
  Rule 2: One seat → one active employee
  Rule 3: Released seat → becomes available
  Rule 4: Reserved seat → cannot be allocated
  Rule 7: Duplicate seat location → not allowed
"""
import pytest
from datetime import date


# ═══════════════════════════════════════════════════════════════
# FALSE / EDGE CASES — written before implementation
# ═══════════════════════════════════════════════════════════════

class TestAllocationEdgeCases:

    def test_allocate_already_occupied_seat_returns_409(
        self, client, sample_project, occupied_seat
    ):
        """Rule 2: Seat already occupied → 409 Conflict."""
        seat, _ = occupied_seat
        # Create a second employee
        e2 = client.post("/employees", json={
            "name": "Second Employee",
            "email": "second@ethara.ai",
            "project_id": sample_project.id,
        }).json()
        r = client.post("/seats/allocate", json={
            "employee_id": e2["id"],
            "seat_id": seat.id,
        })
        assert r.status_code == 409
        assert "already occupied" in r.json()["detail"].lower()

    def test_allocate_reserved_seat_returns_403(
        self, client, sample_project, reserved_seat, sample_employee
    ):
        """Rule 4: Reserved seat cannot be allocated."""
        r = client.post("/seats/allocate", json={
            "employee_id": sample_employee.id,
            "seat_id": reserved_seat.id,
        })
        assert r.status_code == 403
        assert "reserved" in r.json()["detail"].lower()

    def test_employee_cannot_have_two_active_seats(
        self, client, sample_project, sample_employee, sample_seat, db_session
    ):
        """Rule 1: Employee already has a seat → 409 on second allocation."""
        from app.models.seat import Seat, SeatStatus
        seat2 = Seat(floor=3, zone="C", bay="Bay-1", seat_number="C1-01", status=SeatStatus.AVAILABLE)
        db_session.add(seat2)
        db_session.commit()
        db_session.refresh(seat2)

        # First allocation
        r1 = client.post("/seats/allocate", json={
            "employee_id": sample_employee.id,
            "seat_id": sample_seat.id,
        })
        assert r1.status_code == 201

        # Second allocation attempt
        r2 = client.post("/seats/allocate", json={
            "employee_id": sample_employee.id,
            "seat_id": seat2.id,
        })
        assert r2.status_code == 409
        assert "already has" in r2.json()["detail"].lower()

    def test_release_already_available_seat_returns_400(
        self, client, sample_employee
    ):
        """Edge: Employee has no seat → release returns 400."""
        r = client.post("/seats/release", json={"employee_id": sample_employee.id})
        assert r.status_code == 400
        assert "no active seat" in r.json()["detail"].lower()

    def test_allocate_to_nonexistent_employee_returns_404(self, client, sample_seat):
        r = client.post("/seats/allocate", json={
            "employee_id": 99999,
            "seat_id": sample_seat.id,
        })
        assert r.status_code == 404

    def test_allocate_nonexistent_seat_returns_404(self, client, sample_employee):
        r = client.post("/seats/allocate", json={
            "employee_id": sample_employee.id,
            "seat_id": 99999,
        })
        assert r.status_code == 404

    def test_create_duplicate_seat_location_returns_422(self, client, sample_seat):
        """Rule 7: Duplicate floor/zone/bay/seat_number not allowed."""
        r = client.post("/seats", json={
            "floor": 2,
            "zone": "B",
            "bay": "Bay-4",
            "seat_number": "B4-23",
        })
        assert r.status_code == 422
        assert "already exists" in r.json()["detail"].lower()

    def test_allocate_maintenance_seat_returns_403(self, client, sample_employee, db_session):
        """Edge: Maintenance seat cannot be allocated."""
        from app.models.seat import Seat, SeatStatus
        maint = Seat(floor=4, zone="D", bay="Bay-2", seat_number="D2-10", status=SeatStatus.MAINTENANCE)
        db_session.add(maint)
        db_session.commit()
        db_session.refresh(maint)

        r = client.post("/seats/allocate", json={
            "employee_id": sample_employee.id,
            "seat_id": maint.id,
        })
        assert r.status_code == 403
        assert "maintenance" in r.json()["detail"].lower()

    def test_no_available_seats_returns_404(self, client, sample_project, db_session):
        """Edge: Auto-assign when no available seats exist."""
        from app.models.employee import Employee, EmployeeStatus
        emp = Employee(
            employee_code="ETH-99999",
            name="Lonely Employee",
            email="lonely@ethara.ai",
            department="HR",
            role="Manager",
            joining_date=date.today(),
            status=EmployeeStatus.ACTIVE,
            project_id=sample_project.id,
        )
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(emp)

        # No seats exist → auto-assign should 404
        r = client.post("/seats/allocate", json={"employee_id": emp.id})
        assert r.status_code == 404
        assert "no available seats" in r.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════
# HAPPY PATH
# ═══════════════════════════════════════════════════════════════

class TestAllocationHappyPath:

    def test_allocate_specific_seat_success(self, client, sample_employee, sample_seat):
        r = client.post("/seats/allocate", json={
            "employee_id": sample_employee.id,
            "seat_id": sample_seat.id,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["employee_id"] == sample_employee.id
        assert data["seat_id"] == sample_seat.id
        assert data["allocation_status"] == "active"

    def test_seat_status_becomes_occupied_after_allocation(
        self, client, sample_employee, sample_seat
    ):
        """Rule 2: Seat status must update to 'occupied' after allocation."""
        client.post("/seats/allocate", json={
            "employee_id": sample_employee.id,
            "seat_id": sample_seat.id,
        })
        r = client.get(f"/seats/{sample_seat.id}")
        assert r.json()["status"] == "occupied"

    def test_release_seat_returns_to_available(self, client, sample_employee, occupied_seat):
        """Rule 3: Released seat becomes available again."""
        seat, _ = occupied_seat
        r = client.post("/seats/release", json={"employee_id": sample_employee.id})
        assert r.status_code == 200

        r2 = client.get(f"/seats/{seat.id}")
        assert r2.json()["status"] == "available"

    def test_employee_seat_info_cleared_after_release(
        self, client, sample_employee, occupied_seat
    ):
        client.post("/seats/release", json={"employee_id": sample_employee.id})
        r = client.get(f"/employees/{sample_employee.id}")
        assert r.json()["seat"] is None

    def test_list_available_seats(self, client, sample_seat):
        r = client.get("/seats/available")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert sample_seat.id in ids

    def test_filter_seats_by_floor(self, client, sample_seat):
        r = client.get("/seats?floor=2")
        assert r.status_code == 200
        floors = [s["floor"] for s in r.json()["seats"]]
        assert all(f == 2 for f in floors)

    def test_create_seat_success(self, client):
        r = client.post("/seats", json={
            "floor": 5, "zone": "J", "bay": "Bay-10", "seat_number": "J10-99"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "available"
        assert data["floor"] == 5

    def test_suggest_seats_returns_list(self, client, sample_project, sample_seat):
        r = client.get(f"/seats/suggest?project_id={sample_project.id}&count=3")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
