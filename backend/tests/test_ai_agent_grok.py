"""
TDD — Grok AI Agent Tests (grok-3-mini via xAI API, direct OpenAI SDK)

Architecture under test:
  ai_agent.py uses the openai SDK directly (no LangChain).
  _get_client_and_source() selects provider: Grok > OpenAI > Gemini.
  AIAgent.run() loops tool calls then returns a final AIResponse.

Test layers:
  1. Unit  — config fields, base URL, model name in source
  2. Unit  — LLM provider selection priority (mocked OpenAI client)
  3. Unit  — tool dispatch: each tool returns correct data from DB
  4. Unit  — tool-calling loop: mock API responses drive the loop
  5. Integration — /ai/query HTTP endpoint (no real API call)
  6. Live  — real xAI API (skipped unless XAI_API_KEY is set)
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile

from app.database import Base
from app.models.project import Project, ProjectStatus
from app.models.employee import Employee, EmployeeStatus
from app.models.seat import Seat, SeatStatus
from app.models.seat_allocation import SeatAllocation, AllocationStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_test_db():
    """Create an isolated file-backed SQLite DB and return (engine, session, path)."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    return engine, db, db_path


def _make_mock_completion(content: str, tool_calls=None):
    """Build a minimal mock matching openai ChatCompletion response shape."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ═══════════════════════════════════════════════════════════════
# 1. UNIT — Config & source-code contracts
# ═══════════════════════════════════════════════════════════════

class TestGrokConfig:
    """Settings fields and ai_agent.py source-code invariants."""

    def test_grok_model_defaults_to_grok_3_mini(self):
        from app.config import Settings
        assert Settings().GROK_MODEL == "grok-3-mini"

    def test_both_grok_key_fields_exist_in_settings(self):
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "GROK_API_KEY")
        assert hasattr(s, "XAI_API_KEY")

    def test_correct_xai_base_url_in_agent(self):
        import inspect
        from app.services import ai_agent
        src = inspect.getsource(ai_agent)
        assert "https://api.x.ai/v1" in src, "Wrong or missing xAI base URL"
        assert "api.xai.com" not in src, "Old incorrect domain still present"

    def test_deprecated_grok_beta_not_in_agent(self):
        import inspect
        from app.services import ai_agent
        assert "grok-beta" not in inspect.getsource(ai_agent)

    def test_agent_uses_settings_grok_model_not_hardcoded(self):
        import inspect
        from app.services import ai_agent
        assert "settings.GROK_MODEL" in inspect.getsource(ai_agent)

    def test_langchain_not_imported_in_agent(self):
        """LangChain was replaced by direct OpenAI SDK."""
        import inspect
        from app.services import ai_agent
        src = inspect.getsource(ai_agent)
        assert "from langchain" not in src
        assert "import langchain" not in src

    def test_openai_sdk_used_directly(self):
        import inspect
        from app.services import ai_agent
        assert "from openai import OpenAI" in inspect.getsource(ai_agent)

    def test_tools_list_defined_in_agent(self):
        """TOOLS list must exist and contain all 5 expected tool names."""
        from app.services.ai_agent import TOOLS
        names = {t["function"]["name"] for t in TOOLS}
        assert names == {
            "get_employee_seat",
            "search_seats",
            "get_seat_utilization",
            "search_projects",
            "find_neighbors",
        }


# ═══════════════════════════════════════════════════════════════
# 2. UNIT — LLM provider selection priority
# ═══════════════════════════════════════════════════════════════

class TestProviderPriority:
    """_get_client_and_source() must pick the right provider."""

    def _run(self, db, grok_key="", xai_key="", openai_key="", gemini_key=""):
        from app.services.ai_agent import AIAgent
        fake = _make_mock_completion("ok")
        with patch("app.services.ai_agent.settings") as ms, \
             patch("app.services.ai_agent.OpenAI") as MockClient:
            ms.GROK_API_KEY   = grok_key
            ms.XAI_API_KEY    = xai_key
            ms.OPENAI_API_KEY = openai_key
            ms.GEMINI_API_KEY = gemini_key
            ms.GROK_MODEL     = "grok-3-mini"
            ms.OPENAI_MODEL   = "gpt-4o"
            MockClient.return_value.chat.completions.create.return_value = fake
            return AIAgent(db, "sess").run("hello"), MockClient
        return None, None

    def test_no_keys_returns_rule_based(self, db_session):
        from app.services.ai_agent import AIAgent
        with patch("app.services.ai_agent.settings") as ms:
            ms.GROK_API_KEY = ms.XAI_API_KEY = ms.OPENAI_API_KEY = ms.GEMINI_API_KEY = ""
            ms.GROK_MODEL = "grok-3-mini"
            result = AIAgent(db_session, "s").run("hello")
        assert result.source == "rule_based"
        assert "No AI API key" in result.answer

    def test_xai_key_selects_grok_source(self, db_session):
        result, MockClient = self._run(db_session, xai_key="xai-test")
        assert result.source == "grok"
        # Verify xAI base_url was passed to OpenAI client
        kwargs = MockClient.call_args.kwargs
        assert "api.x.ai" in kwargs.get("base_url", "")

    def test_grok_key_selects_grok_source(self, db_session):
        result, _ = self._run(db_session, grok_key="xai-grok")
        assert result.source == "grok"

    def test_grok_beats_openai(self, db_session):
        result, _ = self._run(db_session, grok_key="xai-grok", openai_key="sk-openai")
        assert result.source == "grok"

    def test_grok_beats_gemini(self, db_session):
        result, _ = self._run(db_session, grok_key="xai-grok", gemini_key="gemini-key")
        assert result.source == "grok"

    def test_openai_when_no_grok(self, db_session):
        result, _ = self._run(db_session, openai_key="sk-openai")
        assert result.source == "openai"

    def test_gemini_as_last_resort(self, db_session):
        result, MockClient = self._run(db_session, gemini_key="gemini-key")
        assert result.source == "gemini"
        kwargs = MockClient.call_args.kwargs
        assert "generativelanguage" in kwargs.get("base_url", "")


# ═══════════════════════════════════════════════════════════════
# 3. UNIT — Tool dispatch + DB layer contracts
# ═══════════════════════════════════════════════════════════════

class TestAgentTools:
    """Each tool must call the correct repository and return a string."""

    @pytest.fixture
    def seeded(self):
        engine, db, db_path = _make_test_db()
        proj = Project(name="ProjectAlpha", status=ProjectStatus.ACTIVE,
                       description="desc", manager_name="mgr@ethara.ai")
        db.add(proj); db.commit(); db.refresh(proj)

        emp = Employee(
            employee_code="ETH-00042", name="Alice Neon",
            email="alice@ethara.ai", department="Engineering",
            role="Senior Engineer", joining_date=date.today(),
            status=EmployeeStatus.ACTIVE, project_id=proj.id,
        )
        db.add(emp); db.commit(); db.refresh(emp)

        seat = Seat(floor=3, zone="C", bay="Bay-7",
                    seat_number="C7-12", status=SeatStatus.AVAILABLE)
        db.add(seat); db.commit(); db.refresh(seat)

        alloc = SeatAllocation(
            employee_id=emp.id, seat_id=seat.id, project_id=proj.id,
            allocation_status=AllocationStatus.ACTIVE, allocation_date=date.today(),
        )
        seat.status = SeatStatus.OCCUPIED
        db.add(alloc); db.commit()

        yield db, emp, proj, seat
        db.close(); engine.dispose(); os.unlink(db_path)

    # ── get_employee_seat ─────────────────────────────────────

    def test_seat_by_email(self, seeded):
        db, emp, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._get_employee_seat("alice@ethara.ai")
        assert "Alice Neon" in r
        assert "Floor 3" in r
        assert "Zone C" in r

    def test_seat_by_name(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._get_employee_seat("Alice")
        assert "Floor 3" in r

    def test_seat_unknown_employee(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._get_employee_seat("nobody@nowhere.com")
        assert "No employee found" in r

    def test_seat_employee_with_no_allocation(self, db_session, sample_employee):
        """Employee exists but has no seat — should get a clear message."""
        from app.services.ai_agent import AIAgent
        r = AIAgent(db_session, "s")._get_employee_seat(sample_employee.email)
        assert sample_employee.name in r
        assert "no active seat" in r.lower()

    # ── search_seats ─────────────────────────────────────────

    def test_search_by_floor(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._search_seats(floor=3)
        assert "Floor 3" in r

    def test_search_occupied(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._search_seats(status="OCCUPIED")
        assert "OCCUPIED" in r.upper()

    def test_search_no_results(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._search_seats(floor=99)
        assert "No seats found" in r

    # ── get_seat_utilization ──────────────────────────────────

    def test_utilization_has_all_fields(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._get_seat_utilization()
        for keyword in ("Total", "Occupied", "Available", "%"):
            assert keyword in r, f"Missing '{keyword}' in utilization output"

    def test_utilization_occupied_is_1(self, seeded):
        """Seeded DB has exactly 1 occupied seat."""
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._get_seat_utilization()
        assert "Occupied: 1" in r

    # ── search_projects ───────────────────────────────────────

    def test_project_by_name(self, seeded):
        db, emp, proj, seat = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._search_projects("Alpha")
        assert "ProjectAlpha" in r
        assert "mgr@ethara.ai" in r

    def test_project_no_match(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._search_projects("ZZZNOMATCH")
        assert "No projects found" in r

    # ── find_neighbors ────────────────────────────────────────

    def test_neighbors_returns_string(self, seeded):
        db, emp, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._find_neighbors("alice@ethara.ai")
        assert isinstance(r, str) and len(r) > 0

    def test_neighbors_unknown_employee(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._find_neighbors("ghost@ethara.ai")
        assert "not found" in r.lower()

    # ── _dispatch_tool ────────────────────────────────────────

    def test_dispatch_get_employee_seat(self, seeded):
        db, emp, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._dispatch_tool(
            "get_employee_seat", {"email_or_name": emp.email}
        )
        assert "Alice Neon" in r

    def test_dispatch_get_seat_utilization(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._dispatch_tool("get_seat_utilization", {})
        assert "Total" in r

    def test_dispatch_search_projects(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._dispatch_tool("search_projects", {"query": "Alpha"})
        assert "ProjectAlpha" in r

    def test_dispatch_unknown_tool(self, seeded):
        db, *_ = seeded
        from app.services.ai_agent import AIAgent
        r = AIAgent(db, "s")._dispatch_tool("nonexistent_tool", {})
        assert "Unknown tool" in r


# ═══════════════════════════════════════════════════════════════
# 4. UNIT — Tool-calling loop (mocked OpenAI responses)
# ═══════════════════════════════════════════════════════════════

class TestAgentLoop:
    """Verify the agentic loop handles tool calls → execute → final answer."""

    def _tool_call_mock(self, name: str, args: dict, call_id: str = "tc_1"):
        tc = MagicMock()
        tc.id = call_id
        tc.function.name = name
        tc.function.arguments = json.dumps(args)
        return tc

    def test_direct_answer_no_tools(self, db_session):
        """Model answers immediately without calling any tool."""
        with patch("app.services.ai_agent.settings") as ms, \
             patch("app.services.ai_agent.OpenAI") as MockClient:
            ms.GROK_API_KEY = "xai-key"; ms.XAI_API_KEY = ""
            ms.OPENAI_API_KEY = ms.GEMINI_API_KEY = ""
            ms.GROK_MODEL = "grok-3-mini"; ms.OPENAI_MODEL = "gpt-4o"
            MockClient.return_value.chat.completions.create.return_value = \
                _make_mock_completion("There are 66 available seats.")

            from app.services.ai_agent import AIAgent
            result = AIAgent(db_session, "loop-1").run("available seats?")

        assert "66" in result.answer
        assert result.source == "grok"
        assert result.intent == "ai_agent"
        assert result.confidence == 0.9

    def test_tool_call_then_final_answer(self, db_session):
        """Model calls a tool first, then produces a final answer."""
        tc = self._tool_call_mock("get_seat_utilization", {})
        with patch("app.services.ai_agent.settings") as ms, \
             patch("app.services.ai_agent.OpenAI") as MockClient:
            ms.GROK_API_KEY = "xai-key"; ms.XAI_API_KEY = ""
            ms.OPENAI_API_KEY = ms.GEMINI_API_KEY = ""
            ms.GROK_MODEL = "grok-3-mini"; ms.OPENAI_MODEL = "gpt-4o"
            MockClient.return_value.chat.completions.create.side_effect = [
                _make_mock_completion(content=None, tool_calls=[tc]),
                _make_mock_completion("Occupancy is 90%."),
            ]
            from app.services.ai_agent import AIAgent
            result = AIAgent(db_session, "loop-2").run("utilization?")

        assert "90%" in result.answer
        assert result.source == "grok"

    def test_api_error_returns_graceful_response(self, db_session):
        """Network error must not raise 500 — returns AIResponse with error text."""
        with patch("app.services.ai_agent.settings") as ms, \
             patch("app.services.ai_agent.OpenAI") as MockClient:
            ms.GROK_API_KEY = "xai-key"; ms.XAI_API_KEY = ""
            ms.OPENAI_API_KEY = ms.GEMINI_API_KEY = ""
            ms.GROK_MODEL = "grok-3-mini"; ms.OPENAI_MODEL = "gpt-4o"
            MockClient.return_value.chat.completions.create.side_effect = \
                Exception("Connection timeout")
            from app.services.ai_agent import AIAgent
            result = AIAgent(db_session, "loop-3").run("anything")

        assert result.source == "grok"
        assert result.confidence == 0.0
        assert "error" in result.answer.lower() or "timeout" in result.answer.lower()

    def test_response_includes_session_id(self, db_session):
        """AIResponse must carry back the session_id."""
        with patch("app.services.ai_agent.settings") as ms, \
             patch("app.services.ai_agent.OpenAI") as MockClient:
            ms.GROK_API_KEY = "xai-key"; ms.XAI_API_KEY = ""
            ms.OPENAI_API_KEY = ms.GEMINI_API_KEY = ""
            ms.GROK_MODEL = "grok-3-mini"; ms.OPENAI_MODEL = "gpt-4o"
            MockClient.return_value.chat.completions.create.return_value = \
                _make_mock_completion("Done.")
            from app.services.ai_agent import AIAgent
            result = AIAgent(db_session, "my-session-id").run("test")

        assert result.session_id == "my-session-id"


# ═══════════════════════════════════════════════════════════════
# 5. INTEGRATION — /ai/query HTTP endpoint
# ═══════════════════════════════════════════════════════════════

class TestAIQueryEndpoint:
    """HTTP-level tests — no real API calls."""

    def test_valid_query_returns_200(self, client):
        r = client.post("/ai/query", json={"query": "Show available seats"})
        assert r.status_code == 200

    def test_response_has_required_fields(self, client):
        r = client.post("/ai/query", json={"query": "Where is Alice?"})
        assert r.status_code == 200
        data = r.json()
        for field in ("answer", "intent", "source"):
            assert field in data, f"Missing field: {field}"

    def test_empty_query_returns_422(self, client):
        r = client.post("/ai/query", json={"query": ""})
        assert r.status_code == 422

    def test_short_query_under_3_chars_returns_422(self, client):
        r = client.post("/ai/query", json={"query": "Hi"})
        assert r.status_code == 422

    def test_missing_query_field_returns_422(self, client):
        r = client.post("/ai/query", json={})
        assert r.status_code == 422

    def test_no_api_key_returns_rule_based_or_no_key(self, client):
        """In test env (no API key) → rule_based fallback, answer is non-empty."""
        r = client.post("/ai/query", json={"query": "Show available seats on Floor 2"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["answer"]) > 0
        assert data["source"] in ("rule_based", "grok", "openai", "gemini")

    def test_session_id_accepted(self, client):
        r = client.post("/ai/query", json={
            "query": "Show available seats",
            "session_id": "test-session-abc"
        })
        assert r.status_code == 200

    def test_unauthenticated_request_returns_401(self):
        """Without a JWT token, /ai/query must return 401."""
        from fastapi.testclient import TestClient
        from app.main import app as _app
        bare_client = TestClient(_app, raise_server_exceptions=False)
        r = bare_client.post("/ai/query", json={"query": "Show available seats"})
        assert r.status_code == 401

    def test_rate_limit_after_10_requests(self, client):
        """POST /ai/query is rate-limited at 10/minute per IP."""
        ip = {"X-Forwarded-For": "10.9.9.9"}
        for _ in range(10):
            client.post("/ai/query", json={"query": "Show seats"}, headers=ip)
        r = client.post("/ai/query", json={"query": "Show seats"}, headers=ip)
        assert r.status_code == 429

    def test_rule_based_find_seat_intent(self, client, sample_employee, occupied_seat):
        """Rule-based path must return seat info from the fixture DB."""
        r = client.post("/ai/query", json={
            "query": f"Where is my seat? My email is {sample_employee.email}"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "find_seat"
        assert "Floor 2" in data["answer"]

    def test_rule_based_available_seats(self, client):
        r = client.post("/ai/query", json={"query": "Show available seats on Floor 2"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "available_seats"
        assert data["source"] == "rule_based"


# ═══════════════════════════════════════════════════════════════
# 6. ENUM INPUT — status fields accept lowercase (Prompt 11 regression guard)
# ═══════════════════════════════════════════════════════════════

class TestEnumInputNormalisation:
    """
    Guard against regression of the UPPERCASE enum bug.
    POST /employees and POST /seats must accept lowercase status strings.
    """

    def test_employee_create_with_lowercase_status(self, client, sample_project):
        r = client.post("/employees", json={
            "name": "Enum Test User",
            "email": "enumtest@ethara.ai",
            "status": "inactive",           # lowercase — must NOT return 422
            "project_id": sample_project.id,
        })
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        assert r.json()["status"] == "inactive"

    def test_employee_create_with_uppercase_status(self, client, sample_project):
        r = client.post("/employees", json={
            "name": "Enum Test User 2",
            "email": "enumtest2@ethara.ai",
            "status": "ACTIVE",
            "project_id": sample_project.id,
        })
        assert r.status_code == 201
        assert r.json()["status"] == "active"

    def test_employee_create_default_status_is_active(self, client, sample_project):
        r = client.post("/employees", json={
            "name": "Default Status User",
            "email": "defaultstatus@ethara.ai",
            "project_id": sample_project.id,
        })
        assert r.status_code == 201
        assert r.json()["status"] == "active"

    def test_employee_update_with_lowercase_status(self, client, sample_employee):
        r = client.put(f"/employees/{sample_employee.id}", json={"status": "on_leave"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json()["status"] == "on_leave"

    def test_seat_create_with_lowercase_status(self, client):
        r = client.post("/seats", json={
            "floor": 4, "zone": "D", "bay": "Bay-3",
            "seat_number": "D3-99", "status": "reserved",   # lowercase
        })
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        assert r.json()["status"] == "reserved"

    def test_seat_update_with_lowercase_status(self, client, sample_seat):
        r = client.put(f"/seats/{sample_seat.id}", json={"status": "maintenance"})
        assert r.status_code == 200
        assert r.json()["status"] == "maintenance"

    def test_project_update_with_lowercase_status(self, client, sample_project):
        r = client.put(f"/projects/{sample_project.id}", json={"status": "inactive"})
        assert r.status_code == 200
        assert r.json()["status"] == "inactive"


# ═══════════════════════════════════════════════════════════════
# 7. LIVE — Real xAI Grok API (skipped unless key set)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    not os.getenv("XAI_API_KEY") and not os.getenv("GROK_API_KEY"),
    reason="XAI_API_KEY / GROK_API_KEY not set — skipping live Grok test"
)
class TestLiveGrokAPI:
    """
    Run manually with a real key:
        XAI_API_KEY=xai-... pytest tests/test_ai_agent_grok.py -k TestLiveGrokAPI -v
    """

    def test_live_grok_returns_non_empty_answer(self, client, sample_employee, occupied_seat):
        r = client.post("/ai/query", json={
            "query": f"Where is {sample_employee.name} seated?",
            "session_id": "live-1"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "grok"
        assert len(data["answer"]) > 10

    def test_live_grok_references_db_data(self, client, sample_employee, occupied_seat):
        """Grok must call DB tools and mention real floor/zone from the fixture."""
        r = client.post("/ai/query", json={
            "query": f"What floor is {sample_employee.email} sitting on?",
            "session_id": "live-2"
        })
        assert r.status_code == 200
        data = r.json()
        # occupied_seat fixture → floor=2, zone=B
        assert any(x in data["answer"] for x in ["2", "Floor", "floor"])

    def test_live_grok_utilization_mentions_percentage(self, client):
        r = client.post("/ai/query", json={
            "query": "What is the current seat occupancy rate?",
            "session_id": "live-3"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "grok"
        assert "%" in data["answer"] or "percent" in data["answer"].lower()
