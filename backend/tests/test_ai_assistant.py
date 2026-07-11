"""
TDD: AI Assistant tests.
Tests intent parsing + end-to-end query responses.
"""
import pytest
from app.utils.intent_parser import IntentParser


# ═══════════════════════════════════════════════════════════════
# Unit tests: Intent Parser
# ═══════════════════════════════════════════════════════════════

class TestIntentParser:

    def setup_method(self):
        self.parser = IntentParser()

    def test_find_seat_intent_by_name(self):
        result = self.parser.parse("Where is Amit seated?")
        assert result.intent == "find_seat"
        assert result.confidence > 0.5

    def test_find_seat_intent_by_email(self):
        result = self.parser.parse("Where is my seat? My email is amit@ethara.ai")
        assert result.intent == "find_seat"
        assert result.entities.get("email") == "amit@ethara.ai"

    def test_find_project_intent(self):
        result = self.parser.parse("Which project is Sara assigned to?")
        assert result.intent == "find_project"
        assert result.confidence > 0.5

    def test_available_seats_intent_with_floor(self):
        result = self.parser.parse("Show available seats on Floor 3")
        assert result.intent == "available_seats"
        assert result.entities.get("floor") == 3

    def test_available_seats_intent_with_zone(self):
        result = self.parser.parse("Show free seats in Zone B")
        assert result.intent == "available_seats"
        assert result.entities.get("zone") == "B"

    def test_seat_utilization_intent(self):
        result = self.parser.parse("How many seats are occupied for Project Indigo?")
        assert result.intent == "seat_utilization"
        assert "Indigo" in result.entities.get("project_name", "")

    def test_allocate_seat_intent(self):
        result = self.parser.parse("Allocate a seat for a new employee joining today")
        assert result.intent == "allocate_seat"

    def test_find_neighbors_intent(self):
        result = self.parser.parse("Who is sitting near me? My email is john@ethara.ai")
        assert result.intent == "find_neighbors"

    def test_unknown_intent_returns_unknown(self):
        result = self.parser.parse("What is the capital of France?")
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    def test_empty_query_returns_unknown(self):
        result = self.parser.parse("   ")
        assert result.intent == "unknown"

    def test_gibberish_query_returns_unknown(self):
        result = self.parser.parse("xyzzy foo bar baz")
        assert result.intent == "unknown"


# ═══════════════════════════════════════════════════════════════
# Integration: AI endpoint
# ═══════════════════════════════════════════════════════════════

class TestAIEndpointEdgeCases:

    def test_short_query_returns_422(self, client):
        """EDGE: Query too short → Pydantic validation fails."""
        r = client.post("/ai/query", json={"query": "Hi"})
        assert r.status_code == 422

    def test_empty_query_returns_422(self, client):
        r = client.post("/ai/query", json={"query": ""})
        assert r.status_code == 422

    def test_unknown_intent_returns_helpful_message(self, client):
        r = client.post("/ai/query", json={"query": "What is the meaning of life?"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "unknown"
        assert len(data["answer"]) > 0

    def test_find_seat_for_nonexistent_employee(self, client):
        r = client.post("/ai/query", json={"query": "Where is nonexistent_person_xyz seated?"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "find_seat"
        assert "couldn't find" in data["answer"].lower()


class TestAIEndpointHappyPath:

    def test_find_seat_by_email_returns_seat_info(
        self, client, sample_employee, occupied_seat
    ):
        r = client.post("/ai/query", json={
            "query": f"Where is my seat? My email is {sample_employee.email}"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "find_seat"
        assert "Floor 2" in data["answer"]
        assert "Zone B" in data["answer"]
        assert data["source"] == "rule_based"

    def test_find_project_by_email(self, client, sample_employee):
        r = client.post("/ai/query", json={
            "query": f"Which project is {sample_employee.email} assigned to?"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "find_project"
        assert "TestProject" in data["answer"]

    def test_available_seats_query(self, client, sample_seat):
        r = client.post("/ai/query", json={"query": "Show available seats on Floor 2"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "available_seats"
        assert data["data"]["floor"] == 2

    def test_response_has_required_fields(self, client, sample_seat):
        r = client.post("/ai/query", json={"query": "Show available seats"})
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "intent" in data
        assert "source" in data
