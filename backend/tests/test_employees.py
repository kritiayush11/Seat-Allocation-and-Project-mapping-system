"""
TDD: Employee endpoint tests.
FALSE/EDGE CASES FIRST — written before implementation to drive design.
"""
import pytest
from datetime import date


# ═══════════════════════════════════════════════════════════════
# FALSE / EDGE CASES (written first — Red phase)
# ═══════════════════════════════════════════════════════════════

class TestEmployeeCreateEdgeCases:
    """Business Rule 6: Duplicate email not allowed."""

    def test_duplicate_email_returns_422(self, client, sample_project):
        """EDGE: Creating two employees with the same email must fail."""
        payload = {
            "name": "Amit Kumar",
            "email": "amit@ethara.ai",
            "project_id": sample_project.id,
            "joining_date": "2024-01-15",
        }
        r1 = client.post("/employees", json=payload)
        assert r1.status_code == 201

        r2 = client.post("/employees", json=payload)
        assert r2.status_code == 422
        assert "already exists" in r2.json()["detail"].lower()

    def test_invalid_email_format_returns_422(self, client, sample_project):
        """EDGE: Malformed email must be rejected by Pydantic."""
        payload = {
            "name": "Bad Email",
            "email": "not-an-email",
            "project_id": sample_project.id,
        }
        r = client.post("/employees", json=payload)
        assert r.status_code == 422

    def test_nonexistent_project_returns_404(self, client):
        """EDGE: Assigning employee to non-existent project must fail."""
        payload = {
            "name": "Ghost Project Emp",
            "email": "ghost@ethara.ai",
            "project_id": 99999,
        }
        r = client.post("/employees", json=payload)
        assert r.status_code == 404
        assert "project" in r.json()["detail"].lower()

    def test_missing_name_returns_422(self, client):
        """EDGE: Name is required."""
        r = client.post("/employees", json={"email": "noname@ethara.ai"})
        assert r.status_code == 422

    def test_missing_email_returns_422(self, client):
        """EDGE: Email is required."""
        r = client.post("/employees", json={"name": "No Email"})
        assert r.status_code == 422


class TestEmployeeReadEdgeCases:

    def test_get_nonexistent_employee_returns_404(self, client):
        """EDGE: GET /employees/99999 must return 404."""
        r = client.get("/employees/99999")
        assert r.status_code == 404

    def test_get_employee_with_zero_id_returns_422_or_404(self, client):
        """EDGE: ID 0 is not a valid employee."""
        r = client.get("/employees/0")
        assert r.status_code in (404, 422)


class TestEmployeeUpdateEdgeCases:

    def test_update_email_to_existing_email_returns_422(self, client, sample_project):
        """EDGE: Cannot update email to one already taken by another employee."""
        e1 = client.post("/employees", json={
            "name": "Employee One", "email": "one@ethara.ai",
            "project_id": sample_project.id,
        }).json()
        e2 = client.post("/employees", json={
            "name": "Employee Two", "email": "two@ethara.ai",
            "project_id": sample_project.id,
        }).json()

        r = client.put(f"/employees/{e2['id']}", json={"email": "one@ethara.ai"})
        assert r.status_code == 422

    def test_update_nonexistent_employee_returns_404(self, client):
        r = client.put("/employees/99999", json={"name": "Ghost"})
        assert r.status_code == 404


class TestEmployeeDeleteEdgeCases:

    def test_deactivate_nonexistent_employee_returns_404(self, client):
        r = client.delete("/employees/99999")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════
# HAPPY PATH (Green phase)
# ═══════════════════════════════════════════════════════════════

class TestEmployeeHappyPath:

    def test_create_employee_success(self, client, sample_project):
        payload = {
            "name": "Sara Khan",
            "email": "sara@ethara.ai",
            "department": "Engineering",
            "role": "Software Engineer",
            "project_id": sample_project.id,
            "joining_date": "2024-03-01",
        }
        r = client.post("/employees", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Sara Khan"
        assert data["email"] == "sara@ethara.ai"
        assert data["employee_code"].startswith("ETH-")
        assert data["project"]["id"] == sample_project.id

    def test_employee_code_auto_generated(self, client, sample_project):
        r = client.post("/employees", json={
            "name": "Auto Code", "email": "autocode@ethara.ai",
            "project_id": sample_project.id,
        })
        assert r.status_code == 201
        assert r.json()["employee_code"].startswith("ETH-")

    def test_list_employees_pagination(self, client, sample_project):
        for i in range(5):
            client.post("/employees", json={
                "name": f"User {i}", "email": f"user{i}@ethara.ai",
                "project_id": sample_project.id,
            })
        r = client.get("/employees?page=1&page_size=3")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 5
        assert len(data["employees"]) <= 3

    def test_search_by_name(self, client, sample_project):
        client.post("/employees", json={
            "name": "Unique Searchable Name", "email": "uniquesearch@ethara.ai",
            "project_id": sample_project.id,
        })
        r = client.get("/employees?q=Unique+Searchable")
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        assert "Unique Searchable Name" in r.json()["employees"][0]["name"]

    def test_get_employee_returns_seat_info(self, client, sample_employee, occupied_seat):
        r = client.get(f"/employees/{sample_employee.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["seat"] is not None
        assert data["seat"]["floor"] == 2

    def test_deactivate_employee(self, client, sample_employee):
        r = client.delete(f"/employees/{sample_employee.id}")
        assert r.status_code == 200

        r2 = client.get(f"/employees/{sample_employee.id}")
        assert r2.json()["status"] == "inactive"
