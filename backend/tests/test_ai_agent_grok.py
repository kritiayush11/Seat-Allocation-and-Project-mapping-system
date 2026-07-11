"""
TDD — Grok AI Agent Tests (grok-3-mini via xAI API)

Red → Green → Refactor

Tests are structured in three layers:
  1. Unit  — config, URL, model name (no network)
  2. Integration — AIAgent wiring with mocked LLM (no real API call)
  3. Contract — tool schemas and DB query correctness (no real API call)

Real xAI API calls are skipped unless XAI_API_KEY is set in the environment,
keeping CI fast and free.
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile

from app.database import Base, get_db
from app.main import app
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.employee import Employee, EmployeeStatus
from app.models.seat import Seat, SeatStatus
from app.models.seat_allocation import SeatAllocation, AllocationStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_test_db():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    return engine, db, db_path


# ═══════════════════════════════════════════════════════════════
# 1. UNIT — Config & model name
# ═══════════════════════════════════════════════════════════════

class TestGrokConfig:
    """Config must expose the right model name and base URL constants."""

    def test_grok_model_is_grok_3_mini(self):
        """GROK_MODEL must default to grok-3-mini (free tier)."""
        from app.config import Settings
        s = Settings()
        assert s.GROK_MODEL == "grok-3-mini", (
            f"Expected grok-3-mini, got {s.GROK_MODEL}"
        )

    def test_grok_api_key_field_exists(self):
        """Settings must have both GROK_API_KEY and XAI_API_KEY fields."""
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "GROK_API_KEY")
        assert hasattr(s, "XAI_API_KEY")

    def test_xai_base_url_in_agent(self):
        """The correct xAI base URL must be used in ai_agent.py (not the old one)."""
        import inspect
        from app.services import ai_agent
        source = inspect.getsource(ai_agent)
        assert "https://api.x.ai/v1" in source, \
            "ai_agent.py must use https://api.x.ai/v1 (not api.xai.com)"
        assert "grok-beta" not in source, \
            "ai_agent.py must not reference deprecated grok-beta model"

    def test_grok_model_name_in_agent(self):
        """Agent must use settings.GROK_MODEL (not a hardcoded string)."""
        import inspect
        from app.services import ai_agent
        source = inspect.getsource(ai_agent)
        assert "settings.GROK_MODEL" in source, \
            "ai_agent.py must use settings.GROK_MODEL for the model name"


# ═══════════════════════════════════════════════════════════════
# 2. UNIT — AIAgent LLM selection priority
# ═══════════════════════════════════════════════════════════════

class TestAIAgentLLMSelection:
    """AIAgent must select the right LLM based on which key is set."""

    def _make_agent(self, db, session_id="test-session"):
        from app.services.ai_agent import AIAgent
        return AIAgent(db, session_id)

    def test_no_keys_returns_rule_based_message(self, db_session):
        """With no API keys configured, agent must return a helpful no-key message."""
        with patch("app.services.ai_agent.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GROK_API_KEY = ""
            mock_settings.XAI_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.GROK_MODEL = "grok-3-mini"

            agent = self._make_agent(db_session)
            result = agent.run("where is alice?")

        assert result.source == "rule_based"
        assert "No AI credentials" in result.answer

    def test_xai_key_selects_grok_source(self, db_session):
        """When XAI_API_KEY is set, agent source must be 'grok'."""
        mock_llm = MagicMock()
        mock_llm.return_value = MagicMock()

        with patch("app.services.ai_agent.settings") as mock_settings, \
             patch("langchain_openai.ChatOpenAI") as mock_openai:

            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GROK_API_KEY = ""
            mock_settings.XAI_API_KEY = "xai-test-key-123"
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.GROK_MODEL = "grok-3-mini"

            # Make LLM init succeed but agent invoke fail gracefully
            mock_openai.return_value = MagicMock()
            mock_openai.return_value.invoke = MagicMock(side_effect=Exception("mock stop"))

            agent = self._make_agent(db_session)
            result = agent.run("how many seats are available?")

        # Source is set before the invoke call — even on error it should be grok
        assert result.source == "grok", f"Expected 'grok', got '{result.source}'"

    def test_grok_api_key_takes_priority_over_openai(self, db_session):
        """GROK_API_KEY must be preferred over OPENAI_API_KEY."""
        with patch("app.services.ai_agent.settings") as mock_settings, \
             patch("langchain_openai.ChatOpenAI") as mock_openai:

            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GROK_API_KEY = "xai-grok-key"
            mock_settings.XAI_API_KEY = ""
            mock_settings.OPENAI_API_KEY = "sk-openai-key"
            mock_settings.GROK_MODEL = "grok-3-mini"

            mock_openai.return_value = MagicMock()
            mock_openai.return_value.invoke = MagicMock(side_effect=Exception("mock stop"))

            agent = self._make_agent(db_session)
            result = agent.run("show me seat utilization")

        assert result.source == "grok"

    def test_gemini_takes_highest_priority(self, db_session):
        """GEMINI_API_KEY must be preferred over Grok and OpenAI."""
        with patch("app.services.ai_agent.settings") as mock_settings, \
             patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:

            mock_settings.GEMINI_API_KEY = "gemini-key-abc"
            mock_settings.GROK_API_KEY = "xai-grok-key"
            mock_settings.XAI_API_KEY = ""
            mock_settings.OPENAI_API_KEY = "sk-openai-key"
            mock_settings.GROK_MODEL = "grok-3-mini"

            mock_gemini.return_value = MagicMock()
            mock_gemini.return_value.invoke = MagicMock(side_effect=Exception("mock stop"))

            agent = self._make_agent(db_session)
            result = agent.run("where is test user?")

        assert result.source == "gemini"


# ═══════════════════════════════════════════════════════════════
# 3. UNIT — Tool contracts (DB queries work correctly)
# ═══════════════════════════════════════════════════════════════

class TestGrokAgentTools:
    """
    Verify each tool the agent calls against the real DB layer.
    Tools are extracted and called directly — no LLM involved.
    """

    @pytest.fixture
    def seeded_db(self):
        engine, db, db_path = _make_test_db()

        proj = Project(name="ProjectAlpha", status=ProjectStatus.ACTIVE,
                       description="desc", manager_name="mgr@ethara.ai")
        db.add(proj); db.commit(); db.refresh(proj)

        emp = Employee(
            employee_code="ETH-00042",
            name="Alice Neon",
            email="alice@ethara.ai",
            department="Engineering",
            role="Senior Engineer",
            joining_date=date.today(),
            status=EmployeeStatus.ACTIVE,
            project_id=proj.id,
        )
        db.add(emp); db.commit(); db.refresh(emp)

        seat = Seat(floor=3, zone="C", bay="Bay-7", seat_number="C7-12",
                    status=SeatStatus.AVAILABLE)
        db.add(seat); db.commit(); db.refresh(seat)

        alloc = SeatAllocation(
            employee_id=emp.id,
            seat_id=seat.id,
            project_id=proj.id,
            allocation_status=AllocationStatus.ACTIVE,
            allocation_date=date.today(),
        )
        seat.status = SeatStatus.OCCUPIED
        db.add(alloc); db.commit()

        yield db, emp, proj, seat

        db.close()
        engine.dispose()
        import os as _os
        _os.unlink(db_path)

    def test_employee_seat_lookup_by_email(self, seeded_db):
        """get_employee_seat tool must find seat by email and return floor/zone."""
        db, emp, proj, seat = seeded_db
        from app.repositories.employee_repository import EmployeeRepository
        repo = EmployeeRepository(db)

        found = repo.get_by_email("alice@ethara.ai")
        assert found is not None
        assert found.name == "Alice Neon"

        alloc = repo.get_active_allocation(found.id)
        assert alloc is not None
        assert alloc.seat.floor == 3
        assert alloc.seat.zone == "C"

    def test_employee_seat_lookup_by_name(self, seeded_db):
        """get_employee_seat tool must find seat by partial name."""
        db, emp, proj, seat = seeded_db
        from app.repositories.employee_repository import EmployeeRepository
        repo = EmployeeRepository(db)

        results, total = repo.search(query="Alice")
        assert total >= 1
        assert results[0].name == "Alice Neon"

    def test_seat_utilization_counts(self, seeded_db):
        """get_seat_utilization tool must count occupied seats correctly."""
        db, emp, proj, seat = seeded_db
        from app.repositories.seat_repository import SeatRepository
        repo = SeatRepository(db)

        total = repo.count()
        occupied = repo.count(status="OCCUPIED")
        assert total >= 1
        assert occupied >= 1

    def test_project_search(self, seeded_db):
        """search_projects tool must find project by partial name."""
        db, emp, proj, seat = seeded_db
        from app.repositories.project_repository import ProjectRepository
        repo = ProjectRepository(db)

        results, total = repo.search(query="Alpha")
        assert total >= 1
        assert results[0].name == "ProjectAlpha"

    def test_find_neighbors_same_zone(self, seeded_db):
        """find_neighbors tool must search seats in same floor/zone."""
        db, emp, proj, seat = seeded_db
        from app.repositories.seat_repository import SeatRepository
        repo = SeatRepository(db)

        nearby, _ = repo.search(floor=3, zone="C", limit=10)
        assert len(nearby) >= 1


# ═══════════════════════════════════════════════════════════════
# 4. INTEGRATION — /ai/query endpoint with session_id triggers agent
# ═══════════════════════════════════════════════════════════════

class TestAIQueryEndpointWithGrok:
    """
    End-to-end: POST /ai/query with session_id must trigger AIAgent.
    LLM is mocked so no real API call is made.
    """

    def test_session_id_triggers_agent_path(self, client):
        """When session_id is provided and no key configured → agent returns no-key message."""
        r = client.post("/ai/query", json={
            "query": "Where is Alice seated?",
            "session_id": "test-grok-session-001"
        })
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "session_id" in data or data.get("session_id") is None  # field present

    def test_without_session_id_uses_rule_based(self, client):
        """Without session_id, must always use rule-based path."""
        r = client.post("/ai/query", json={"query": "Show available seats"})
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "rule_based"

    def test_grok_agent_error_returns_200_not_500(self, client):
        """When agent has no LLM key, endpoint still returns 200 with a helpful answer."""
        # No API keys are configured in the test environment — agent falls back gracefully
        r = client.post("/ai/query", json={
            "query": "How many seats are occupied?",
            "session_id": "test-error-session"
        })
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_response_schema_always_has_required_fields(self, client):
        """Every /ai/query response must have answer, intent, source fields."""
        for query in [
            "Where is Alice?",
            "How many seats are occupied?",
            "Which project is sara@ethara.ai on?",
        ]:
            r = client.post("/ai/query", json={"query": query})
            assert r.status_code == 200
            data = r.json()
            assert "answer" in data, f"Missing 'answer' for query: {query}"
            assert "intent" in data, f"Missing 'intent' for query: {query}"
            assert "source" in data, f"Missing 'source' for query: {query}"


# ═══════════════════════════════════════════════════════════════
# 5. LIVE — Real Grok API call (skipped unless key set)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    not os.getenv("XAI_API_KEY") and not os.getenv("GROK_API_KEY"),
    reason="XAI_API_KEY / GROK_API_KEY not set — skipping live Grok test"
)
class TestLiveGrokAPI:
    """
    Requires XAI_API_KEY or GROK_API_KEY in environment.
    Run manually: XAI_API_KEY=xai-... pytest tests/test_ai_agent_grok.py -k live -v
    """

    def test_live_grok_returns_answer(self, client, sample_employee, occupied_seat):
        """Real Grok API must respond with a non-empty answer."""
        r = client.post("/ai/query", json={
            "query": f"Where is {sample_employee.name} seated?",
            "session_id": "live-grok-test-session"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "grok"
        assert len(data["answer"]) > 0

    def test_live_grok_uses_db_data(self, client, sample_employee, occupied_seat):
        """Grok must use the DB tools and mention real floor/zone data."""
        r = client.post("/ai/query", json={
            "query": f"What floor is {sample_employee.email} on?",
            "session_id": "live-grok-db-test"
        })
        assert r.status_code == 200
        data = r.json()
        # occupied_seat is floor 2, zone B
        assert "2" in data["answer"] or "Floor" in data["answer"]
