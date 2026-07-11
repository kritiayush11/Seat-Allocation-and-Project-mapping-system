"""
TDD — Rate Limiting Tests (slowapi / Fixed Window Counter algorithm)

Red → Green → Refactor

Limits under test (matching the spec exactly):
  GET  /seats           → 60/minute
  POST /seats/allocate  → 20/minute  (book)
  POST /auth/login      → 5/minute
  POST /auth/signup     → 5/minute
  POST /ai/query        → 10/minute

Limiter state is reset before every test by the autouse fixture in conftest.py.
Each test class uses a spoofed X-Forwarded-For header so the custom _get_client_ip
function in limiter.py resolves requests to a known, consistent IP.
"""
import pytest
from fastapi.testclient import TestClient

# ── Shared constants ──────────────────────────────────────────────────────────

SPOOFED_IP_HEADERS = {"X-Forwarded-For": "10.0.0.1"}


# ── 1. POST /auth/login — 5/minute ───────────────────────────────────────────

class TestLoginRateLimit:
    """Brute-force protection: 5 requests/minute per IP. 6th must return 429."""

    def test_login_allowed_within_limit(self, client: TestClient):
        """First 5 login attempts must NOT be rate-limited (may 401, never 429)."""
        for i in range(5):
            r = client.post(
                "/auth/login",
                json={"username_or_email": "nobody", "password": "wrong"},
                headers=SPOOFED_IP_HEADERS,
            )
            assert r.status_code != 429, f"Request {i+1} was rate-limited unexpectedly"

    def test_login_blocked_on_6th_request(self, client: TestClient):
        """6th login request within a minute must return 429 Too Many Requests."""
        for _ in range(5):
            client.post(
                "/auth/login",
                json={"username_or_email": "nobody", "password": "wrong"},
                headers=SPOOFED_IP_HEADERS,
            )
        r = client.post(
            "/auth/login",
            json={"username_or_email": "nobody", "password": "wrong"},
            headers=SPOOFED_IP_HEADERS,
        )
        assert r.status_code == 429, "Expected 429 after exceeding login limit"

    def test_rate_limit_response_is_json(self, client: TestClient):
        """429 response body must be JSON — not an empty body or HTML crash page."""
        for _ in range(5):
            client.post(
                "/auth/login",
                json={"username_or_email": "nobody", "password": "wrong"},
                headers=SPOOFED_IP_HEADERS,
            )
        r = client.post(
            "/auth/login",
            json={"username_or_email": "nobody", "password": "wrong"},
            headers=SPOOFED_IP_HEADERS,
        )
        assert r.status_code == 429
        assert r.headers.get("content-type", "").startswith("application/json")
        body = r.json()
        assert "error" in body or "detail" in body


# ── 2. POST /auth/signup — 5/minute ──────────────────────────────────────────

class TestSignupRateLimit:
    """Account-spam protection: 5 requests/minute per IP."""

    def test_signup_allowed_within_limit(self, client: TestClient):
        for i in range(5):
            r = client.post(
                "/auth/signup",
                json={
                    "username": f"spamuser{i}",
                    "email": f"spam{i}@test.ai",
                    "password": "password123",
                },
                headers=SPOOFED_IP_HEADERS,
            )
            assert r.status_code != 429, f"Signup {i+1} was rate-limited unexpectedly"

    def test_signup_blocked_on_6th_request(self, client: TestClient):
        for i in range(5):
            client.post(
                "/auth/signup",
                json={
                    "username": f"spamuser{i}",
                    "email": f"spam{i}@test.ai",
                    "password": "password123",
                },
                headers=SPOOFED_IP_HEADERS,
            )
        r = client.post(
            "/auth/signup",
            json={"username": "spamuser99", "email": "spam99@test.ai", "password": "password123"},
            headers=SPOOFED_IP_HEADERS,
        )
        assert r.status_code == 429


# ── 3. GET /seats — 60/minute ────────────────────────────────────────────────

class TestSeatsGetRateLimit:
    """Browse limit: 60 req/min per IP. 61st must be blocked."""

    def test_seats_get_allowed_within_limit(self, client: TestClient):
        for i in range(60):
            r = client.get("/seats", headers=SPOOFED_IP_HEADERS)
            assert r.status_code != 429, f"GET /seats request {i+1} was unexpectedly limited"

    def test_seats_get_blocked_on_61st_request(self, client: TestClient):
        for _ in range(60):
            client.get("/seats", headers=SPOOFED_IP_HEADERS)
        r = client.get("/seats", headers=SPOOFED_IP_HEADERS)
        assert r.status_code == 429


# ── 4. POST /seats/allocate — 20/minute ──────────────────────────────────────

class TestSeatAllocateRateLimit:
    """Booking limit: 20 req/min per IP. Prevents seat hoarding."""

    def test_allocate_allowed_within_limit(self, client: TestClient):
        for i in range(20):
            r = client.post(
                "/seats/allocate",
                json={"employee_id": 9999},  # 404 is fine — we only care it's not 429
                headers=SPOOFED_IP_HEADERS,
            )
            assert r.status_code != 429, f"Allocate request {i+1} was unexpectedly limited"

    def test_allocate_blocked_on_21st_request(self, client: TestClient):
        for _ in range(20):
            client.post(
                "/seats/allocate",
                json={"employee_id": 9999},
                headers=SPOOFED_IP_HEADERS,
            )
        r = client.post(
            "/seats/allocate",
            json={"employee_id": 9999},
            headers=SPOOFED_IP_HEADERS,
        )
        assert r.status_code == 429


# ── 5. POST /ai/query — 10/minute ────────────────────────────────────────────

class TestAIQueryRateLimit:
    """LLM cost protection: 10 req/min per IP."""

    def test_ai_query_allowed_within_limit(self, client: TestClient):
        for i in range(10):
            r = client.post(
                "/ai/query",
                json={"query": "where is john"},
                headers=SPOOFED_IP_HEADERS,
            )
            assert r.status_code != 429, f"AI query {i+1} was unexpectedly limited"

    def test_ai_query_blocked_on_11th_request(self, client: TestClient):
        for _ in range(10):
            client.post(
                "/ai/query",
                json={"query": "where is john"},
                headers=SPOOFED_IP_HEADERS,
            )
        r = client.post(
            "/ai/query",
            json={"query": "where is john"},
            headers=SPOOFED_IP_HEADERS,
        )
        assert r.status_code == 429

    def test_ai_rate_limit_response_is_json(self, client: TestClient):
        """429 body must be JSON — not an empty body or server crash."""
        for _ in range(10):
            client.post("/ai/query", json={"query": "x x x"}, headers=SPOOFED_IP_HEADERS)
        r = client.post("/ai/query", json={"query": "x x x"}, headers=SPOOFED_IP_HEADERS)
        assert r.status_code == 429
        assert r.headers.get("content-type", "").startswith("application/json")


# ── 6. Per-IP isolation ───────────────────────────────────────────────────────

class TestRateLimitIsPerIP:
    """Rate limits must be scoped per client IP, not globally."""

    def test_different_ips_have_independent_limits(self, client: TestClient):
        """Exhausting IP A's limit must NOT block IP B."""
        ip_a = {"X-Forwarded-For": "10.0.1.1"}
        ip_b = {"X-Forwarded-For": "10.0.1.2"}

        # Exhaust IP A
        for _ in range(5):
            client.post(
                "/auth/login",
                json={"username_or_email": "x", "password": "y"},
                headers=ip_a,
            )
        blocked = client.post(
            "/auth/login",
            json={"username_or_email": "x", "password": "y"},
            headers=ip_a,
        )
        assert blocked.status_code == 429

        # IP B must still be allowed
        r_b = client.post(
            "/auth/login",
            json={"username_or_email": "x", "password": "y"},
            headers=ip_b,
        )
        assert r_b.status_code != 429, "IP B should not be blocked by IP A's limit"
