# Ethara Seat Allocation & Project Mapping System

> A full-stack application managing seat allocation for ~5,000 employees across floors, zones, and projects — with an AI assistant powered by Grok (xAI) querying live Neon PostgreSQL data.

---

## Table of Contents

- [Tech Stack & Rationale](#tech-stack--rationale)
- [SOLID Principles](#solid-principles)
- [Seat Allocation Algorithm](#seat-allocation-algorithm)
- [TDD Approach](#tdd-approach)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)

---

## Tech Stack & Rationale

| Layer        | Technology                                          | Why                                                                         |
| ------------ | --------------------------------------------------- | --------------------------------------------------------------------------- |
| Frontend     | React 19 + TypeScript + Craco/Webpack               | Type-safe components, Radix UI primitives, Framer Motion animations         |
| Styling      | Tailwind CSS + Shadcn tokens                        | Rapid dark-theme implementation matching Ethara brand palette               |
| State        | TanStack React Query                                | Server-state caching with auto-refetch — critical for live dashboards       |
| Charts       | Recharts                                            | Lightweight, composable bar/pie charts                                      |
| Backend      | Python FastAPI                                      | Auto-generates Swagger at `/docs`, async-first, Pydantic validation         |
| ORM          | SQLAlchemy 2.0                                      | Repository pattern, supports both SQLite (dev) and PostgreSQL (prod)        |
| Database     | Neon PostgreSQL (production) / SQLite (dev)         | Row-level locking prevents concurrent duplicate seat allocation             |
| Migrations   | Alembic                                             | Schema versioned alongside code                                             |
| AI Assistant | Rule-based IntentParser + Grok (xAI) via OpenAI SDK | Works offline; Grok queries live Neon data via tool-calling when key is set |
| Deployment   | Backend: Render · Frontend: Netlify                 | Zero-downtime deploys, free tier, automatic GitHub integration              |

---

## SOLID Principles

### Single Responsibility (SRP)

- `EmployeeRepository` — only employee DB queries
- `SeatAllocationService` — only allocation business logic
- `AIAssistantService` — only NLP query resolution
- `IntentParser` — only intent classification
- `AIAgent` — only LLM orchestration and tool dispatch

### Open/Closed (OCP)

- `IntentParser` uses a **Strategy pattern** — new `IntentHandler` subclasses added without touching existing code
- AI provider selection in `_get_client_and_source()` — add a new provider without changing the call site

### Liskov Substitution (LSP)

- `BaseRepository[T]` — all concrete repositories are fully substitutable via the generic interface

### Interface Segregation (ISP)

- Pydantic schemas (`EmployeeCreate` vs `EmployeeUpdate` vs `EmployeeResponse`) separate read/write contracts
- `AIQuery` schema is distinct from `AIResponse`

### Dependency Inversion (DIP)

- Services depend on repository abstractions, not concrete SQLAlchemy classes
- FastAPI `Depends()` wires implementations at runtime
- `get_settings()` injected via `lru_cache`

---

## Seat Allocation Algorithm

**Algorithm: Proximity-Based Greedy with Zone Fallback**

```
Input: employee with project_id

1. If specific seat_id provided:
   a. Validate seat exists
   b. Check status != reserved, != maintenance  (Rule 4)
   c. Check no active allocation on seat        (Rule 2)
   d. Allocate

2. Auto-assign (no seat_id):
   a. Find all active allocations for employee's project
   b. Determine majority floor + zone of project team
   c. Score all available seats:
      - +3 if same zone as team
      - +2 if same floor as team
   d. Select highest-scored seat
   e. Fallback: any available seat if team has no existing seats

3. Guard: one active allocation per employee   (Rule 1)
4. On allocation: seat.status → OCCUPIED
5. On release:    seat.status → AVAILABLE      (Rule 3)
```

**Why Greedy + Proximity:**

- O(n) scoring over available seats — fast enough for 5,500 seats in <5ms
- Keeps project teams physically co-located, improving collaboration
- Zone fallback ensures new joiners are never left unallocated

---

## TDD Approach

**Red → Green → Refactor**. False/edge cases written before implementation.

Edge cases covered:

- Allocate to already-occupied seat → `409 Conflict`
- Allocate to reserved seat → `403 Forbidden`
- Employee already has active seat → `409 Conflict`
- Release when no active allocation → `400 Bad Request`
- Allocate to nonexistent employee → `404`
- Create duplicate seat location → `422`
- Allocate maintenance seat → `403`
- No available seats anywhere → `404`
- Duplicate employee email → `422`
- Empty/short AI query → `422`
- AI with no API key → graceful rule-based fallback

**Test results: 137 passed, 2 skipped (live Grok — requires `XAI_API_KEY`)**

```bash
cd backend
python -m pytest tests/ -v
# === 137 passed, 2 skipped in ~2m ===
```

---

## Directory Structure

```
Seat-Allocation-and-Project-mapping-system/
├── README.md
├── PLAN.md
├── UPDATES.md
├── AI_PROMPTS.md
├── .env.example
├── docker-compose.yml
│
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point, CORS, rate limiting
│   │   ├── config.py             # Pydantic BaseSettings (all env vars)
│   │   ├── database.py           # SQLAlchemy engine + session factory
│   │   ├── dependencies.py       # JWT auth, bcrypt, get_current_user
│   │   ├── limiter.py            # slowapi rate limiter (per-IP)
│   │   ├── models/               # ORM models (UPPERCASE enums matching Neon)
│   │   ├── schemas/              # Pydantic schemas (lowercase serialisation)
│   │   ├── repositories/         # DB access layer
│   │   ├── services/
│   │   │   ├── ai_agent.py       # OpenAI SDK tool-calling agent (Grok/OpenAI/Gemini)
│   │   │   ├── ai_assistant_service.py
│   │   │   ├── employee_service.py
│   │   │   ├── seat_allocation_service.py
│   │   │   └── dashboard_service.py
│   │   ├── routers/
│   │   └── utils/
│   │       ├── intent_parser.py  # Rule-based NLP fallback
│   │       └── seed_data.py
│   ├── tests/                    # 137 TDD tests
│   │   ├── conftest.py
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
│   │   └── services/api.ts       # Axios client (REACT_APP_API_URL)
│   ├── .env.production           # REACT_APP_API_URL for Netlify builds
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
| `POST` | `/auth/signup` | Register a new administrator account |
| `POST` | `/auth/login`  | Log in and retrieve JWT access token |
| `GET`  | `/auth/me`     | Fetch active logged-in user profile  |

### Employees

| Method   | Endpoint          | Description                                                                                   |
| -------- | ----------------- | --------------------------------------------------------------------------------------------- |
| `POST`   | `/employees`      | Create employee (auto-generates ETH-XXXXX code)                                               |
| `GET`    | `/employees`      | List with filters: `q`, `project_id`, `status`, `department`, `has_seat`, `page`, `page_size` |
| `GET`    | `/employees/{id}` | Get employee with seat + project info                                                         |
| `PUT`    | `/employees/{id}` | Update employee                                                                               |
| `DELETE` | `/employees/{id}` | Deactivate employee (soft delete)                                                             |

### Projects

| Method | Endpoint                   | Description                                   |
| ------ | -------------------------- | --------------------------------------------- |
| `POST` | `/projects`                | Create project                                |
| `GET`  | `/projects`                | List projects (`active_only=true` by default) |
| `GET`  | `/projects/{id}`           | Get project with employee + seat counts       |
| `PUT`  | `/projects/{id}`           | Update project                                |
| `GET`  | `/projects/{id}/employees` | List all employees in project                 |

### Seats

| Method | Endpoint           | Description                                                       |
| ------ | ------------------ | ----------------------------------------------------------------- |
| `POST` | `/seats`           | Create seat                                                       |
| `GET`  | `/seats`           | List with filters: `floor`, `zone`, `status`, `page`, `page_size` |
| `GET`  | `/seats/{id}`      | Get seat with current occupant                                    |
| `PUT`  | `/seats/{id}`      | Update seat details/status                                        |
| `GET`  | `/seats/available` | List available seats (optional `floor`, `zone`)                   |
| `GET`  | `/seats/suggest`   | Suggest seats by project proximity (`project_id`, `count`)        |
| `POST` | `/seats/allocate`  | Allocate seat (`employee_id`, optional `seat_id`)                 |
| `POST` | `/seats/release`   | Release seat (`employee_id`)                                      |

### Dashboard

| Method | Endpoint                         | Description                                            |
| ------ | -------------------------------- | ------------------------------------------------------ |
| `GET`  | `/dashboard/summary`             | Totals: employees, seats, occupied, available, pending |
| `GET`  | `/dashboard/project-utilization` | Per-project allocation breakdown                       |
| `GET`  | `/dashboard/floor-utilization`   | Per-floor occupancy with rates                         |

### AI Assistant

| Method | Endpoint    | Description                                                               |
| ------ | ----------- | ------------------------------------------------------------------------- |
| `POST` | `/ai/query` | Natural language query `{ "query": "...", "session_id": "..." }` (10/min) |

### Dev / Health

| Method | Endpoint  | Description                                             |
| ------ | --------- | ------------------------------------------------------- |
| `POST` | `/seed`   | Seed database (idempotent, requires auth token)         |
| `GET`  | `/health` | Health check — `{"status":"healthy","version":"1.0.0"}` |
| `GET`  | `/docs`   | Swagger UI                                              |
| `GET`  | `/redoc`  | ReDoc UI                                                |

---

## Getting Started

### Local Development (no Docker)

**Prerequisites:** Python 3.11+, Node.js 18+

#### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Copy env and set DATABASE_URL
cp ../.env.example .env
# Edit .env — set DATABASE_URL to your Neon connection string

uvicorn app.main:app --reload --port 8000
```

Backend: http://localhost:8000 · Swagger: http://localhost:8000/docs

#### Frontend

```bash
cd frontend
npm install
npm start        # http://localhost:3000
```

---

## Running Tests

```bash
cd backend

# Run all 137 tests
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# Run a specific file
python -m pytest tests/test_seats.py -v

# Run only edge/false-case tests
python -m pytest tests/ -v -k "EdgeCase"

# Run with live Grok API (requires key)
XAI_API_KEY=xai-... python -m pytest tests/test_ai_agent_grok.py -k "Live" -v
```

Expected: **137 passed, 2 skipped**

---

## Environment Variables

Copy `.env.example` to `backend/.env`:

| Variable              | Default                                     | Description                                                    |
| --------------------- | ------------------------------------------- | -------------------------------------------------------------- |
| `DATABASE_URL`        | `sqlite:///./ethara_seats.db`               | Neon PostgreSQL URL in production                              |
| `JWT_SECRET_KEY`      | _(auto-generated per restart)_              | Set explicitly in production so tokens survive restarts        |
| `XAI_API_KEY`         | _(empty)_                                   | **Primary** — enables Grok (grok-3-mini, free at console.x.ai) |
| `GROK_API_KEY`        | _(empty)_                                   | Alias for `XAI_API_KEY`                                        |
| `OPENAI_API_KEY`      | _(empty)_                                   | Fallback if no Grok key — enables GPT-4o                       |
| `GEMINI_API_KEY`      | _(empty)_                                   | Last-resort fallback — enables Gemini 2.0 Flash                |
| `GROK_MODEL`          | `grok-3-mini`                               | xAI model name                                                 |
| `ALLOWED_ORIGINS_RAW` | `https://ethara-frontend12.netlify.app,...` | Comma-separated CORS origins                                   |
| `BCRYPT_ROUNDS`       | `12`                                        | Lower to `10` for faster local dev                             |

AI provider priority: **Grok (xAI) → OpenAI → Gemini**. Only one key needed.

---

## Deployment

| Service  | Platform | URL                                      |
| -------- | -------- | ---------------------------------------- |
| Backend  | Render   | https://ethara-backend-xnma.onrender.com |
| Frontend | Netlify  | https://ethara-frontend12.netlify.app    |
| Database | Neon     | PostgreSQL 16 (ap-southeast-1)           |

### Render (backend)

Required environment variables in Render dashboard:

```
DATABASE_URL=postgresql://...neon.tech/neondb?sslmode=require
JWT_SECRET_KEY=<64-char hex>
XAI_API_KEY=xai-...
ALLOWED_ORIGINS_RAW=https://ethara-frontend12.netlify.app
```

Start command:

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "*"
```

### Netlify (frontend)

Build command: `npm run build`  
Publish directory: `frontend/build`  
Environment variable: `REACT_APP_API_URL=https://ethara-backend-xnma.onrender.com`

---

## Business Rules Enforced

| #   | Rule                                      | Enforcement                           |
| --- | ----------------------------------------- | ------------------------------------- |
| 1   | One employee → one active seat            | Service layer + 409 error             |
| 2   | One seat → one active employee            | DB query check + 409 error            |
| 3   | Released seats become AVAILABLE           | `release_allocation()` updates status |
| 4   | RESERVED seats cannot be allocated        | Service check + 403 error             |
| 5   | New joiners prioritized near project team | Proximity greedy algorithm            |
| 6   | Duplicate email not allowed               | DB unique constraint + 422 error      |
| 7   | Duplicate seat location not allowed       | DB unique constraint + 422 error      |
| 8   | Dashboard updates after every change      | TanStack Query cache invalidation     |

---

## Design System

| Token              | Value     | Usage                         |
| ------------------ | --------- | ----------------------------- |
| `ethara-bg`        | `#0a0a14` | Page background               |
| `ethara-card`      | `#12121f` | Card backgrounds              |
| `ethara-border`    | `#1e1e3a` | Borders                       |
| `ethara-primary`   | `#c026d3` | Magenta — CTAs, active states |
| `ethara-secondary` | `#7c3aed` | Violet — gradients, secondary |
| `ethara-success`   | `#10b981` | Available status              |
| `ethara-warning`   | `#f59e0b` | Reserved status               |
| `ethara-error`     | `#ef4444` | Occupied / error status       |
