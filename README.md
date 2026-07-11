# Ethara Seat Allocation & Project Mapping System

> A full-stack application managing seat allocation for ~5,000 employees across floors, zones, and projects. Built with FastAPI, React, and an AI assistant.

---

## Table of Contents

- [Tech Stack & Rationale](#tech-stack--rationale)
- [SOLID Principles](#solid-principles)
- [Seat Allocation Algorithm](#seat-allocation-algorithm)
- [TDD Approach](#tdd-approach)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Docker Deployment](#docker-deployment)
- [Viewing & Managing the Database](#viewing--managing-the-database)
- [ORM & Migrations (SQLAlchemy + Alembic)](#orm--migrations-sqlalchemy--alembic)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)

---

## Tech Stack & Rationale

| Layer        | Technology                                                   | Why                                                                              |
| ------------ | ------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| Frontend     | React 19 + TypeScript + Craco/Webpack                        | Type-safe components, Radix UI primitives, Framer Motion animations              |
| Styling      | Tailwind CSS + Shadcn tokens                                 | Rapid dark-theme implementation matching Ethara brand palette                    |
| State        | TanStack React Query                                         | Server-state caching with auto-refetch — critical for live dashboards            |
| Charts       | Recharts                                                     | Lightweight, composable bar/pie charts with no canvas complexity                 |
| Backend      | Python FastAPI                                               | Auto-generates Swagger at `/docs`, async-first, Pydantic validation              |
| ORM          | SQLAlchemy 2.0                                               | Repository pattern, supports both SQLite (dev) and PostgreSQL (prod)             |
| Database     | PostgreSQL / SQLite                                          | Row-level locking prevents concurrent duplicate seat allocation                  |
| Migrations   | Alembic                                                      | Schema versioned alongside code                                                  |
| AI Assistant | Rule-based IntentParser + LangChain (Gemini / Grok / OpenAI) | Works offline, deterministic for 95% of queries, upgrades to LLM when key is set |
| Deployment   | Docker Compose                                               | Single command brings up DB + backend + frontend + nginx                         |

---

## SOLID Principles

### Single Responsibility (SRP)

- `EmployeeRepository` — only employee DB queries
- `SeatAllocationService` — only allocation business logic
- `AIAssistantService` — only NLP query resolution
- `IntentParser` — only intent classification
- Each React component renders one concern (e.g., `Badge`, `SeatCard`, `Navbar`)

### Open/Closed (OCP)

- `IntentParser` uses a **Strategy pattern** — new `IntentHandler` subclasses can be added to `_handlers` list without touching existing code
- Seat allocation strategies (proximity-first, zone-first) are composable

### Liskov Substitution (LSP)

- `BaseRepository[T]` — all concrete repositories (`EmployeeRepository`, `SeatRepository`, etc.) are fully substitutable via the generic interface

### Interface Segregation (ISP)

- `IEmployeeReader` and `IEmployeeWriter` are conceptually separate — the service layer only requests what it needs via dependency injection
- Pydantic schemas (`EmployeeCreate` vs `EmployeeUpdate` vs `EmployeeResponse`) separate read/write contracts

### Dependency Inversion (DIP)

- Services depend on repository abstractions, not concrete SQLAlchemy classes
- FastAPI `Depends()` wires implementations at runtime
- `get_settings()` is injected via `lru_cache`, not imported as a global

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
4. Guard: DB transaction with row lock          (prevents concurrent booking)
5. On allocation: seat.status → occupied
6. On release:    seat.status → available       (Rule 3)
```

**Why Greedy + Proximity:**

- O(n) scoring over available seats — fast enough for 5,500 seats in < 5ms
- Keeps project teams physically co-located, improving collaboration
- Zone fallback ensures new joiners are never left unallocated

---

## TDD Approach

**Red → Green → Refactor**. False/edge cases written before implementation.

Edge cases tested first:

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

**Test results: 82/82 passing**

```bash
cd backend
# With local venv
.venv/bin/python3 -m pytest tests/ -v
# === 82 passed in ~4s ===
```

---

## Directory Structure

```
Seat-Allocation-and-Project-mapping-system/
├── PLAN.md                        # Architecture plan and tech decisions
├── README.md                      # This file
├── AI_PROMPTS.md                  # AI usage documentation
├── docker-compose.yml             # Full stack deployment
├── .env.example                   # Environment variable template
│
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point, CORS, router registration
│   │   ├── config.py             # Pydantic BaseSettings
│   │   ├── database.py           # SQLAlchemy engine + session factory
│   │   ├── models/               # ORM models (Employee, Project, Seat, SeatAllocation)
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── repositories/         # DB access layer (BaseRepository + entity repos)
│   │   ├── services/             # Business logic layer
│   │   ├── routers/              # FastAPI route handlers
│   │   └── utils/
│   │       ├── intent_parser.py  # Rule-based NLP (Strategy pattern, OCP)
│   │       └── seed_data.py      # 5000 employee + 5500 seat generator
│   ├── tests/                    # TDD test suite (82 tests)
│   │   ├── conftest.py           # Fixtures with file-based SQLite isolation
│   │   ├── test_employees.py
│   │   ├── test_seats.py
│   │   ├── test_projects.py
│   │   ├── test_dashboard.py
│   │   └── test_ai_assistant.py
│   ├── migrations/               # Alembic migration files
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx              # React entry point
│   │   ├── App.tsx               # Router + QueryClient + ToastProvider
│   │   ├── index.css             # Tailwind + Ethara design tokens
│   │   ├── types/index.ts        # Shared TypeScript interfaces
│   │   ├── services/api.ts       # Axios API client for all endpoints
│   │   ├── hooks/                # React Query hooks (useEmployees, useSeats, etc.)
│   │   ├── components/
│   │   │   ├── layout/           # Navbar, Sidebar, Layout
│   │   │   └── ui/               # Button, Card, Badge, Table, Modal, SearchBar, Toast
│   │   └── pages/
│   │       ├── Dashboard.tsx     # Stats cards + bar/pie charts
│   │       ├── Employees.tsx     # Table + CRUD modals + seat allocation
│   │       ├── Seats.tsx         # Table + filters + allocate/release
│   │       ├── Projects.tsx      # Card grid + employee detail modal
│   │       └── AIAssistant.tsx   # Chat interface
│   ├── tailwind.config.js        # Ethara color palette
│   ├── craco.config.js           # Webpack/Craco build config
│   ├── Dockerfile
│   └── package.json
│
└── nginx/
    └── nginx.conf                # Reverse proxy (API → backend, / → frontend)
```

---

## API Endpoints

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

### Authentication

| Method | Endpoint       | Description                                 |
| ------ | -------------- | ------------------------------------------- |
| `POST` | `/auth/signup` | Register a new administrator account        |
| `POST` | `/auth/login`  | Log in and retrieve JWT access token        |
| `GET`  | `/auth/me`     | Fetch active logged-in user profile details |

### Dashboard

| Method | Endpoint                         | Description                                            |
| ------ | -------------------------------- | ------------------------------------------------------ |
| `GET`  | `/dashboard/summary`             | Totals: employees, seats, occupied, available, pending |
| `GET`  | `/dashboard/project-utilization` | Per-project allocation breakdown                       |
| `GET`  | `/dashboard/floor-utilization`   | Per-floor occupancy with rates                         |

### AI Assistant

| Method | Endpoint    | Description                                 |
| ------ | ----------- | ------------------------------------------- |
| `POST` | `/ai/query` | Natural language query `{ "query": "..." }` |

### Dev

| Method | Endpoint  | Description                                              |
| ------ | --------- | -------------------------------------------------------- |
| `POST` | `/seed`   | Seed database (idempotent, requires authorization token) |
| `GET`  | `/health` | Health check                                             |
| `GET`  | `/docs`   | Swagger UI                                               |
| `GET`  | `/redoc`  | ReDoc UI                                                 |

---

## Getting Started

### Option A — Docker (recommended, one command)

Requires Docker Desktop to be running.

```bash
# 1. Clone the repo
git clone https://github.com/kritiayush11/Seat-Allocation-and-Project-mapping-system.git
cd Seat-Allocation-and-Project-mapping-system

# 2. Start all services — PostgreSQL + FastAPI + React + Nginx
docker compose up --build

# 3. Seed the database (5,000 employees, 5,500 seats, 11 projects)
#    Get a token first:
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"admin","password":"adminpassword"}'
# Then seed (replace <token> with the access_token from above):
curl -X POST http://localhost:8000/seed \
  -H "Authorization: Bearer <token>"
```

Or use the Swagger UI at http://localhost:8000/docs — log in via `/auth/login`, click Authorize, then call `POST /seed`.

Services after startup:

| Service         | URL                         |
| --------------- | --------------------------- |
| App (via Nginx) | http://localhost            |
| Frontend direct | http://localhost:3000       |
| Backend API     | http://localhost:8000       |
| Swagger UI      | http://localhost:8000/docs  |
| ReDoc           | http://localhost:8000/redoc |
| PostgreSQL      | localhost:5432              |

Default login credentials (created automatically at first seed):

| Role  | Username | Password        |
| ----- | -------- | --------------- |
| Admin | `admin`  | `adminpassword` |
| HR    | `hr`     | `hrpassword`    |

---

### Option B — Local dev (no Docker)

**Prerequisites:** Python 3.11+, Node.js 18+

#### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Copy env (uses SQLite by default — no DB install needed)
cp ../.env.example .env

# Start the server
uvicorn app.main:app --reload --port 8000
```

Backend: http://localhost:8000 · Swagger: http://localhost:8000/docs

#### Seed the database

```bash
# Direct Python (works immediately, no token needed)
cd backend
python3 -m app.utils.seed_data
```

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

# Run all 82 tests
.venv/bin/python3 -m pytest tests/ -v

# With coverage report
.venv/bin/python3 -m pytest tests/ -v --cov=app --cov-report=term-missing

# Run a specific file
.venv/bin/python3 -m pytest tests/test_seats.py -v

# Run only edge/false-case tests
.venv/bin/python3 -m pytest tests/ -v -k "EdgeCase"

# Security tests only
.venv/bin/python3 -m pytest tests/test_security_tdd.py tests/test_auth.py -v
```

Expected: **82 passed**

---

## Docker Deployment

```bash
# Start everything
docker compose up --build

# Run in background (detached)
docker compose up --build -d

# View live logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend

# Stop all services
docker compose down

# Stop and delete volumes (wipes the PostgreSQL database — use with caution)
docker compose down -v

# Rebuild only the backend after a code change
docker compose up --build backend
```

---

## Viewing & Managing the Database

### PostgreSQL (Docker)

```bash
# Open an interactive psql shell in the running DB container
docker exec -it seat-allocation-and-project-mapping-system-db-1 \
  psql -U ethara -d ethara_seats

# Useful psql commands:
\dt                              -- list all tables
\d employees                     -- describe the employees table
SELECT COUNT(*) FROM employees;
SELECT COUNT(*) FROM seats WHERE status = 'occupied';
SELECT username, email, is_admin FROM users;
\q                               -- quit
```

#### GUI tools for PostgreSQL

Connect any GUI client to `localhost:5432`:

| Tool          | Platform            | Notes                         |
| ------------- | ------------------- | ----------------------------- |
| **TablePlus** | macOS/Windows       | Clean UI, free tier available |
| **DBeaver**   | macOS/Windows/Linux | Free, full-featured           |
| **pgAdmin 4** | Browser-based       | Official PostgreSQL tool      |
| **DataGrip**  | macOS/Windows/Linux | JetBrains IDE, paid           |

Connection details:

```
Host:     localhost
Port:     5432
Database: ethara_seats
User:     ethara
Password: ethara_secret
```

### SQLite (local dev)

The database file is `backend/ethara_seats.db` when running without Docker.

```bash
# CLI
sqlite3 backend/ethara_seats.db
.tables
SELECT COUNT(*) FROM employees;
.quit
```

GUI tools: **DB Browser for SQLite** (free, macOS/Windows/Linux) or **TablePlus**.

---

## ORM & Migrations (SQLAlchemy + Alembic)

### How the ORM works

This project uses **SQLAlchemy 2.0** with a **Repository pattern**:

```
HTTP Request
    → Router       (FastAPI — parses request, returns response)
    → Service      (business logic, enforces rules)
    → Repository   (DB queries via SQLAlchemy ORM)
    → Model        (ORM table class)
    → PostgreSQL / SQLite
```

Models live in `backend/app/models/`. Each model maps to a DB table:

```python
# backend/app/models/seat.py
class Seat(Base):
    __tablename__ = "seats"
    id          = Column(Integer, primary_key=True)
    floor       = Column(Integer, nullable=False)
    zone        = Column(String(1), nullable=False)
    seat_number = Column(String(20), unique=True)
    status      = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE)
```

Repositories in `backend/app/repositories/` wrap all raw SQL — services never query the DB directly (Dependency Inversion).

### Alembic migrations

Alembic tracks every schema change as a versioned migration file in `backend/migrations/versions/`.

```bash
cd backend
source .venv/bin/activate

# Check current migration state
alembic current

# See full migration history
alembic history --verbose

# Auto-generate a migration after changing a model
alembic revision --autogenerate -m "add index to employee email"

# Apply all pending migrations (upgrade to latest)
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Roll back to a specific revision ID
alembic downgrade <revision_id>
```

> In local dev (SQLite), tables are created automatically on startup via `Base.metadata.create_all()` — no migration needed. Alembic is for PostgreSQL and incremental schema updates.

### Adding a new model (step-by-step)

1. Create `backend/app/models/my_model.py` — define the SQLAlchemy class inheriting `Base`
2. Import it in `backend/app/models/__init__.py` so Alembic can detect it
3. Create `backend/app/repositories/my_model_repository.py` extending `BaseRepository`
4. Add service logic in `backend/app/services/`
5. Add routes in `backend/app/routers/` and register in `main.py`
6. Generate migration: `alembic revision --autogenerate -m "add my_model table"`
7. Apply: `alembic upgrade head`

---

## Environment Variables

Copy `.env.example` to `backend/.env`:

| Variable          | Default                       | Description                                                                                                                                           |
| ----------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`    | `sqlite:///./ethara_seats.db` | Database connection string                                                                                                                            |
| `JWT_SECRET_KEY`  | _(auto-generated)_            | JWT signing key — set explicitly in production so tokens survive restarts. Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `DEBUG`           | `true`                        | Enable debug mode                                                                                                                                     |
| `OPENAI_API_KEY`  | _(empty)_                     | Optional — enables GPT-4o fallback in AI assistant                                                                                                    |
| `GEMINI_API_KEY`  | _(empty)_                     | Optional — enables Gemini fallback                                                                                                                    |
| `GROK_API_KEY`    | _(empty)_                     | Optional — enables xAI Grok fallback                                                                                                                  |
| `OPENAI_MODEL`    | `gpt-4o`                      | OpenAI model to use                                                                                                                                   |
| `ALLOWED_ORIGINS` | `["http://localhost:5173"]`   | CORS allowed origins                                                                                                                                  |

For PostgreSQL:

```
DATABASE_URL=postgresql://user:password@localhost:5432/ethara_seats
```

For PostgreSQL:

```
DATABASE_URL=postgresql://user:password@localhost:5432/ethara_seats
```

---

## Design System

Matching the Ethara website (dark navy + magenta):

| Token              | Value     | Usage                         |
| ------------------ | --------- | ----------------------------- |
| `ethara-bg`        | `#0a0a14` | Page background               |
| `ethara-card`      | `#12121f` | Card backgrounds              |
| `ethara-border`    | `#1e1e3a` | Borders                       |
| `ethara-primary`   | `#c026d3` | Magenta — CTAs, active states |
| `ethara-secondary` | `#7c3aed` | Violet — gradients, secondary |
| `ethara-success`   | `#10b981` | Available status              |
| `ethara-warning`   | `#f59e0b` | Reserved status               |
| `ethara-error`     | `#ef4444` | Occupied status               |

---

## Business Rules Enforced

| #   | Rule                                      | Enforcement                                           |
| --- | ----------------------------------------- | ----------------------------------------------------- |
| 1   | One employee → one active seat            | Service layer + 409 error                             |
| 2   | One seat → one active employee            | DB query check + 409 error                            |
| 3   | Released seats become available           | `release_allocation()` sets `seat.status = available` |
| 4   | Reserved seats cannot be allocated        | Service check + 403 error                             |
| 5   | New joiners prioritized near project team | Proximity greedy algorithm                            |
| 6   | Duplicate email not allowed               | DB unique constraint + 422 error                      |
| 7   | Duplicate seat location not allowed       | DB unique constraint + 422 error                      |
| 8   | Dashboard updates after every change      | TanStack Query cache invalidation                     |

---

## Deployment Platforms

The project is ready to deploy on:

- **Railway** — push backend folder, set `DATABASE_URL` env var
- **Render** — web service + PostgreSQL add-on
- **Vercel** — frontend static build (`npm run build` → `dist/`)
- **Fly.io** — Docker-based, use `fly launch`
- **Docker anywhere** — `docker compose up --build`
