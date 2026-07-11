"""
TDD: Dashboard endpoint tests.
"""
import pytest


class TestDashboardEdgeCases:

    def test_summary_returns_zero_counts_on_empty_db(self, client):
        """Edge: Empty database should return all zeros, not crash."""
        r = client.get("/dashboard/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_employees"] == 0
        assert data["total_seats"] == 0
        assert data["occupied_seats"] == 0
        assert data["utilization_rate"] == 0.0

    def test_project_utilization_empty_db(self, client):
        """Edge: No projects → empty list, not error."""
        r = client.get("/dashboard/project-utilization")
        assert r.status_code == 200
        assert r.json() == []

    def test_floor_utilization_empty_db(self, client):
        """Edge: No seats → empty list, not error."""
        r = client.get("/dashboard/floor-utilization")
        assert r.status_code == 200
        assert r.json() == []


class TestDashboardHappyPath:

    def test_summary_reflects_allocation(
        self, client, sample_employee, occupied_seat
    ):
        r = client.get("/dashboard/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_employees"] >= 1
        # occupied_seat fixture creates 1 occupied seat
        assert data["occupied_seats"] >= 1
        assert data["total_seats"] >= 1
        assert 0.0 <= data["utilization_rate"] <= 100.0
        assert data["utilization_rate"] > 0.0

    def test_pending_allocation_count(self, client, sample_employee):
        """sample_employee has no seat → pending count should be ≥ 1."""
        r = client.get("/dashboard/summary")
        assert r.json()["pending_allocation"] >= 1

    def test_project_utilization_shape(self, client, sample_project):
        r = client.get("/dashboard/project-utilization")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        item = data[0]
        assert "project_id" in item
        assert "project_name" in item
        assert "total_employees" in item
        assert "allocated_seats" in item

    def test_floor_utilization_shape(self, client, sample_seat):
        r = client.get("/dashboard/floor-utilization")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        item = data[0]
        assert "floor" in item
        assert "occupancy_rate" in item
        assert item["floor"] == 2  # sample_seat is on floor 2

    def test_utilization_rate_calculation(
        self, client, sample_employee, occupied_seat
    ):
        r = client.get("/dashboard/floor-utilization")
        floor2 = next((f for f in r.json() if f["floor"] == 2), None)
        assert floor2 is not None
        assert floor2["occupancy_rate"] > 0.0
