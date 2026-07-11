"""
TDD: Project endpoint tests.
"""
import pytest


class TestProjectEdgeCases:

    def test_duplicate_project_name_returns_422(self, client):
        client.post("/projects", json={"name": "UniqueProject"})
        r = client.post("/projects", json={"name": "UniqueProject"})
        assert r.status_code == 422
        assert "already exists" in r.json()["detail"].lower()

    def test_get_nonexistent_project_returns_404(self, client):
        r = client.get("/projects/99999")
        assert r.status_code == 404

    def test_empty_project_name_returns_422(self, client):
        r = client.post("/projects", json={"name": ""})
        assert r.status_code == 422

    def test_update_to_existing_name_returns_422(self, client):
        client.post("/projects", json={"name": "Alpha"})
        beta = client.post("/projects", json={"name": "Beta"}).json()
        r = client.put(f"/projects/{beta['id']}", json={"name": "Alpha"})
        assert r.status_code == 422

    def test_get_employees_for_nonexistent_project_returns_404(self, client):
        r = client.get("/projects/99999/employees")
        assert r.status_code == 404


class TestProjectHappyPath:

    def test_create_project_success(self, client):
        r = client.post("/projects", json={
            "name": "Indigo",
            "description": "Core platform",
            "manager_name": "Arjun Sharma",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Indigo"
        assert data["status"] == "active"

    def test_list_projects_returns_only_active_by_default(self, client):
        client.post("/projects", json={"name": "ActiveProj"})
        archived = client.post("/projects", json={"name": "ArchivedProj"}).json()
        client.put(f"/projects/{archived['id']}", json={"status": "archived"})

        r = client.get("/projects")
        names = [p["name"] for p in r.json()]
        assert "ActiveProj" in names
        assert "ArchivedProj" not in names

    def test_project_employee_count_included(self, client, sample_project, sample_employee):
        r = client.get(f"/projects/{sample_project.id}")
        assert r.status_code == 200
        assert r.json()["employee_count"] >= 1

    def test_project_employees_endpoint(self, client, sample_project, sample_employee):
        r = client.get(f"/projects/{sample_project.id}/employees")
        assert r.status_code == 200
        assert len(r.json()) >= 1
        assert r.json()[0]["project_id"] == sample_project.id
