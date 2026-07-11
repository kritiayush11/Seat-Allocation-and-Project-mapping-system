# GitHub Push Plan — Ethara Seat Allocation & Project Mapping System

**Approach: TDD — Red (false/edge cases first) → Green → Refactor → Push**

---

## Status Snapshot (as of July 11, 2026)

| Item                             | Status                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------ |
| Git initialized at project level | ❌ Not yet (git is at `~/`, not at project root)                               |
| `.gitignore`                     | ✅ Comprehensive — blocks `.env`, `*.db`, `.venv`, `node_modules`, `.DS_Store` |
| `.env.example`                   | ✅ Present — safe to commit                                                    |
| Sensitive `.env` file            | ❌ Not present (safe)                                                          |
| SQLite DB files in root          | ⚠️ `ethara_seats.db`, `.db-shm`, `.db-wal` — blocked by `.gitignore`           |
| Backend tests                    | ✅ 82 pytest tests across 9 test files                                         |
| Frontend tests                   | ❌ None — no Jest/Vitest setup                                                 |
| GitHub Actions / CI              | ❌ Not configured                                                              |
| Remote GitHub repo               | ❌ Not created yet                                                             |

---

## Phase 0 — Pre-Flight Safety Checks ✅ COMPLETE

### 0.1 Verify `.gitignore` covers all sensitive paths ✅

- [x] Root `.gitignore` blocks `*.db`, `.env`, `.venv`, `node_modules`, `.DS_Store`
- [x] No `.env` files exist anywhere in the tree (scan confirmed clean)

### 0.2 Confirm no secrets are hardcoded in source ✅

- [x] `backend/app/config.py` — `JWT_SECRET_KEY` has a static default BUT `get_settings()` detects it at runtime and replaces it with `secrets.token_hex(32)` — covered by `test_security_tdd.py`
- [x] No hardcoded API keys found anywhere (`sk-*`, `AIza*`, `xai-*` scan came back clean)
- [x] `seed_data.py` — test credentials (`admin/adminpassword`, `hr/hrpassword`) are intentional, clearly marked, and documented in UPDATES.md

### 0.3 Run the full backend test suite ✅ 82/82 PASSED

```
82 passed, 7 warnings in 4.01s
```

> Note: use `../.venv/bin/python3 -m pytest tests/ -v` from `backend/` (venv uses `python3`, not `python`)

---

## Phase 1 — TDD: False/Edge Case Verification ✅ COMPLETE

Before pushing, we verify the test suite actually catches the edge cases it claims to.  
Strategy: **temporarily break the code, confirm the test goes RED, then revert.**

### 1.1 Security Tests (test_security_tdd.py) ✅

| Edge Case                                  | Result                                |
| ------------------------------------------ | ------------------------------------- |
| `JWT_SECRET_KEY` defaults to static string | 🔴 RED confirmed → 🟢 GREEN on revert |

**Verified:** Removed `get_settings()` guard in `config.py` → `test_jwt_secret_key_security` FAILED (`AssertionError: 'ethara_super_secret_signing_key_2026_prod' != ...`). Reverted → PASSED.

### 1.2 Seat Allocation Edge Cases (test_seats.py) ✅

| Edge Case                                              | Result                                |
| ------------------------------------------------------ | ------------------------------------- |
| Employee cannot have two active seats (double-booking) | 🔴 RED confirmed → 🟢 GREEN on revert |

**Verified:** Removed Business Rule 1 guard in `allocate_seat()` → `test_employee_cannot_have_two_active_seats` FAILED (`assert 201 == 409` — second allocation went through). Reverted → PASSED.

### 1.3 Final Full Suite ✅

```
82 passed, 7 warnings in 4.32s
```

All source files confirmed back to original state.

---

## Phase 2 — Git Initialization at Project Level ✅ COMPLETE

> ⚠️ **Problem:** `git status` shows git is initialized at `~/` (home directory), not at the project. This must be fixed.

### Steps

```bash
# Step 1: Initialize git at the project root (NOT home dir)
cd /Users/kritiayush/code/Seat-Allocation-and-Project-mapping-system
git init

# Step 2: Set the default branch name
git branch -M main

# Step 3: Verify .gitignore is working — these should NOT appear:
git status  # should NOT show: .env, *.db, .venv/, node_modules/
```

---

## Phase 3 — GitHub Repository Setup

### 3.1 Create Remote Repo

Using GitHub CLI (`gh`):

```bash
gh repo create Seat-Allocation-and-Project-mapping-system \
  --public \
  --description "Full-stack seat allocation & project mapping system — FastAPI + React 19 + AI Assistant" \
  --source=. \
  --remote=origin
```

Or manually:

1. Go to https://github.com/new
2. Name: `Seat-Allocation-and-Project-mapping-system`
3. Set to Public or Private (your choice)
4. Do NOT initialize with README, .gitignore, or license (we have them)

### 3.2 Link Remote

```bash
git remote add origin https://github.com/<your-username>/Seat-Allocation-and-Project-mapping-system.git
git remote -v  # verify
```

---

## Phase 4 — Staging & First Commit

### 4.1 Stage Files Explicitly (never `git add -A` blindly)

```bash
# Backend
git add backend/app/
git add backend/tests/
git add backend/migrations/
git add backend/requirements.txt
git add backend/requirements-dev.txt
git add backend/alembic.ini
git add backend/Dockerfile

# Frontend
git add frontend/src/
git add frontend/public/
git add frontend/package.json
git add frontend/tsconfig.json
git add frontend/tailwind.config.ts
git add frontend/craco.config.js  # if exists
git add frontend/Dockerfile

# Nginx
git add nginx/

# Root config
git add docker-compose.yml
git add .gitignore
git add .env.example
git add README.md
git add PLAN.md
git add UPDATES.md
git add AI_PROMPTS.md
```

### 4.2 Verify Nothing Sensitive Is Staged

```bash
git diff --cached --name-only  # review every file listed
# Must NOT include: .env, *.db, .venv, node_modules, .DS_Store
```

### 4.3 Create Initial Commit

```bash
git commit -m "feat: initial commit — Ethara Seat Allocation & Project Mapping System

- FastAPI backend with SQLAlchemy 2.0, Alembic migrations
- React 19 + TypeScript frontend (Craco/Webpack, TanStack Query, Radix UI)
- Proximity-based greedy seat allocation algorithm
- LangChain AI assistant with Gemini/Grok/OpenAI fallback chain
- 82 backend tests passing (TDD — edge cases first)
- Docker Compose deployment (PostgreSQL + FastAPI + React + Nginx)
- Security hardened: dynamic JWT secret, read-only AI tool scope"
```

---

## Phase 5 — Push & CI Setup

### 5.1 Push to GitHub

```bash
git push -u origin main
```

### 5.2 GitHub Actions CI (optional but recommended)

Create `.github/workflows/backend-ci.yml`:

```yaml
name: Backend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - name: Run tests
        run: cd backend && python -m pytest tests/ -v
```

---

## Phase 6 — Post-Push Verification

- [ ] Visit GitHub repo URL — README renders correctly
- [ ] Confirm no sensitive files appear in the repo (no `.env`, no `*.db`)
- [ ] All 82 backend tests still pass locally after the push
- [ ] GitHub Actions CI (if configured) shows green checkmark

---

## Files That MUST NOT be Committed

| File/Pattern                              | Reason                                              |
| ----------------------------------------- | --------------------------------------------------- |
| `.env`                                    | Contains secrets (JWT key, API keys, DB password)   |
| `ethara_seats.db`, `*.db-shm`, `*.db-wal` | SQLite DB with live data                            |
| `.venv/`, `venv/`                         | Python virtualenv — install from `requirements.txt` |
| `frontend/node_modules/`                  | npm/yarn packages — install from `package.json`     |
| `frontend/build/`, `frontend/dist/`       | Build artifacts                                     |
| `.DS_Store`                               | macOS metadata                                      |
| `__pycache__/`, `*.pyc`                   | Python bytecode                                     |
| `.pytest_cache/`                          | Test cache                                          |

---

## Checklist Summary

```
Phase 0 — Pre-Flight
  [ ] .gitignore verified
  [ ] No hardcoded secrets in source
  [ ] 82 backend tests passing

Phase 1 — TDD False Case Verification
  [ ] Security test goes RED on hardcoded JWT key → reverted → GREEN
  [ ] Seat conflict test goes RED when guard removed → reverted → GREEN
  [ ] All 82 tests GREEN after revert

Phase 2 — Git Init
  [ ] `git init` at project root
  [ ] `git branch -M main`

Phase 3 — Remote Setup
  [ ] GitHub repo created
  [ ] `git remote add origin <url>`

Phase 4 — Staging & Commit
  [ ] Files staged explicitly (not `git add -A`)
  [ ] `git diff --cached --name-only` reviewed
  [ ] No sensitive files staged
  [ ] Initial commit created

Phase 5 — Push
  [ ] `git push -u origin main`
  [ ] (Optional) GitHub Actions CI added

Phase 6 — Post-Push
  [ ] Repo visible on GitHub
  [ ] README renders correctly
  [ ] No secrets visible
  [ ] CI green (if configured)
```

---

> **Waiting for user approval before executing any phase.**
