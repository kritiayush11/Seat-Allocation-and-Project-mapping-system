# GitHub Push Plan — Ethara Seat Allocation & Project Mapping System

**Approach: TDD — Red (false/edge cases first) → Green → Refactor → Push**

---

## Current Status (July 2026)

| Item                | Status                                                                          |
| ------------------- | ------------------------------------------------------------------------------- |
| GitHub repository   | ✅ `https://github.com/kritiayush11/Seat-Allocation-and-Project-mapping-system` |
| Git branch          | ✅ `main` — all changes pushed                                                  |
| `.gitignore`        | ✅ Blocks `.env`, `*.db`, `.venv`, `node_modules`, `.DS_Store`, `build/`        |
| `.env.example`      | ✅ Present — safe to commit                                                     |
| `backend/.env`      | ✅ Gitignored — credentials managed via Render dashboard                        |
| Backend tests       | ✅ 137 pytest tests passing, 2 skipped (live Grok — require `XAI_API_KEY`)      |
| Frontend build      | ✅ `npm run build` succeeds, deployed on Netlify                                |
| Database            | ✅ Neon PostgreSQL — 5,001 employees, 5,500 seats migrated                      |
| Backend deployment  | ✅ Render — `https://ethara-backend-xnma.onrender.com`                          |
| Frontend deployment | ✅ Netlify — `https://ethara-frontend12.netlify.app`                            |

---

## Repository Safety Rules

### Files That MUST NOT Be Committed

| File/Pattern                              | Reason                                        |
| ----------------------------------------- | --------------------------------------------- |
| `backend/.env`                            | Neon DB URL, JWT secret, xAI API key          |
| `ethara_seats.db`, `*.db-shm`, `*.db-wal` | SQLite DB with local data                     |
| `.venv/`, `venv/`                         | Python virtualenv                             |
| `frontend/node_modules/`                  | npm packages                                  |
| `frontend/build/`, `frontend/dist/`       | Build artifacts                               |
| `.DS_Store`                               | macOS metadata                                |
| `__pycache__/`, `*.pyc`                   | Python bytecode                               |
| `backend/migrate_to_neon.py`              | One-off migration script (not needed in repo) |

### Safe to Commit

| File                       | Contents                                    |
| -------------------------- | ------------------------------------------- |
| `frontend/.env.production` | Only `REACT_APP_API_URL` — no secrets       |
| `.env.example`             | Template with empty values, no real secrets |
| `backend/app/config.py`    | Default placeholder values only             |

---

## Environment Variables (Render Dashboard)

Set these in the Render service environment — never hardcode in source:

```
DATABASE_URL=postgresql://neondb_owner:<password>@<host>/neondb?sslmode=require
JWT_SECRET_KEY=<64-char hex — generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
XAI_API_KEY=xai-<your-key>         # Free at console.x.ai
ALLOWED_ORIGINS_RAW=https://ethara-frontend12.netlify.app
```

Render start command:

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "*"
```

---

## TDD Verification

Before every push:

```bash
cd backend
python -m pytest tests/ -v
# Expected: 137 passed, 2 skipped
```

The 2 skipped tests (`TestLiveGrokAPI`) require `XAI_API_KEY` to be set. Run them manually:

```bash
XAI_API_KEY=xai-... python -m pytest tests/test_ai_agent_grok.py -k "Live" -v
```

### Key Edge Cases Verified

| Edge Case                                  | Test                                                        |
| ------------------------------------------ | ----------------------------------------------------------- |
| JWT_SECRET_KEY not hardcoded               | `test_security_tdd.py::test_jwt_secret_key_security`        |
| Concurrent seat double-booking blocked     | `test_seats.py::test_employee_cannot_have_two_active_seats` |
| Neon connection alive                      | `test_health.py::TestNeonDatabaseConnection`                |
| All 6 tables present on Neon               | `test_health.py::TestNeonSchemaIntegrity`                   |
| Rate limits fire at correct thresholds     | `test_rate_limiting.py` (13 tests)                          |
| AI returns rule-based fallback with no key | `test_ai_agent_grok.py::TestAIAgentLLMSelection`            |

---

## Standard Push Workflow

```bash
# 1. Run tests
cd backend && python -m pytest tests/ -q

# 2. Stage only the files you changed
git add path/to/changed/file.py

# 3. Verify nothing sensitive is staged
git diff --cached --name-only

# 4. Commit
git commit -m "fix|feat|docs: short description"

# 5. Push to main
git push
```

Render and Netlify automatically redeploy on push to `main`.

---

## Checklist for New Features

```
[ ] Write failing tests first (TDD Red phase)
[ ] Implement to make tests pass (Green phase)
[ ] Refactor (Refactor phase)
[ ] python -m pytest tests/ -q  →  all green
[ ] No sensitive files staged (git diff --cached --name-only)
[ ] git commit -m "..."
[ ] git push
[ ] Verify Render redeploys successfully
[ ] Verify Netlify redeploys successfully (if frontend changed)
```
