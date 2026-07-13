# Debugging Notes — Ethara Seat Allocation System

All bugs found during development, their root causes, fixes, and lessons learned.

---

## Bug 1: Login returns 422 `input: null` on Render

**Symptom:** `POST /auth/login` works locally but returns 422 in production with `"input": null`.  
**Root cause:** Render runs behind a reverse proxy. Without `--proxy-headers`, uvicorn strips the request body on every POST.  
**Fix:** Add `--proxy-headers --forwarded-allow-ips "*"` to the uvicorn start command.  
**Lesson:** Always use `--proxy-headers` when deploying uvicorn behind any reverse proxy (Render, nginx, AWS ALB).

---

## Bug 2: Frontend shows "Page not found" after logout / page refresh

**Symptom:** Navigating to `/login`, `/ai`, `/employees` directly (or after logout redirect) shows Netlify's 404 page.  
**Root cause:** React Router handles routing client-side. Netlify serves static files — it looks for a file at `/login` and finds nothing.  
**Fix:** Add `frontend/public/_redirects` with `/*    /index.html   200`. CRA copies it to `build/` automatically.  
**Lesson:** Every React SPA deployed on Netlify needs `_redirects`. On Vercel it's `vercel.json`, on Apache it's `.htaccess`.

---

## Bug 3: All seat/employee/project writes fail with `invalid input value for enum`

**Symptom:** `POST /employees`, `POST /seats` etc return 500 on Render. Works locally.  
**Root cause:** Neon PostgreSQL stores enum types as UPPERCASE (`AVAILABLE`, `ACTIVE`). Python models defined them as lowercase (`"available"`, `"active"`). Every INSERT was rejected.  
**Fix:**  
- Updated all 4 enum classes (`SeatStatus`, `EmployeeStatus`, `ProjectStatus`, `AllocationStatus`) to use UPPERCASE values  
- Added `create_type=False` to `SAEnum()` so SQLAlchemy doesn't try to recreate Neon's existing enum types  
- Added `field_serializer` to response schemas to lowercase enums in JSON output (so frontend/tests don't break)  
- Added `field_validator` with `.upper()` to all input schemas to accept both cases  
**Lesson:** Always inspect the actual DB enum type values with `SELECT * FROM pg_enum` before defining Python enums. Never assume case.

---

## Bug 4: `?status=reserved` query param returns 422

**Symptom:** `GET /seats?status=reserved` returns `Input should be 'AVAILABLE', 'OCCUPIED'...`  
**Root cause:** FastAPI `Query()` params bypass Pydantic `field_validator` — the enum is parsed directly by FastAPI's type coercion, which is case-sensitive.  
**Fix:** Added `_missing_()` classmethod to all enum classes. Python calls `_missing_` when enum lookup fails — we return the UPPERCASE member on case-insensitive match.  
```python
@classmethod
def _missing_(cls, value):
    if isinstance(value, str):
        for member in cls:
            if member.value == value.upper():
                return member
    return None
```
**Lesson:** `field_validator` only runs for Pydantic model fields (request body). Query params need `_missing_` on the enum itself.

---

## Bug 5: `POST /employees` returns 422 `Input should be 'ACTIVE'...` for `status: "active"`

**Symptom:** Creating an employee with `"status": "inactive"` (lowercase) returns 422.  
**Root cause:** `EmployeeBase` (parent of `EmployeeCreate`) had no `field_validator`. Only `EmployeeUpdate` had one.  
**Fix:** Added `field_validator("status", mode="before")` with `.upper()` to `EmployeeBase`.  
**Lesson:** When adding a validator to an Update schema, also check the Base/Create schema — they share the same field.

---

## Bug 6: `dashboard/summary` shows `occupied_seats: 0` despite seats being occupied

**Symptom:** Dashboard shows 0 occupied seats even though `seat_allocations` has ~4,951 ACTIVE records.  
**Root cause:** `count_by_status()` returned a dict with UPPERCASE keys (`"OCCUPIED"`) but `dashboard_service.py` looked up `seat_counts.get("occupied", 0)` (lowercase).  
**Fix:** Updated `count_by_status()` and `floor_utilization()` to use UPPERCASE keys, and updated `dashboard_service.py` lookups to match.  
**Lesson:** After changing enum case, grep for every hardcoded string that reads from enum values — dict keys, comparisons, lookups.

---

## Bug 7: `pydantic_settings.sources.SettingsError` on Render for `ALLOWED_ORIGINS`

**Symptom:** Backend crashes on startup: `error parsing value for field "ALLOWED_ORIGINS"`.  
**Root cause:** `ALLOWED_ORIGINS: list[str]` field — pydantic-settings tries to JSON-decode any list-typed field from env vars. Render sets env vars as plain strings, not JSON arrays.  
**Fix:** Renamed field to `ALLOWED_ORIGINS_RAW: str` with a `@property` that splits on commas or parses JSON. Since it's a `str` field, pydantic-settings never tries to JSON-decode it.  
**Lesson:** Never use `list[str]` for env var fields in pydantic-settings when deploying to Render. Always use `str` + manual parse.

---

## Bug 8: `UniqueViolation: duplicate key value violates unique constraint "employees_pkey"`

**Symptom:** First `POST /employees` after deployment fails with `Key (id)=(13) already exists`.  
**Root cause:** During migration, rows were inserted with explicit `id` values (1–5001). PostgreSQL sequences were never incremented — they stayed at their initial value (~1). Next INSERT tried `id=13` (already exists).  
**Fix:** Reset all sequences after migration:
```sql
SELECT setval(pg_get_serial_sequence('employees', 'id'), MAX(id)) FROM employees;
-- repeat for all tables
```
**Lesson:** After any bulk INSERT with explicit IDs (migration, restore, seed), always reset sequences.

---

## Bug 9: AI assistant always returns `source: "rule_based"` despite API key set

**Symptom:** Groq/Grok key set in Render env vars but every AI response shows `rule_based`.  
**Root cause 1:** `ai_assistant_service.py` gated agent delegation on `session_id` being present AND a key being set. Frontend sends `session_id` but the deployed code was old.  
**Root cause 2:** Old LangChain-based agent had version conflicts (`langchain` / `langchain-core` / `langchain-openai` incompatibilities).  
**Fix:**  
- Rewrote `ai_agent.py` using direct OpenAI SDK (works with Groq, Grok, OpenAI, Gemini — all OpenAI-compatible)  
- Removed session_id gate — agent runs whenever any API key is set  
- Added `isinstance(key, str) and key` check to prevent `MagicMock` in tests from triggering the provider  
**Lesson:** Don't use LangChain for simple tool-calling. Direct SDK is 10x simpler and more reliable.

---

## Bug 10: Groq tests always selected `"groq"` source even in `test_no_keys_returns_rule_based`

**Symptom:** After adding `GROQ_API_KEY` to config, tests that mock `settings` with `GROK_API_KEY=""` etc still returned `source="groq"`.  
**Root cause:** Tests use `MagicMock()` for settings. `MagicMock` returns a truthy mock for any attribute — `mock.GROQ_API_KEY` is a non-empty `MagicMock` object, so `if settings.GROQ_API_KEY:` is always `True`.  
**Fix:** Used `isinstance(key, str) and key` — a `MagicMock` is not a `str`, so this check returns `False` for mocked settings.  
**Lesson:** When patching settings with `MagicMock`, any new attribute you don't explicitly set will be truthy. Use `isinstance` to distinguish real string values from mocks.

---

## Bug 11: JWT tokens expired between restarts (local dev)

**Symptom:** After restarting the backend, all logged-in users get 401 errors.  
**Root cause:** `config.py` auto-rotated `JWT_SECRET_KEY` to a new random hex on every startup if the key matched the placeholder string. When the key is empty, the rotation guard didn't fire.  
**Fix:** Set a fixed `JWT_SECRET_KEY` in `backend/.env`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
**Lesson:** JWT secrets must be fixed and stored in env vars, not generated dynamically at startup.

---

## Bug 12: CORS blocking requests from Netlify

**Symptom:** Browser console shows `CORS error` for every API call from Netlify.  
**Root cause:** `ALLOWED_ORIGINS_RAW` didn't include `https://ethara-frontend12.netlify.app`.  
**Fix:** Updated `ALLOWED_ORIGINS_RAW` in both `config.py` default and Render dashboard.  
**Lesson:** Always add the production frontend URL to CORS origins before deploying. Check browser Network tab → preflight OPTIONS response headers.
