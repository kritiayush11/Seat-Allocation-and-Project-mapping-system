# Ethara Seat Allocation & Project Mapping System — PLAN

## Overview
A full-stack application to manage seat allocation for ~5,000 employees at Ethara across multiple floors, zones, and projects. Includes an AI assistant for natural language queries.

---

## Recommended Technology Stack & Rationale

### Frontend: React.js + TypeScript + Vite + Tailwind CSS
**Why:**
- React with TypeScript gives type safety across the entire component tree, catching seat/employee data-shape bugs at compile time.
- Vite gives near-instant HMR and a lean build pipeline — far faster than CRA for a 5,000-record data-heavy app.
- Tailwind CSS enables rapid dark-theme implementation that matches Ethara's brand (deep navy + magenta accent) without custom CSS overload.
- React Query (TanStack Query) for server-state caching — critical when rendering dashboards with large datasets.

### Backend: Python FastAPI
**Why:**
- FastAPI gives automatic OpenAPI/Swagger docs at `/docs` — fulfills the documentation requirement with zero extra effort.
- Async-first architecture handles concurrent seat allocation requests without race conditions (important for 5,000 employees).
- Pydantic models enforce the schema at every API boundary — aligns with SOLID's Open/Closed Principle (extend models, don't modify).
- SQLAlchemy ORM provides a clean abstraction over the database, supporting future DB migrations.

### Database: PostgreSQL (SQLite for local dev)
**Why:**
- PostgreSQL's row-level locking prevents duplicate seat allocation under concurrent requests — a hard business requirement.
- Unique constraints at the DB level as the final guard against business rule violations.
- Alembic for migrations — keeps schema versioned alongside code.

### AI Assistant: Rule-based intent parser with OpenAI fallback
**Why:**
- A deterministic keyword/regex intent parser covers 95% of queries reliably without API cost or latency.
- OpenAI GPT-4o as optional fallback for complex queries when OPENAI_API_KEY is set.
- This approach works in all environments (demo, offline, production) — no hard dependency on external APIs.

---

## Architecture: SOLID Principles Applied

### Single Responsibility Principle (SRP)
- `EmployeeRepository` only handles employee DB operations.
- `SeatAllocationService` only handles allocation business logic.
- `AIAssistantService` only handles query parsing and response generation.
- Each React component has one job (e.g., `SeatCard`, `EmployeeTable`, `FloorMap`).

### Open/Closed Principle (OCP)
- `IntentParser` uses a strategy pattern — new intent handlers can be added without modifying the core parser.
- Seat allocation strategies (proximity-first, zone-first) are plug-in strategies.

### Liskov Substitution Principle (LSP)
- All repository classes implement a base `BaseRepository[T]` generic — any repo can be swapped without breaking service layer.

### Interface Segregation Principle (ISP)
- `IEmployeeReader` and `IEmployeeWriter` are separate interfaces — read-only roles only get `IEmployeeReader`.
- `ISeatAllocator` is separate from `ISeatQuery`.

### Dependency Inversion Principle (DIP)
- Services depend on abstract repository interfaces, not concrete SQLAlchemy classes.
- FastAPI dependency injection (`Depends()`) wires implementations at runtime.

---

## Seat Allocation Algorithm

### Primary Algorithm: Proximity-Based Greedy with Zone Fallback

```
1. INPUT: new employee with project_id
2. FIND all teammates (employees on same project) → get their seat zones
3. SCORE available seats:
   - +3 if seat zone matches majority teammate zone
   - +2 if seat floor matches majority teammate floor
   - +1 for seats with lower seat numbers (prefer organized allocation)
4. SELECT highest-scored available seat
5. FALLBACK: if no seats in preferred zone → find nearest zone with availability
6. FALLBACK 2: if entire floor is full → suggest next floor
7. CONSTRAINT CHECK: one active allocation per employee, one employee per seat
8. ALLOCATE with transaction + row lock to prevent concurrent double-booking
```

**Why Greedy + Proximity:**
- O(n) scoring over available seats is fast enough for 5,500 seats.
- Proximity keeps project teams physically co-located, improving collaboration.
- Zone fallback ensures new joiners are never left unallocated.

### Duplicate Prevention
- PostgreSQL unique constraint on `(seat_id)` where `allocation_status = 'active'` (partial unique index).
- Application-level check before insert.
- DB-level `SELECT FOR UPDATE` lock on seat row during allocation transaction.

---

## TDD Approach

### Test-First Order:
1. **Failing tests written first** for all business rules (see `tests/` directory).
2. **False/edge case tests first:**
   - Allocate to already-occupied seat → expect 409
   - Duplicate employee email → expect 422
   - Release a seat that's already available → expect 400
   - Allocate a reserved seat → expect 403
   - New joiner with no available seats anywhere → expect 200 with `no_seats_available` flag
3. Implementation written to make tests pass (Red → Green → Refactor).

---

## Project Directory Structure

```
Seat-Allocation-and-Project-mapping-system/
├── PLAN.md                          # This file
├── README.md                        # Full documentation
├── AI_PROMPTS.md                    # AI usage documentation
├── docker-compose.yml               # Full stack Docker setup
├── .env.example                     # Environment variable template
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings (Pydantic BaseSettings)
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── employee.py
│   │   │   ├── project.py
│   │   │   ├── seat.py
│   │   │   └── seat_allocation.py
│   │   │
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── employee.py
│   │   │   ├── project.py
│   │   │   ├── seat.py
│   │   │   └── ai_assistant.py
│   │   │
│   │   ├── repositories/            # DB access layer (SRP, DIP)
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Generic BaseRepository[T]
│   │   │   ├── employee_repository.py
│   │   │   ├── project_repository.py
│   │   │   └── seat_repository.py
│   │   │
│   │   ├── services/                # Business logic (SRP, OCP)
│   │   │   ├── __init__.py
│   │   │   ├── employee_service.py
│   │   │   ├── seat_allocation_service.py
│   │   │   ├── dashboard_service.py
│   │   │   └── ai_assistant_service.py
│   │   │
│   │   ├── routers/                 # FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── employees.py
│   │   │   ├── projects.py
│   │   │   ├── seats.py
│   │   │   ├── dashboard.py
│   │   │   └── ai_assistant.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── intent_parser.py     # Rule-based NLP (OCP strategy)
│   │       └── seed_data.py         # 5000 employee seed generator
│   │
│   ├── migrations/                  # Alembic migration files
│   │   └── versions/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # Pytest fixtures
│   │   ├── test_employees.py        # TDD: employee CRUD + edge cases
│   │   ├── test_seats.py            # TDD: seat allocation logic
│   │   ├── test_projects.py         # TDD: project mapping
│   │   ├── test_dashboard.py        # TDD: dashboard aggregations
│   │   └── test_ai_assistant.py     # TDD: intent parsing
│   │
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css               # Tailwind + custom Ethara theme vars
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Table.tsx
│   │   │   │   └── SearchBar.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── StatsCard.tsx
│   │   │   │   ├── ProjectChart.tsx
│   │   │   │   └── FloorOccupancy.tsx
│   │   │   ├── employees/
│   │   │   │   ├── EmployeeTable.tsx
│   │   │   │   ├── EmployeeForm.tsx
│   │   │   │   └── EmployeeCard.tsx
│   │   │   ├── seats/
│   │   │   │   ├── SeatGrid.tsx
│   │   │   │   ├── SeatCard.tsx
│   │   │   │   ├── AllocateModal.tsx
│   │   │   │   └── FloorMap.tsx
│   │   │   └── ai/
│   │   │       └── AIAssistant.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Employees.tsx
│   │   │   ├── Projects.tsx
│   │   │   ├── Seats.tsx
│   │   │   └── NotFound.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useEmployees.ts
│   │   │   ├── useSeats.ts
│   │   │   ├── useProjects.ts
│   │   │   └── useDashboard.ts
│   │   │
│   │   ├── services/
│   │   │   └── api.ts              # Axios API client
│   │   │
│   │   └── types/
│   │       └── index.ts            # Shared TypeScript interfaces
│   │
│   ├── public/
│   │   └── ethara-logo.png
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
│
└── nginx/
    └── nginx.conf                   # Reverse proxy config
```

---

## API Endpoints (Complete List)

### Employees
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/employees` | Create employee |
| GET | `/employees` | List with filters (name, email, project, status) |
| GET | `/employees/{id}` | Get employee details + seat |
| PUT | `/employees/{id}` | Update employee |
| DELETE | `/employees/{id}` | Deactivate employee |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects` | Create project |
| GET | `/projects` | List projects |
| GET | `/projects/{id}` | Get project details |
| GET | `/projects/{id}/employees` | List employees in project |

### Seats
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/seats` | Create seat |
| GET | `/seats` | List with filters (floor, zone, status) |
| GET | `/seats/available` | List available seats |
| GET | `/seats/{id}` | Get seat details |
| POST | `/seats/allocate` | Allocate seat to employee |
| POST | `/seats/release` | Release seat |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/summary` | Total counts (seats, employees, etc.) |
| GET | `/dashboard/project-utilization` | Project-wise allocation breakdown |
| GET | `/dashboard/floor-utilization` | Floor-wise occupancy |

### AI Assistant
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/query` | Natural language query handler |

---

## Design Theme (Matching Ethara Website)
- Background: `#0a0a14` (near-black navy)
- Card background: `#12121f`
- Primary accent: `#c026d3` (magenta/fuchsia)
- Secondary accent: `#7c3aed` (violet)
- Text primary: `#ffffff`
- Text secondary: `#94a3b8`
- Border: `#1e1e3a`
- Success: `#10b981`
- Warning: `#f59e0b`
- Error: `#ef4444`
- Font: Inter (Google Fonts)
- Hexagonal background pattern (SVG, subtle opacity)

---

## Seed Data Plan
- 5,000 employees across 11 projects
- 5 floors (Floor 1–5)
- 10+ zones per floor (Zone A–J)
- 5,500 seats total
  - ~4,400 occupied
  - ~500 available  
  - ~100 reserved
  - ~50 maintenance
- 50 employees with no seat (pending allocation)

---

## Phase-wise Implementation

| Phase | Task | Est. Complexity |
|-------|------|----------------|
| 1 | Database models + migrations | Low |
| 2 | TDD — write failing tests | Medium |
| 3 | Repository layer | Low |
| 4 | Service layer + allocation algorithm | High |
| 5 | FastAPI routers + Pydantic schemas | Medium |
| 6 | Seed data generator | Medium |
| 7 | Frontend scaffold + theme | Medium |
| 8 | Dashboard + charts | High |
| 9 | Employee/Seat/Project CRUD UI | High |
| 10 | AI Assistant UI + backend | Medium |
| 11 | Integration testing | Medium |
| 12 | Docker + deployment config | Low |

---

## Checklist Against Assessment Requirements

- [x] Employee Management (ID, name, email, dept, role, joining date, status, project, seat)
- [x] Project Mapping (11 projects: Indigo, Indreed, Mydreed, Preed, Serfy, Oreed, Bedegreed, Opreed, Serry, Kaary, Mered)
- [x] Seat Allocation (floor, zone, bay, seat#, status, employee, project, date)
- [x] Duplicate prevention (DB constraints + app-level)
- [x] New Joiner Allocation with proximity suggestions
- [x] Alternate zone fallback
- [x] Search & Filter (name, ID, email, project, floor, zone, status)
- [x] Dashboard (all required metrics)
- [x] AI Assistant (rule-based + OpenAI fallback)
- [x] All 5 required API groups
- [x] 5,000 employees seed data
- [x] 5+ floors, 10+ zones, 5,500+ seats
- [x] 500+ available, 100+ reserved, 50 pending
- [x] Swagger/OpenAPI docs at `/docs`
- [x] Docker deployment
- [x] README.md with commands, endpoints, directory structure
- [x] AI_PROMPTS.md
- [x] SOLID principles documented
- [x] TDD with false/edge case tests
- [x] Ethara brand design (dark + magenta)
- [x] Ethara logo
