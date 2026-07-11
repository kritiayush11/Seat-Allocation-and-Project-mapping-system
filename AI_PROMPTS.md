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
- SOLID principle mapping to concrete files (SRP per layer, DIP via FastAPI Depends, OCP via Strategy pattern for intent parser)
- Proximity-based greedy algorithm with zone fallback documented
- TDD Red→Green→Refactor workflow with edge cases first

**What AI generated incorrectly:**
- Initial plan suggested a separate `interfaces/` directory which added unnecessary complexity; simplified to inline abstractions

**Manual fix:**
- Removed the standalone `interfaces/` directory, instead kept abstract base classes inline with their concrete implementations

---

## Prompt 2 — Database Design

**Prompt:**
> "Design SQLAlchemy ORM models for Employee, Project, Seat, and SeatAllocation. Include enums, unique constraints, relationships, and composite indexes for active allocation queries. Support both SQLite for dev and PostgreSQL for production."

**What AI generated correctly:**
- All four models with correct FK relationships and `back_populates`
- `SeatStatus` and `AllocationStatus` enums with proper string values
- Composite unique constraint on `(floor, zone, bay, seat_number)` preventing duplicate seats
- Composite indexes on `(employee_id, allocation_status)` and `(seat_id, allocation_status)` for fast active-allocation lookups
- SQLite WAL mode + foreign key pragma for dev performance

**What AI generated incorrectly:**
- Used deprecated `declarative_base()` from `sqlalchemy.ext.declarative` — should be `sqlalchemy.orm.declarative_base()` in SQLAlchemy 2.0

**Manual fix:**
- Kept the deprecated import with a comment noting the SQLAlchemy 2.0 path since the warning is non-breaking and `pydantic-settings` also shows a V2 warning

---

## Prompt 3 — Backend APIs

**Prompt:**
> "Create FastAPI routers for employees, projects, seats, dashboard, and AI assistant. Each router should delegate to its service class. Include Swagger documentation via docstrings. Add a /seed endpoint for demo data."

**What AI generated correctly:**
- All 5 router files with full endpoint coverage matching the assessment spec
- Proper HTTP status codes (201 for creates, 409 for conflicts, 403 for reserved seats, 422 for validation)
- Query parameter handling with type coercion
- Swagger docstrings on every endpoint

**What AI generated incorrectly:**
- Missing `seed_router` import in `routers/__init__.py` initially

**Manual fix:**
- Added `seed_router` to `__init__.py` and registered it in `main.py`

---

## Prompt 4 — Seat Allocation Logic

**Prompt:**
> "Implement the proximity-based greedy seat allocation algorithm. Score available seats +3 for same zone as project team, +2 for same floor. Enforce all 8 business rules with proper HTTP error codes. Prevent concurrent double-booking."

**What AI generated correctly:**
- `find_seats_near_project()` in `SeatRepository` correctly queries active allocations by project to find majority zone
- All 8 business rules enforced at service layer with correct status codes
- `create_allocation()` atomically updates both the `SeatAllocation` record and `Seat.status` in the same transaction

**What AI generated incorrectly:**
- `count_by_status()` initially returned `{str(SeatStatus.OCCUPIED): count}` which produces `"SeatStatus.OCCUPIED"` as the key instead of `"occupied"` — this caused dashboard counts to return 0

**Manual fix:**
- Changed to `status.value if hasattr(status, 'value') else str(status)` for proper enum value extraction
- Applied same fix to `floor_utilization()`

---

## Prompt 5 — AI Assistant

**Prompt:**
> "Build a rule-based intent parser using the Strategy/OCP pattern. Handlers: find_seat, find_project, available_seats, seat_utilization, allocate_seat, find_neighbors. Each handler has its own regex patterns and confidence score. Higher-specificity handlers should win over generic ones."

**What AI generated correctly:**
- 6 `IntentHandler` subclasses each with `matches()` and `parse()` methods
- Regex patterns for email extraction, floor/zone parsing, project name extraction
- `IntentParser` as orchestrator — iterates handlers, picks highest confidence result
- OpenAI GPT-4o fallback when `OPENAI_API_KEY` is set

**What AI generated incorrectly:**
- Initial handler order had `SeatLocationHandler` (confidence 0.9) before `SeatUtilizationHandler` (0.85) — queries like "how many seats occupied for Project Indigo" were matching `find_project` instead of `seat_utilization`
- `NeighborHandler` (0.75) was losing to `SeatLocationHandler` (0.9) for "sitting near" queries

**Manual fix:**
- Raised `SeatUtilizationHandler` confidence to 0.95 (it has more specific keywords like "how many", "utilization")
- Raised `NeighborHandler` confidence to 0.95 (its keywords "near me", "sitting near" are unambiguous)
- Tests confirmed: 69/69 passing after fix

---

## Prompt 6 — Frontend

**Prompt:**
> "Build a React + TypeScript + Vite frontend matching Ethara's brand: deep navy background (#0a0a14), magenta accent (#c026d3), hexagonal background pattern. Pages: Dashboard (stats + Recharts), Employees (CRUD table), Seats (grid + allocation), Projects (card grid), AI Assistant (chat UI). Use TanStack Query for server state."

**What AI generated correctly:**
- Tailwind config with full Ethara color palette
- All 5 pages with correct business flows
- Toast notification system with context provider
- Reusable `Table` + `Pagination` component with generic typing
- AI Assistant chat UI with intent + source metadata display
- `Badge` component with correct status → CSS class mapping

**What AI generated incorrectly:**
- `Card` component was missing the `onClick` prop in its TypeScript interface, causing a build error in `Projects.tsx`

**Manual fix:**
- Added `onClick?: () => void` to `CardProps` interface and wired it to the `div`

---

## Prompt 7 — Testing (TDD)

**Prompt:**
> "Write a TDD test suite using pytest. Write FALSE/edge case tests first (before implementation). Test all 8 business rules, intent parser accuracy, and dashboard aggregations. Use per-test SQLite database isolation."

**What AI generated correctly:**
- 69 tests covering employees, seats, projects, dashboard, and AI assistant
- False cases written before happy paths per TDD Red→Green pattern
- Fixtures for `sample_project`, `sample_employee`, `sample_seat`, `reserved_seat`, `occupied_seat`
- Clear test class separation: `TestXxxEdgeCases` vs `TestXxxHappyPath`

**What AI generated incorrectly:**
- First approach used `sqlite:///:memory:` — each SQLAlchemy connection creates a separate in-memory DB, so tables created in the `db_engine` fixture weren't visible to the `TestClient`'s sessions
- Result: `no such table: employees` errors for 31 tests

**Manual fix:**
- Switched to a temp file-backed SQLite DB per test (`tempfile.mkstemp(suffix=".db")`)
- This ensures all connections within a test see the same schema and committed data
- 69/69 tests passing after fix

---

## Prompt 8 — Debugging

**Prompt:**
> "Tests failing with 'no such table: employees'. Root cause analysis and fix."

**Diagnosis process:**
1. Checked if `Base.metadata.create_all(bind=db_engine)` was being called — it was
2. Confirmed the issue was SQLite `:memory:` creating a separate DB per connection
3. Confirmed the `TestClient` creates its own connection pool separate from the test fixture's session
4. Solution: use a named temp file so all connections share one physical DB

**What AI debugged correctly:**
- Identified the root cause (SQLite in-memory connection isolation) after two failed attempts at patching
- Chose a fundamentally different approach (file-based) rather than incremental patches

---

## Prompt 9 — Deployment

**Prompt:**
> "Create Docker Compose with PostgreSQL, FastAPI backend, React frontend built with nginx, and an nginx reverse proxy. Backend should wait for DB health check before starting."

**What AI generated correctly:**
- `docker-compose.yml` with `depends_on: condition: service_healthy` for PostgreSQL
- Multi-stage Dockerfile for frontend (build stage + nginx serve stage)
- Backend Dockerfile with non-root user for security
- Nginx reverse proxy config routing `/api/` to backend, `/` to frontend

**What AI generated incorrectly:**
- Backend Dockerfile `COPY . .` runs before the virtual env is activated in the container context; solved by using `CMD` with explicit uvicorn path

**Manual fix:**
- Used `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` without shell activation

---

## Prompt 10 — Refactoring

**Prompt:**
> "Identify and fix the enum string key bug in count_by_status() returning 0 for occupied_seats on the dashboard."

**Diagnosis:**
- `Seat.status` is a `SeatStatus` enum — SQLAlchemy returns enum objects from GROUP BY queries
- `str(SeatStatus.OCCUPIED)` produces `"SeatStatus.OCCUPIED"` not `"occupied"`
- `count_map.get("occupied", 0)` always returns 0 because the key doesn't match

**Fix applied:**
```python
key = status.value if hasattr(status, "value") else str(status)
```

---

## Summary: AI vs Manual

| Area | AI Accuracy | Manual Intervention |
|------|-------------|-------------------|
| Architecture / SOLID design | ✅ Excellent | Minor simplification (removed `interfaces/` dir) |
| ORM models + constraints | ✅ Excellent | None |
| Pydantic schemas | ✅ Excellent | None |
| Repository layer | ✅ Excellent | None |
| Service layer / business rules | ✅ Excellent | Enum key fix in `count_by_status` |
| FastAPI routers | ✅ Excellent | Added missing `seed_router` import |
| Intent parser | ⚠️ Good | Confidence score tuning for 2 handlers |
| Test suite | ⚠️ Good | SQLite isolation strategy change (`:memory:` → file) |
| Frontend components | ✅ Excellent | Added `onClick` to `CardProps` |
| Docker / deployment | ✅ Excellent | None |

**Overall: ~95% of code generated correctly by AI. 5% required targeted manual fixes.**

---

## How Correctness Was Verified

1. **Backend**: `pytest tests/ -v` — 69/69 tests pass
2. **Frontend**: `npm run build` — TypeScript compilation + Vite bundle succeeds with 0 errors
3. **Integration**: Backend started with `uvicorn`, `/seed` called, Swagger at `/docs` tested manually
4. **AI Assistant**: Sent 6 sample queries via Swagger, verified correct intent classification
5. **Dashboard**: Seeded data, verified counts match expected values (5000 employees, 5500 seats, ~100 reserved)
6. **Business rules**: Each of the 8 rules verified via dedicated edge-case test
