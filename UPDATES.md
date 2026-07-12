# Project Upgrades & Technical Changelog

All upgrades, migrations, bug fixes, and architecture decisions for the **Ethara Seat Allocation & Project Mapping System**.

---

## Release: July 2026 — Production Deployment on Render + Netlify

### Database: SQLite → Neon PostgreSQL

- Migrated all data from `ethara_seats.db` (SQLite) to **Neon PostgreSQL 16** hosted in `ap-southeast-1`
- Migrated 5,001 employees, 5,500 seats, 4,951 seat allocations, 11 projects
- Custom Python migration script using SQLAlchemy Core with FK-safe insertion order and `TRUNCATE ... CASCADE`
- Backend `.env` updated with Neon pooled connection string (`sslmode=require`)

### Critical Bug Fix: UPPERCASE Enum Mismatch

- **Root cause:** Neon PostgreSQL stores enums as UPPERCASE (`AVAILABLE`, `OCCUPIED`, `ACTIVE`) but all Python models defined them as lowercase. Every INSERT and UPDATE was rejected by Postgres with `invalid input value for enum`.
- **Fix:** Updated all four models (`seat.py`, `employee.py`, `project.py`, `seat_allocation.py`) to use UPPERCASE enum values matching Neon. Used `create_type=False` on `SAEnum` so SQLAlchemy never tries to recreate the existing Neon enum types.
- **API compatibility preserved:** Added `field_serializer` to all response schemas so JSON output still returns lowercase strings (`"active"`, `"occupied"`) — no frontend or test changes needed.
- **Input flexibility:** Added `field_validator` with `.upper()` normalisation to all `*Update` schemas so both `"archived"` and `"ARCHIVED"` are accepted as input.
- Also fixed `seat_repository.count_by_status()` and `floor_utilization()` to use UPPERCASE dict keys, and `dashboard_service.py` to look up UPPERCASE keys from the seat counts map.

### AI Agent: LangChain Removed → Direct OpenAI SDK

- **Replaced** the entire LangChain-based `AIAgent` with a direct **OpenAI SDK tool-calling loop**
- Works with **xAI Grok**, OpenAI, or Gemini (all via the same OpenAI-compatible API interface)
- Provider priority: **Grok (xAI free tier) → OpenAI → Gemini**
- Model: `grok-3-mini` (free, set via `GROK_MODEL` env var)
- Tool-calling loop: up to 5 rounds, each round dispatches DB tools and feeds results back to the model
- DB tools: `get_employee_seat`, `search_seats`, `get_seat_utilization`, `search_projects`, `find_neighbors`
- Chat history persisted in `chat_messages` table (Neon) per `session_id`
- **Why removed LangChain:** Version conflicts, 5+ abstraction layers over a simple API call, harder to debug, slower startup
- `ai_assistant_service.py` updated: agent is invoked when any API key is present (previously gated on `session_id` being set)
- `AIAssistant.tsx` subtitle updated to reflect Grok/Neon integration

### Deployment

- **Backend** deployed on **Render** (free web service, Python runtime)
  - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "*"`
  - `--proxy-headers` is required — without it Render's reverse proxy strips POST request bodies, causing `input: null` 422 errors
- **Frontend** deployed on **Netlify** — `https://ethara-frontend12.netlify.app`
  - `frontend/.env.production` sets `REACT_APP_API_URL=https://ethara-backend-xnma.onrender.com`
  - CORS: `ALLOWED_ORIGINS_RAW` in Render env vars includes the Netlify domain
- **Database** on **Neon** — `https://console.neon.tech` (PostgreSQL 16)

### Auth Fix: Empty JWT Secret

- `JWT_SECRET_KEY` was left empty in `.env`, breaking the security rotation guard in `config.py`
- Fixed: set a fixed 64-char hex secret in `backend/.env` so tokens survive restarts
- `get_settings()` rotation guard now only replaces the hardcoded placeholder string, not an empty string

### CORS Fix: `pydantic-settings` SettingsError

- `ALLOWED_ORIGINS` as a `List[str]` field caused `SettingsError: error parsing value for field` on Render because pydantic-settings tries to JSON-decode any list field from env vars
- **Fix:** Renamed to `ALLOWED_ORIGINS_RAW: str` with a `@property` that splits on commas or parses JSON — fully Render-compatible

### Login Page

- Removed demo credentials helper box from the login page
- Users create their own admin accounts via `/auth/signup`
- Admin accounts on Neon: `admin` (password: `admin123`), `hr` (password: `hrpassword`)

---

## Release: July 11, 2026 — Security & Rate Limiting

### JWT Security (TDD)

- `JWT_SECRET_KEY` defaulted to a static hardcoded string. Added a failing security test, then patched `get_settings()` to auto-rotate with `secrets.token_hex(32)` if the placeholder is detected at startup.
- `test_security_tdd.py::test_jwt_secret_key_security` — passes.

### Rate Limiting via slowapi

- `POST /auth/login` and `POST /auth/signup` → 5/minute (brute-force protection)
- `GET /seats` → 60/minute (DB scraping protection)
- `POST /seats/allocate` → 20/minute (seat-hoarding prevention)
- `POST /ai/query` → 10/minute (LLM cost protection)
- Custom `_get_client_ip()` reads `X-Forwarded-For` header — works correctly behind Render's proxy
- 13 rate-limit TDD tests across all 5 rate-limited endpoints + per-IP isolation test

---

## Release: Initial — Full-Stack Scaffold

### Frontend Build System

- Migrated from Vite to **Craco (Webpack)** to align with `react-scripts` conventions
- React 19 + TypeScript, react-router-dom v7, TanStack React Query, Radix UI, Framer Motion
- Tailwind CSS dark theme with Ethara brand tokens (navy + magenta)

### Conversational AI Agent (original LangChain version)

- LangChain agent with Gemini / Grok / OpenAI key detection and DB-bound tools
- In-database memory via `chat_messages` table (later preserved in the SDK rewrite)
- Voice dictation via Web Speech API in `AIAssistant.tsx`

### Version Control

- Comprehensive `.gitignore` blocks `.env`, `*.db`, `.venv`, `node_modules`, `build/`, `.DS_Store`
- `backend/.env` is never committed — credentials managed via Render dashboard env vars
