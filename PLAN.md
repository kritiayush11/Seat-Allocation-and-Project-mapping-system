# Ethara Seat Allocation & Project Mapping System — PLAN

## Overview

A full-stack application managing seat allocation for ~5,000 employees at Ethara across multiple floors, zones, and projects. Includes an AI assistant (Grok via xAI) that queries live Neon PostgreSQL data using tool-calling.

---

## Technology Stack & Rationale

### Frontend: React 19 + TypeScript + Craco/Webpack + Tailwind CSS

- React + TypeScript gives type safety across the entire component tree
- Craco/Webpack: standard build pipeline with `react-scripts` conventions
- Tailwind CSS: rapid dark-theme implementation matching Ethara brand (deep navy + magenta)
- TanStack React Query: server-state caching with auto-refetch — critical for live dashboards

### Backend: Python FastAPI

- Auto-generates Swagger docs at `/docs`
- Pydantic models enforce schema at every API boundary (Open/Closed Principle)
- SQLAlchemy ORM abstracts the database, supporting both SQLite (dev) and PostgreSQL (prod)
- slowapi rate limiting: per-IP, Fixed Window Counter

### Database: Neon PostgreSQL (production) / SQLite (development)

- PostgreSQL row-level locking prevents duplicate seat allocation under concurrent requests
- Neon: serverless PostgreSQL, free tier, hosted in `ap-southeast-1`
- IMPORTANT: Neon enum types are UPPERCASE (`AVAILABLE`, `OCCUPIED`, `ACTIVE`) — all models must match exactly

### AI Assistant: Rule-based IntentParser + Grok (xAI) via OpenAI SDK

- Rule-based IntentParser covers 95% of queries deterministically — works offline with zero latency
- When `XAI_API_KEY` is set: Grok `grok-3-mini` (free tier) takes over all queries
- Direct OpenAI SDK with tool-calling loop — no LangChain dependency
- Provider priority: **Grok (xAI) → OpenAI → Gemini**
- DB tools: `get_employee_seat`, `search_seats`, `get_seat_utilization`, `search_projects`, `find_neighbors`
- Chat memory persisted in `chat_messages` table per `session_id`

### Deployment

- Backend: **Render** (Python web service, free tier)
- Frontend: **Netlify** (static build, free tier)
- Database: **Neon** (PostgreSQL 16, free tier)

---

## SOLID Principles Applied

### Single Responsibility (SRP)

- `EmployeeRepository` — only employee DB queries
- `SeatAllocationService` — only allocation business logic
- `AIAssistantService` — only query routing (rule-based or agent)
- `AIAgent` — only LLM orchestration and tool dispatch
- `IntentParser` — only intent classification

### Open/Closed (OCP)

- `IntentParser` uses a Strategy pattern — new `IntentHandler` subclasses added without modifying core
- AI provider selection in `_get_client_and_source()` — add providers without changing call sites

### Liskov Substitution (LSP)

- `BaseRepository[T]` — all concrete repositories are fully substitutable via the generic interface

### Interface Segregation (ISP)

- Pydantic schemas separate read/write contracts: `EmployeeCreate` vs `EmployeeUpdate` vs `EmployeeResponse`
- `AIQuery` (input) is separate from `AIResponse` (output)

### Dependency Inversion (DIP)

- Services depend on repository abstractions, not raw SQLAlchemy sessions
- FastAPI `Depends()` wires implementations at runtime
- `get_settings()` injected via `lru_cache`

---

## Seat Allocation Algorithm

### Primary: Proximity-Based Greedy with Zone Fallback

```
1. INPUT: new employee with project_id

2. If specific seat_id provided:
   a. Validate seat exists
   b. Check status != RESERVED, != MAINTENANCE  (Rule 4)
   c. Check no active allocation on seat         (Rule 2)
   d. Allocate

3. Auto-assign (no seat_id):
   a. Find all active allocations for employee's project
   b. Determine majority floor + zone of project team
   c. Score all AVAILABLE seats:
      - +3 if same zone as team
      - +2 if same floor as team
   d. Select highest-scored seat
   e. Fallback: any available seat if team has no existing seats

4. Guard: one active allocation per employee    (Rule 1)
5. On allocation: seat.status → OCCUPIED
6. On release:    seat.status → AVAILABLE       (Rule 3)
```

**Why Greedy + Proximity:**

- O(n) scoring over available seats — <5ms for 5,500 seats
- Keeps project teams physically co-located
- Zone fallback ensures new joiners are never left unallocated

---

## TDD Approach

**Red → Green → Refactor**. Edge/false cases written before implementation.

```
Current test count: 137 passed, 2 skipped
```

Edge cases covered:

- Allocate to already-occupied seat → `409 Conflict`
- Allocate to RESERVED seat → `403 Forbidden`
- Employee already has active seat → `409 Conflict`
- Release when no active allocation → `400 Bad Request`
- Nonexistent employee → `404`
- Duplicate seat location → `422`
- Allocate MAINTENANCE seat → `403`
- No available seats → `404`
- Duplicate employee email → `422`
- Empty/short AI query → `422`
- AI with no API key → rule-based fallback

```bash
cd backend
python -m pytest tests/ -v
# 137 passed, 2 skipped
```

---

## Directory Structure

```
Seat-Allocation-and-Project-mapping-system/
├── README.md
├── PLAN.md                        # This file
├── UPDATES.md
├── AI_PROMPTS.md
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point, CORS, rate limiting
│   │   ├── config.py             # Pydantic BaseSettings (all env vars)
│   │   ├── database.py           # SQLAlchemy engine + session factory
│   │   ├── dependencies.py       # JWT auth, bcrypt, get_current_user
│   │   ├── limiter.py            # slowapi per-IP rate limiter
│   │   ├── models/               # ORM models (UPPERCASE enums — Neon compatible)
│   │   │   ├── employee.py       # EmployeeStatus: ACTIVE, INACTIVE, ON_LEAVE, TERMINATED
│   │   │   ├── project.py        # ProjectStatus: ACTIVE, INACTIVE, ARCHIVED
│   │   │   ├── seat.py           # SeatStatus: AVAILABLE, OCCUPIED, RESERVED, MAINTENANCE
│   │   │   ├── seat_allocation.py# AllocationStatus: ACTIVE, RELEASED, TRANSFERRED
│   │   │   ├── user.py
│   │   │   └── chat_message.py   # Conversation history for AI agent
│   │   ├── schemas/              # Pydantic schemas (lowercase serialisation for API compat)
│   │   ├── repositories/         # DB access layer (BaseRepository[T] + entity repos)
│   │   ├── services/
│   │   │   ├── ai_agent.py       # OpenAI SDK tool-calling agent (Grok/OpenAI/Gemini)
│   │   │   ├── ai_assistant_service.py # Routes to agent or rule-based fallback
│   │   │   ├── employee_service.py
│   │   │   ├── seat_allocation_service.py
│   │   │   └── dashboard_service.py
│   │   ├── routers/
│   │   └── utils/
│   │       ├── intent_parser.py  # Rule-based NLP (Strategy/OCP pattern)
│   │       └── seed_data.py      # 5,000 employee + 5,500 seat generator
│   │
│   ├── tests/                    # 137 TDD tests
│   │   ├── conftest.py           # Fixtures: file-based SQLite per test
│   │   ├── test_employees.py
│   │   ├── test_seats.py
│   │   ├── test_projects.py
│   │   ├── test_dashboard.py
│   │   ├── test_ai_assistant.py
│   │   ├── test_ai_agent_grok.py # Grok/OpenAI SDK agent tests
│   │   ├── test_auth.py
│   │   ├── test_rate_limiting.py
│   │   ├── test_health.py        # Neon connectivity + schema integrity
│   │   └── test_security_tdd.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AIAssistant.tsx   # Chat UI, session_id, voice dictation
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Employees.tsx
│   │   │   ├── Seats.tsx
│   │   │   └── Projects.tsx
│   │   ├── services/api.ts       # Axios client (REACT_APP_API_URL)
│   │   └── types/index.ts
│   ├── .env.production           # REACT_APP_API_URL → Render backend URL
│   └── package.json
│
└── nginx/
    └── nginx.conf
```

---

## API Endpoints

### Authentication

| Method | Endpoint       | Description                          |
| ------ | -------------- | ------------------------------------ |
| POST   | `/auth/signup` | Register a new administrator account |
| POST   | `/auth/login`  | Log in and retrieve JWT access token |
| GET    | `/auth/me`     | Fetch active logged-in user profile  |

### Employees

| Method | Endpoint          | Description                                          |
| ------ | ----------------- | ---------------------------------------------------- |
| POST   | `/employees`      | Create employee (auto-generates ETH-XXXXX code)      |
| GET    | `/employees`      | List with filters: `q`, `project_id`, `status`, etc. |
| GET    | `/employees/{id}` | Get employee with seat + project info                |
| PUT    | `/employees/{id}` | Update employee                                      |
| DELETE | `/employees/{id}` | Deactivate employee (soft delete)                    |

### Projects

| Method | Endpoint                   | Description                                   |
| ------ | -------------------------- | --------------------------------------------- |
| POST   | `/projects`                | Create project                                |
| GET    | `/projects`                | List projects (`active_only=true` by default) |
| GET    | `/projects/{id}`           | Get project with employee + seat counts       |
| PUT    | `/projects/{id}`           | Update project                                |
| GET    | `/projects/{id}/employees` | List all employees in project                 |

### Seats

| Method | Endpoint           | Description                                  |
| ------ | ------------------ | -------------------------------------------- |
| POST   | `/seats`           | Create seat                                  |
| GET    | `/seats`           | List with filters: `floor`, `zone`, `status` |
| GET    | `/seats/{id}`      | Get seat with current occupant               |
| PUT    | `/seats/{id}`      | Update seat                                  |
| GET    | `/seats/available` | List available seats                         |
| GET    | `/seats/suggest`   | Suggest seats by proximity (`project_id`)    |
| POST   | `/seats/allocate`  | Allocate seat (rate-limited: 20/min)         |
| POST   | `/seats/release`   | Release seat                                 |

### Dashboard

| Method | Endpoint                         | Description                      |
| ------ | -------------------------------- | -------------------------------- |
| GET    | `/dashboard/summary`             | Total counts and utilisation     |
| GET    | `/dashboard/project-utilization` | Per-project allocation breakdown |
| GET    | `/dashboard/floor-utilization`   | Per-floor occupancy rates        |

### AI Assistant

| Method | Endpoint    | Description                                                                |
| ------ | ----------- | -------------------------------------------------------------------------- |
| POST   | `/ai/query` | Natural language query, `{ "query": "...", "session_id": "..." }` (10/min) |

---

## Neon Enum Compatibility Note

All SQLAlchemy enum models use UPPERCASE values to match Neon's existing enum types:

```python
class SeatStatus(str, enum.Enum):
    AVAILABLE   = "AVAILABLE"
    OCCUPIED    = "OCCUPIED"
    RESERVED    = "RESERVED"
    MAINTENANCE = "MAINTENANCE"
```

API responses serialise these as lowercase via Pydantic `field_serializer`. API inputs accept both cases via `field_validator` with `.upper()` normalisation.

**Do not change enum values to lowercase** — this will break all Neon writes.

---

## Seed Data

- 5,001 employees across 11 projects
- 5 floors (1–5), zones A–J per floor
- 5,500 seats total: ~4,951 occupied, ~500 available, ~100 reserved, ~50 maintenance
- 50 employees with no seat (pending allocation)
