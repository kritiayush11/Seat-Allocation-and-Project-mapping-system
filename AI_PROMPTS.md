# AI_PROMPTS.md — Ethara Seat Allocation System

> Documents all AI tool usage, prompts, validations, and manual corrections made during development.

---

## Tool Used

**Kiro (AI-powered IDE)** — Autonomous coding assistant running inside VS Code.

---

## Prompt 1 — Architecture Planning

**Prompt:**

> "Build a full-stack seat allocation and project mapping system for Ethara with ~5,000 employees. Plan the architecture using SOLID principles, TDD approach, and a proximity-based seat allocation algorithm. Recommend the tech stack and justify each choice."

**What AI generated correctly:**

- Complete directory structure with clear separation of concerns
- SOLID principle mapping to concrete files
- Proximity-based greedy algorithm with zone fallback documented
- TDD Red→Green→Refactor workflow with edge cases first

**What AI generated incorrectly:**

- Initial plan suggested a separate `interfaces/` directory which added unnecessary complexity

**Manual fix:**

- Removed the standalone `interfaces/` directory; kept abstract base classes inline

---

## Prompt 2 — Database Design

**Prompt:**

> "Design SQLAlchemy ORM models for Employee, Project, Seat, and SeatAllocation. Include enums, unique constraints, relationships, and composite indexes."

**What AI generated correctly:**

- All four models with correct FK relationships and `back_populates`
- Composite unique constraint on `(floor, zone, bay, seat_number)`
- Composite indexes on allocation lookups for fast queries
- SQLite WAL mode + foreign key pragma for dev

**What AI generated incorrectly:**

- Used deprecated `declarative_base()` from `sqlalchemy.ext.declarative` — updated to `sqlalchemy.orm.declarative_base()`
- Enum values defined as lowercase (`"active"`, `"occupied"`) — caused critical bug when deploying to Neon (see Prompt 11)

---

## Prompt 3 — Backend APIs

**Prompt:**

> "Create FastAPI routers for employees, projects, seats, dashboard, and AI assistant. Each router should delegate to its service class. Include Swagger docs via docstrings."

**What AI generated correctly:**

- All 5 router files with full endpoint coverage and correct HTTP status codes
- Query parameter handling with type coercion
- Swagger docstrings on every endpoint

**What AI generated incorrectly:**

- Missing `seed_router` import in `routers/__init__.py`

**Manual fix:**

- Added `seed_router` to `__init__.py` and registered in `main.py`

---

## Prompt 4 — Seat Allocation Logic

**Prompt:**

> "Implement the proximity-based greedy seat allocation algorithm. Score available seats +3 for same zone, +2 for same floor. Enforce all 8 business rules."

**What AI generated correctly:**

- `find_seats_near_project()` correctly queries active allocations by project to find majority zone
- All 8 business rules enforced at service layer with correct status codes
- `create_allocation()` atomically updates both `SeatAllocation` and `Seat.status`

**What AI generated incorrectly:**

- `count_by_status()` returned `"SeatStatus.OCCUPIED"` as dict key instead of `"occupied"` — dashboard counts showed 0

**Manual fix:**

- Changed to `status.value if hasattr(status, 'value') else str(status)` for correct enum extraction

---

## Prompt 5 — AI Assistant (Rule-Based)

**Prompt:**

> "Build a rule-based intent parser using Strategy/OCP pattern. Handlers: find_seat, find_project, available_seats, seat_utilization, allocate_seat, find_neighbors."

**What AI generated correctly:**

- 6 `IntentHandler` subclasses with regex patterns, email extraction, confidence scores
- `IntentParser` as orchestrator — picks highest confidence result

**What AI generated incorrectly:**

- Handler confidence ordering caused wrong intent matches for complex queries

**Manual fix:**

- Raised `SeatUtilizationHandler` and `NeighborHandler` confidence scores

---

## Prompt 6 — Frontend

**Prompt:**

> "Build a React + TypeScript frontend matching Ethara's brand. Pages: Dashboard, Employees, Seats, Projects, AI Assistant. Use TanStack Query."

**What AI generated correctly:**

- Full Ethara color palette in Tailwind config
- All 5 pages with correct business flows, toast notifications, reusable components
- AI chat UI with voice dictation, session_id, suggestion chips

**What AI generated incorrectly:**

- `Card` component missing `onClick` prop in TypeScript interface

**Manual fix:**

- Added `onClick?: () => void` to `CardProps`

---

## Prompt 7 — Testing (TDD)

**Prompt:**

> "Write a TDD test suite using pytest. Write edge case tests first. Use per-test SQLite database isolation."

**What AI generated correctly:**

- Tests covering all 8 business rules, intent parser, dashboard aggregations
- Fixtures: `sample_project`, `sample_employee`, `sample_seat`, `occupied_seat`

**What AI generated incorrectly:**

- First approach used `sqlite:///:memory:` — SQLAlchemy creates a separate in-memory DB per connection, causing `no such table` errors

**Manual fix:**

- Switched to `tempfile.mkstemp(suffix=".db")` — file-backed SQLite shared across all connections in a test

---

## Prompt 8 — Rate Limiting

**Prompt:**

> "Add per-IP rate limiting via slowapi. Limits: /auth/login 5/min, /seats 60/min, /seats/allocate 20/min, /ai/query 10/min."

**What AI generated correctly:**

- `limiter.py` with `_get_client_ip()` reading `X-Forwarded-For` for correct IP behind proxies
- 13 TDD rate-limit tests covering all endpoints + per-IP isolation
- `conftest.py` autouse fixture resets limiter state between tests

---

## Prompt 9 — Neon PostgreSQL Migration

**Prompt:**

> "Migrate my SQLite ethara_seats.db to Neon PostgreSQL. Write a migration script that handles FK constraints and migrates all 6 tables."

**What AI generated correctly:**

- Migration script using SQLAlchemy Core (not ORM) to avoid autoflush FK violations
- `TRUNCATE TABLE ... CASCADE` to clear destination before each table
- Correct insertion order respecting FK dependencies: users → projects → employees → seats → seat_allocations → chat_messages
- Verified 5,001 employees, 5,500 seats, 4,951 allocations migrated successfully

**What AI generated incorrectly:**

- First attempt used `session_replication_role = 'replica'` to disable FK checks — Neon blocks this for non-superuser roles
- Second attempt used `SET CONSTRAINTS ALL DEFERRED` — also blocked

**Manual fix:**

- Switched to inserting tables in correct FK dependency order with no FK disabling needed

---

## Prompt 10 — Deployment (Render + Netlify)

**Prompt:**

> "Deploy backend to Render and frontend to Netlify. Fix the 422 login error in production."

**Diagnosis process:**

1. Render receives POST with empty body → `input: null` → 422
2. Root cause: uvicorn behind Render's reverse proxy strips request bodies without `--proxy-headers`
3. Fixed start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "*"`
4. Frontend was hardcoding `localhost:8000` because `REACT_APP_API_URL` was not set at build time
5. Fixed: `frontend/.env.production` with correct Render URL, committed to repo so Netlify picks it up automatically

**What AI generated correctly:**

- Full diagnosis of the proxy body-stripping issue
- `ALLOWED_ORIGINS_RAW` as plain string to fix pydantic-settings `SettingsError` on Render
- `frontend/.env.production` approach for baking the API URL into the Netlify build

---

## Prompt 11 — Critical Enum Bug Fix (Neon UPPERCASE)

**Prompt:**

> "Add seat and employee is getting error — fix all this. Check schema from Neon."

**Diagnosis:**

- Inspected Neon PostgreSQL enum types: `seatstatus: 'AVAILABLE'`, `employeestatus: 'ACTIVE'` etc. — all UPPERCASE
- Python models had lowercase values: `SeatStatus.AVAILABLE = "available"` — Postgres rejected every insert
- Dashboard showed 0 occupied seats because `count_by_status()` dict keys were UPPERCASE but lookups used lowercase

**What AI generated correctly:**

- Identified the UPPERCASE vs lowercase mismatch by directly inspecting Neon enum types via `pg_enum`
- Updated all 4 models to UPPERCASE with `create_type=False`
- Added `field_serializer` to schemas to keep API JSON lowercase (no frontend changes needed)
- Added `field_validator` with `.upper()` normalisation to accept both cases as input
- Fixed `seat_repository.py` and `dashboard_service.py` to use UPPERCASE dict keys

---

## Prompt 12 — AI Agent Rewrite (OpenAI SDK)

**Prompt:**

> "AI is always saying rule_based. Fix it. Use Grok free model and the OpenAI SDK. Think like a senior AI engineer."

**Root cause:** Agent was gated on both `session_id` being present AND an API key being set. `ai_assistant_service.py` only delegated to the agent when both conditions were true.

**What AI generated correctly:**

- Complete rewrite of `ai_agent.py` using direct OpenAI SDK (no LangChain)
- `_get_client_and_source()` selects provider: Grok (api.x.ai/v1) → OpenAI → Gemini (OpenAI-compatible endpoint)
- Agentic tool-calling loop: up to 5 rounds, dispatch DB tools, feed results back to model
- `TOOLS` list in OpenAI function-calling JSON format — clean, debuggable, no LangChain abstractions
- `ai_assistant_service.py` updated: delegates to agent on any key present, no session_id gate
- Chat history load/save via `chat_messages` table preserved

**Why removed LangChain:**

- LangChain 0.2.x had version conflicts with langchain-core, langchain-openai, langchain-google-genai
- 5+ abstraction layers (AgentExecutor → RunnableWithMessageHistory → create_tool_calling_agent → ChatPromptTemplate → ...) over what is a simple API call with tools
- Direct SDK: 1 function, 1 loop, fully transparent, easy to test and debug

---

## Summary: AI vs Manual

| Area                           | AI Accuracy  | Manual Intervention                                    |
| ------------------------------ | ------------ | ------------------------------------------------------ |
| Architecture / SOLID design    | ✅ Excellent | Minor simplification (removed `interfaces/` dir)       |
| ORM models + constraints       | ⚠️ Good      | Enum values fixed to UPPERCASE for Neon compatibility  |
| Pydantic schemas               | ✅ Excellent | Added `field_serializer` + `field_validator` for enums |
| Repository layer               | ✅ Excellent | Dict key case fix in `count_by_status`                 |
| Service layer / business rules | ✅ Excellent | None                                                   |
| FastAPI routers                | ✅ Excellent | Added missing `seed_router` import                     |
| Intent parser                  | ⚠️ Good      | Confidence score tuning for 2 handlers                 |
| Test suite (137 tests)         | ✅ Excellent | SQLite isolation strategy (`:memory:` → file)          |
| Frontend components            | ✅ Excellent | Added `onClick` to `CardProps`                         |
| Neon migration                 | ✅ Excellent | FK ordering approach (no `session_replication_role`)   |
| Deployment (Render + Netlify)  | ✅ Excellent | `--proxy-headers` flag, `.env.production` file         |
| AI agent (OpenAI SDK)          | ✅ Excellent | None — full rewrite generated correctly                |

**Overall: ~95% of code generated correctly by AI. 5% required targeted manual fixes.**

---

## How Correctness Was Verified

1. **Backend:** `pytest tests/ -v` — 137/137 tests pass (2 skipped: live Grok, require `XAI_API_KEY`)
2. **Frontend:** `npm run build` — TypeScript + Craco/Webpack bundle with 0 errors
3. **Neon connectivity:** `test_health.py` verifies live connection, schema integrity, and exact row counts
4. **Enum fix:** Verified by inspecting Neon `pg_enum` table and testing INSERT/SELECT round-trips
5. **AI Agent:** Rule-based fallback works offline; Grok activates when `XAI_API_KEY` is set in Render env vars
6. **Business rules:** All 8 rules verified via dedicated edge-case tests
