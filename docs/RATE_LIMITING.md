# Rate Limiting — Design, Algorithm, and Operations Guide

> **Ethara Seat Allocation & Project Mapping System**  
> Implementation: `slowapi 0.1.9` · Algorithm: Fixed Window Counter · Per-IP enforcement

---

## Table of Contents

1. [Why Rate Limiting](#1-why-rate-limiting)
2. [Algorithm Comparison](#2-algorithm-comparison)
3. [Why Fixed Window Counter](#3-why-fixed-window-counter)
4. [SOLID Principles Applied](#4-solid-principles-applied)
5. [Limits Reference Table](#5-limits-reference-table)
6. [Implementation Architecture](#6-implementation-architecture)
7. [TDD Approach — Red → Green](#7-tdd-approach--red--green)
8. [Testing the Limits with curl](#8-testing-the-limits-with-curl)
9. [Verifying in Tests](#9-verifying-in-tests)
10. [Production: Upgrading to Redis](#10-production-upgrading-to-redis)

---

## 1. Why Rate Limiting

This project has three categories of endpoints that need rate limiting for different reasons:

| Threat | Affected Endpoint | Without Limiting |
|--------|------------------|-----------------|
| **Brute-force password attack** | `POST /auth/login` | Attacker can try millions of passwords |
| **Account spam** | `POST /auth/signup` | Bot can create thousands of fake accounts |
| **LLM API cost abuse** | `POST /ai/query` | Each query may call Gemini/OpenAI — metered cost |
| **Seat hoarding / DoS** | `POST /seats/allocate` | Bot can allocate all seats in seconds |
| **Scraping / DB overload** | `GET /seats` | Automated scraper can exhaust DB connection pool |

---

## 2. Algorithm Comparison

Five common rate limiting algorithms were evaluated:

### 2.1 Fixed Window Counter
```
Divide time into fixed windows (e.g. each minute = one window).
Count requests per IP in the current window.
Reset counter when window rolls over.

Window:  |---- 0:00-1:00 ----|---- 1:00-2:00 ----|
Limit:   5 req/min
Allowed: ✓ ✓ ✓ ✓ ✓ ✗ ✗ | ✓ ✓ ✓ ✓ ✓ ✗
```
**Pros:** Simple, O(1) memory per IP, easy to reason about  
**Cons:** Boundary burst — up to 2× limit in a brief window at the minute boundary

### 2.2 Sliding Window Log
```
Keep a log of timestamps for each request per IP.
On each request, evict entries older than the window.
Count remaining — if > limit, reject.

Exact: no boundary burst possible.
```
**Pros:** Most accurate — true "last 60 seconds" enforcement  
**Cons:** O(n) memory per IP (stores every timestamp), slow at high throughput

### 2.3 Sliding Window Counter
```
Hybrid: track two adjacent fixed windows and calculate
a weighted count interpolated by position in the window.

Approximation (not exact) but much more memory-efficient.
```
**Pros:** Smooths the boundary burst, O(1) memory  
**Cons:** Approximate — allows a small overshoot at boundary

### 2.4 Token Bucket
```
Each IP gets a "bucket" that fills at a fixed rate (e.g. 1 token/sec).
Each request consumes 1 token. If bucket is empty, reject.
Bucket has a max capacity (burst limit).

Allows short burst up to capacity, then enforces average rate.
```
**Pros:** Naturally models bursty traffic; great for APIs  
**Cons:** Slightly more complex; harder to explain to end users

### 2.5 Leaky Bucket
```
Requests enter a queue (the "bucket").
Processed at a fixed output rate.
If queue is full, incoming request is dropped.
```
**Pros:** Smoothest output rate, prevents any spike  
**Cons:** Adds latency (requests wait in queue); overkill for web APIs

### Comparison Summary

| Algorithm | Memory | Burst handling | Accuracy | Complexity | Best for |
|-----------|--------|---------------|----------|------------|---------|
| **Fixed Window** ✅ | O(1) | Allows boundary burst | Approximate | Lowest | Most web APIs |
| Sliding Window Log | O(n) | None | Exact | Medium | Low-traffic, strict |
| Sliding Window Counter | O(1) | Minimal | Good | Medium | High-traffic APIs |
| Token Bucket | O(1) | Configurable | Good | Medium | Bursty clients |
| Leaky Bucket | O(n) | None | Exact | Highest | Queue-based systems |

---

## 3. Why Fixed Window Counter

**We chose Fixed Window Counter for this project** for three reasons:

**1. Threat model matches.**  
The risk we are guarding against is sustained automated attacks (credential stuffing, scraping, LLM cost abuse) — not legitimate users doing brief bursts. A brute-force script submitting 100 login attempts per minute is stopped just as effectively by a fixed window as by a leaky bucket.

**2. In-memory simplicity.**  
The project currently runs a single FastAPI instance. Fixed window counters are O(1) per IP — no log structures, no interpolation. The `limits` library (used by slowapi) implements this with a simple dict-based store.

**3. The boundary burst concern doesn't apply here.**  
The boundary burst problem matters for APIs with burst-friendly limits like 1000/minute. Our tightest limit is 5/minute on login — even with a 2× boundary burst that's 10 attempts in 2 seconds, which is still a very tight brute-force constraint.

**When to switch:** If this scales to multiple instances, switch to **Sliding Window Counter with Redis** — it's accurate, O(1), and Redis handles atomic increments across instances natively (see [Section 10](#10-production-upgrading-to-redis)).

---

## 4. SOLID Principles Applied

### Single Responsibility (SRP)
The limiter is in its own module `backend/app/limiter.py`. It owns exactly one thing: the `Limiter` instance and the IP resolution function. `main.py` wires it into the app, routers declare their own limits — no concern is mixed.

```
limiter.py      → owns the Limiter instance + IP key function
main.py         → wires middleware + exception handler
routers/*.py    → declare @limiter.limit("N/period") per route
tests/conftest  → resets limiter state between tests
```

### Open/Closed (OCP)
Adding a limit to a new route requires **zero changes** to `limiter.py` or `main.py`. You only add a decorator to the new route. Existing routes are untouched.

```python
# Adding a new limit: touch only the new route
@router.post("/new-endpoint")
@limiter.limit("30/minute")       # ← only change needed
def new_endpoint(request: Request, ...):
    ...
```

### Dependency Inversion (DIP)
Routers import from `app.limiter` (the abstraction), never from `app.main`. This breaks the circular import (`main → routers → main`) and means routers don't depend on the application assembly layer.

```python
# ✅ Correct — depends on the limiter module
from ..limiter import limiter

# ❌ Wrong — circular import
from ..main import limiter
```

### Interface Segregation (ISP)
`default_limits=[]` means no global default is applied to routes that don't need it (health check, seed endpoint, static reads). Each route declares only what it needs.

### Liskov Substitution (LSP)
The `_get_client_ip` key function is substitutable — you can swap it for any callable `(Request) -> str` without changing how the limiter works. In production, you might pass a different key function to rate-limit by authenticated user ID instead of IP.

---

## 5. Limits Reference Table

| Endpoint | Method | Limit | Reason |
|----------|--------|-------|--------|
| `/auth/login` | POST | **5/minute** | Brute-force password protection |
| `/auth/signup` | POST | **5/minute** | Account spam prevention |
| `/seats` | GET | **60/minute** | DB scraping / connection pool protection |
| `/seats/allocate` | POST | **20/minute** | Seat hoarding / race condition abuse |
| `/ai/query` | POST | **10/minute** | LLM API cost protection (Gemini/OpenAI/Grok) |
| All others | any | none | No specific threat identified |

**Scope:** per client IP, resolved via `X-Forwarded-For` (set by Nginx) or `request.client.host`.

**429 Response format:**
```json
{
  "error": "5 per 1 minute"
}
```

---

## 6. Implementation Architecture

```
backend/
├── app/
│   ├── limiter.py              ← Limiter instance + _get_client_ip key function
│   ├── main.py                 ← app.state.limiter, SlowAPIMiddleware, exception handler
│   └── routers/
│       ├── auth.py             ← @limiter.limit("5/minute") on login + signup
│       ├── seats.py            ← @limiter.limit("60/minute") on GET, @limiter.limit("20/minute") on allocate
│       └── ai_assistant.py     ← @limiter.limit("10/minute") on /ai/query
└── tests/
    ├── conftest.py             ← autouse reset_rate_limiter fixture (runs before every test)
    └── test_rate_limiting.py   ← 13 tests across 6 classes
```

**Key code snippets:**

```python
# limiter.py — single source of truth
from slowapi import Limiter
from fastapi import Request

def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

limiter = Limiter(key_func=_get_client_ip, default_limits=[])
```

```python
# main.py — wiring (nothing else here touches rate limiting)
from .limiter import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

```python
# auth.py — per-route decoration
@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, data: UserLogin, ...):
    ...
```

> **Important:** The `request: Request` parameter must be the **first** positional parameter in any rate-limited route function. slowapi reads the request object to resolve the client IP.

---

## 7. TDD Approach — Red → Green

All tests were written **before** the implementation. The test file is at:
`backend/tests/test_rate_limiting.py`

### Red phase (before slowapi was installed)
```
FAILED test_login_blocked_on_6th_request       → assert 401 == 429
FAILED test_signup_blocked_on_6th_request      → assert 422 == 429
FAILED test_seats_get_blocked_on_61st_request  → assert 200 == 429
FAILED test_allocate_blocked_on_21st_request   → assert 404 == 429
FAILED test_ai_query_blocked_on_11th_request   → assert 200 == 429
... (8 failing)
```

### Green phase (after implementation)
```
95 passed, 7 warnings in 6.33s
```

### Edge cases covered
| Test | What it verifies |
|------|-----------------|
| `test_login_allowed_within_limit` | 5 requests pass (no false positives) |
| `test_login_blocked_on_6th_request` | 6th returns 429 |
| `test_rate_limit_response_is_json` | 429 body is valid JSON, not crash |
| `test_signup_allowed_within_limit` | 5 signups pass |
| `test_signup_blocked_on_6th_request` | 6th signup blocked |
| `test_seats_get_allowed_within_limit` | 60 GETs pass |
| `test_seats_get_blocked_on_61st_request` | 61st blocked |
| `test_allocate_allowed_within_limit` | 20 allocations pass |
| `test_allocate_blocked_on_21st_request` | 21st blocked |
| `test_ai_query_allowed_within_limit` | 10 queries pass |
| `test_ai_query_blocked_on_11th_request` | 11th blocked |
| `test_ai_rate_limit_response_is_json` | 429 body is JSON |
| `test_different_ips_have_independent_limits` | IP A blocked ≠ IP B blocked |

---

## 8. Testing the Limits with curl

### Prerequisites
Docker stack must be running:
```bash
docker compose up -d
```

Get an auth token (needed for protected endpoints):
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"admin","password":"adminpassword"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

---

### 8.1 Test login rate limit (5/minute)

Run 6 login attempts in quick succession — the 6th must return 429:

```bash
for i in $(seq 1 6); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username_or_email":"nobody","password":"wrongpassword"}')
  echo "Request $i: HTTP $STATUS"
done
```

Expected output:
```
Request 1: HTTP 401
Request 2: HTTP 401
Request 3: HTTP 401
Request 4: HTTP 401
Request 5: HTTP 401
Request 6: HTTP 429   ← rate limited
```

See the full 429 response body:
```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"nobody","password":"wrong"}' | python3 -m json.tool
```

---

### 8.2 Test signup rate limit (5/minute)

```bash
for i in $(seq 1 6); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/auth/signup \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"testuser${i}\",\"email\":\"test${i}@x.ai\",\"password\":\"password123\"}")
  echo "Request $i: HTTP $STATUS"
done
```

Expected: first 5 are 201 or 422 (duplicate), 6th is **429**.

---

### 8.3 Test GET /seats rate limit (60/minute)

Send 61 requests and watch the last one get blocked:

```bash
for i in $(seq 1 61); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/seats)
  if [ "$STATUS" = "429" ]; then
    echo "Request $i: HTTP $STATUS ← RATE LIMITED"
    break
  fi
done
```

---

### 8.4 Test seats/allocate rate limit (20/minute)

```bash
for i in $(seq 1 21); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/seats/allocate \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"employee_id": 9999}')
  echo "Request $i: HTTP $STATUS"
  [ "$STATUS" = "429" ] && break
done
```

Expected: requests 1-20 are **404** (employee not found), request 21 is **429**.

---

### 8.5 Test AI query rate limit (10/minute)

```bash
for i in $(seq 1 11); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/ai/query \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"query": "how many seats are available"}')
  echo "Request $i: HTTP $STATUS"
  [ "$STATUS" = "429" ] && break
done
```

Expected: requests 1-10 are **200**, request 11 is **429**.

---

### 8.6 Verify per-IP isolation

Two IPs must have independent counters. Use `X-Forwarded-For` to spoof (only works if Nginx is configured to pass it):

```bash
# Exhaust IP A
for i in $(seq 1 5); do
  curl -s -o /dev/null -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-For: 10.0.1.1" \
    -d '{"username_or_email":"x","password":"y"}'
done

# IP A should now be blocked
echo "IP A:"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 10.0.1.1" \
  -d '{"username_or_email":"x","password":"y"}'

# IP B should still be allowed
echo "IP B:"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 10.0.1.2" \
  -d '{"username_or_email":"x","password":"y"}'
```

Expected:
```
IP A: HTTP 429
IP B: HTTP 401    ← allowed (401 = wrong password, not rate limited)
```

---

### 8.7 Wait for the window to reset

Rate limits reset after 60 seconds (the window). To verify:

```bash
# Hit the login limit
for i in $(seq 1 6); do
  curl -s -o /dev/null -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username_or_email":"x","password":"y"}'
done

echo "Blocked. Waiting 60 seconds..."
sleep 60

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"x","password":"y"}')
echo "After reset: HTTP $STATUS"   # Should be 401, not 429
```

---

### 8.8 Run all rate limit tests (pytest)

```bash
cd backend

# Run only rate limiting tests
.venv/bin/python3 -m pytest tests/test_rate_limiting.py -v

# Run with verbose output showing every request
.venv/bin/python3 -m pytest tests/test_rate_limiting.py -v -s

# Run a single test class
.venv/bin/python3 -m pytest tests/test_rate_limiting.py::TestLoginRateLimit -v

# Run a single test
.venv/bin/python3 -m pytest tests/test_rate_limiting.py::TestLoginRateLimit::test_login_blocked_on_6th_request -v

# Run full suite (95 tests)
.venv/bin/python3 -m pytest tests/ -v

# Run full suite with coverage
.venv/bin/python3 -m pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 9. Verifying in Tests

The test infrastructure handles two important concerns:

### Limiter state reset
```python
# backend/tests/conftest.py
@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Runs before EVERY test — prevents state bleed between tests."""
    from app.limiter import limiter
    limiter.reset()
    yield
```

This is `autouse=True` — it fires automatically for every test in every file, including `test_auth.py`, `test_seats.py`, etc. Without this, a test that exhausts the login limit would cause `test_login_success` in `test_auth.py` to fail with 429.

### IP spoofing in tests
```python
SPOOFED_IP_HEADERS = {"X-Forwarded-For": "10.0.0.1"}

# Use consistent IP so all requests in a test count toward the same bucket
r = client.post("/auth/login", json={...}, headers=SPOOFED_IP_HEADERS)
```

The `_get_client_ip` function in `limiter.py` reads `X-Forwarded-For` first. By spoofing a specific IP in test headers, all requests within a test hit the same counter bucket — making limit enforcement deterministic.

---

## 10. Production: Upgrading to Redis

The current in-memory storage is **not suitable for production** with multiple backend instances, because each instance has its own counter and they don't share state.

### Switch to Redis (one-line change)

```python
# backend/app/limiter.py
limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=[],
    storage_uri="redis://redis:6379",   # ← add this
)
```

### Add Redis to docker-compose.yml

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"

  backend:
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - db
      - redis
```

### Install the Redis driver

```bash
pip install slowapi[redis]
# or
pip install limits[redis]
```

### Why Redis for production

| Concern | In-memory | Redis |
|---------|-----------|-------|
| Multiple backend instances | ❌ Each has its own counter | ✅ Shared atomic counter |
| Container restart | ❌ Counters reset | ✅ Persists across restarts |
| Memory overhead | ✅ None | ✅ Minimal (a few bytes per IP) |
| Added latency | ✅ None | ~1ms per request |
| Complexity | ✅ Zero | Low (one service) |

The `limits` library (used by slowapi) handles Redis atomicity via `INCR` + `EXPIRE` — a standard, safe Redis pattern.
