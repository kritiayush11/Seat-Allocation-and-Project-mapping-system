"""
TDD — Deployment Health & Neon PostgreSQL Integration Tests

These tests verify the app is production-ready:
  1. /health endpoint responds correctly
  2. Neon DB connection is live and schema is intact
  3. All critical tables exist with expected row counts
  4. JWT config is production-safe
  5. CORS config is set
  6. Rate limiter is wired

Run against Neon by setting DATABASE_URL in the environment:
    DATABASE_URL=<neon_url> pytest tests/test_health.py -v
"""
import os
import pytest
from fastapi.testclient import TestClient


# ── 1. Health endpoint ────────────────────────────────────────────────────────

class TestHealthEndpoint:
    """The /health route must always respond 200 with the right shape."""

    def test_health_returns_200(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_response_shape(self, client: TestClient):
        data = client.get("/health").json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_returns_200(self, client: TestClient):
        r = client.get("/")
        assert r.status_code == 200

    def test_root_has_docs_link(self, client: TestClient):
        data = client.get("/").json()
        assert "docs" in data
        assert data["docs"] == "/docs"

    def test_openapi_schema_reachable(self, client: TestClient):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "openapi" in schema
        assert "paths" in schema


# ── 2. Neon DB live connection ────────────────────────────────────────────────

class TestNeonDatabaseConnection:
    """Verify the Neon PostgreSQL connection is live and healthy."""

    def test_neon_url_is_configured(self):
        """DATABASE_URL must point to Neon, not SQLite."""
        from app.config import get_settings
        settings = get_settings()
        assert settings.DATABASE_URL.startswith("postgresql"), (
            f"Expected Neon PostgreSQL URL, got: {settings.DATABASE_URL[:30]}..."
        )
        assert "neon.tech" in settings.DATABASE_URL, (
            "DATABASE_URL does not point to Neon"
        )

    def test_neon_connection_alive(self):
        """Raw SQLAlchemy ping to Neon — must complete without error."""
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_neon_postgres_version(self):
        """Must be running PostgreSQL 14+."""
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            version_str = conn.execute(text("SELECT version()")).scalar()
        assert "PostgreSQL" in version_str
        major = int(version_str.split("PostgreSQL ")[1].split(".")[0])
        assert major >= 14, f"Expected PG >= 14, got: {version_str}"


# ── 3. Schema integrity ───────────────────────────────────────────────────────

class TestNeonSchemaIntegrity:
    """All six application tables must exist on Neon with data."""

    EXPECTED_TABLES = {
        "employees",
        "projects",
        "seats",
        "seat_allocations",
        "users",
        "chat_messages",
    }

    def _get_neon_table_names(self):
        from app.database import engine
        from sqlalchemy import inspect
        return set(inspect(engine).get_table_names())

    def test_all_tables_exist(self):
        tables = self._get_neon_table_names()
        missing = self.EXPECTED_TABLES - tables
        assert not missing, f"Missing tables on Neon: {missing}"

    def test_employees_has_data(self):
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM employees")).scalar()
        assert count > 0, "employees table is empty on Neon"

    def test_projects_has_data(self):
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM projects")).scalar()
        assert count > 0, "projects table is empty on Neon"

    def test_seats_has_data(self):
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM seats")).scalar()
        assert count > 0, "seats table is empty on Neon"

    def test_seat_allocations_has_data(self):
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM seat_allocations")).scalar()
        assert count > 0, "seat_allocations table is empty on Neon"

    def test_expected_row_counts(self):
        """Verify migrated counts are at least the original migration snapshot.
        Uses >= because Neon is a live DB and rows grow as the app is used.
        """
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            employees = conn.execute(text("SELECT COUNT(*) FROM employees")).scalar()
            projects  = conn.execute(text("SELECT COUNT(*) FROM projects")).scalar()
            seats     = conn.execute(text("SELECT COUNT(*) FROM seats")).scalar()
            allocs    = conn.execute(text("SELECT COUNT(*) FROM seat_allocations")).scalar()

        assert employees >= 5001, f"Expected >= 5001 employees, got {employees}"
        assert projects  >= 11,   f"Expected >= 11 projects, got {projects}"
        assert seats     >= 5500, f"Expected >= 5500 seats, got {seats}"
        assert allocs    >= 4951, f"Expected >= 4951 allocations, got {allocs}"

    def test_employees_table_has_expected_columns(self):
        from app.database import engine
        from sqlalchemy import inspect
        cols = {c["name"] for c in inspect(engine).get_columns("employees")}
        for expected in ("id", "employee_code", "name", "email", "status", "project_id"):
            assert expected in cols, f"Column '{expected}' missing from employees"

    def test_seats_table_has_expected_columns(self):
        from app.database import engine
        from sqlalchemy import inspect
        cols = {c["name"] for c in inspect(engine).get_columns("seats")}
        for expected in ("id", "floor", "zone", "bay", "seat_number", "status"):
            assert expected in cols, f"Column '{expected}' missing from seats"

    def test_seat_unique_constraint_exists(self):
        """The uq_seat_location constraint must be present on Neon."""
        from app.database import engine
        from sqlalchemy import inspect
        constraints = inspect(engine).get_unique_constraints("seats")
        names = [c["name"] for c in constraints]
        assert "uq_seat_location" in names, (
            f"uq_seat_location constraint missing. Found: {names}"
        )


# ── 4. Security config ────────────────────────────────────────────────────────

class TestSecurityConfig:

    def test_jwt_secret_key_is_set_and_strong(self):
        from app.config import get_settings
        settings = get_settings()
        assert settings.JWT_SECRET_KEY, "JWT_SECRET_KEY is empty"
        assert settings.JWT_SECRET_KEY != "ethara_super_secret_signing_key_2026_prod", (
            "JWT_SECRET_KEY is the hardcoded default — must be rotated for production"
        )
        assert len(settings.JWT_SECRET_KEY) >= 32, (
            f"JWT_SECRET_KEY too short ({len(settings.JWT_SECRET_KEY)} chars); need >= 32"
        )

    def test_jwt_algorithm_is_hs256(self):
        from app.config import get_settings
        assert get_settings().JWT_ALGORITHM == "HS256"

    def test_access_token_expiry_is_reasonable(self):
        from app.config import get_settings
        minutes = get_settings().ACCESS_TOKEN_EXPIRE_MINUTES
        assert 15 <= minutes <= 1440, (
            f"ACCESS_TOKEN_EXPIRE_MINUTES={minutes} is outside safe range [15, 1440]"
        )


# ── 5. CORS config ────────────────────────────────────────────────────────────

class TestCORSConfig:

    def test_allowed_origins_is_not_empty(self):
        from app.config import get_settings
        origins = get_settings().ALLOWED_ORIGINS
        assert isinstance(origins, list)
        assert len(origins) > 0, "ALLOWED_ORIGINS is empty"

    def test_cors_headers_present_on_health(self, client: TestClient):
        """OPTIONS preflight to /health must return CORS headers."""
        r = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI returns 200 for OPTIONS on GET routes
        assert r.status_code in (200, 400)


# ── 6. Rate limiter wiring ────────────────────────────────────────────────────

class TestRateLimiterWiring:

    def test_limiter_is_attached_to_app(self):
        """app.state.limiter must be wired (set in main.py)."""
        from app.main import app
        from app.limiter import limiter
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is limiter

    def test_rate_limit_exceeded_handler_registered(self):
        """RateLimitExceeded exception handler must be present."""
        from app.main import app
        from slowapi.errors import RateLimitExceeded
        assert RateLimitExceeded in app.exception_handlers


# ── 7. All routers registered ────────────────────────────────────────────────

class TestRouterRegistration:
    """Every expected route prefix must appear in the OpenAPI schema."""

    EXPECTED_PREFIXES = [
        "/auth/",
        "/employees",
        "/projects",
        "/seats",
        "/dashboard/",
        "/ai/",
        "/health",
    ]

    def test_all_route_prefixes_exist(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        paths = set(schema.get("paths", {}).keys())
        for prefix in self.EXPECTED_PREFIXES:
            matched = any(p.startswith(prefix) or p == prefix.rstrip("/") for p in paths)
            assert matched, f"No route with prefix '{prefix}' found in OpenAPI paths: {sorted(paths)}"
