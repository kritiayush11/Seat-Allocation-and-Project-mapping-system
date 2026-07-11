"""
Rate limiter — Single Responsibility: owns the slowapi Limiter instance.

Kept in its own module to avoid circular imports between main.py and routers.
Both main.py (for wiring middleware) and routers (for @limiter.limit decorators)
import from here — neither depends on the other.

Algorithm: Fixed Window Counter (slowapi default via `limits` library)
Storage:   In-memory (default) — swap to Redis in production:
             Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")

Key function: prefers X-Forwarded-For header (set by Nginx proxy) so that the
real client IP is used in production, not the internal proxy address. Falls back
to request.client.host for direct connections (local dev, tests).
"""
from fastapi import Request
from slowapi import Limiter


def _get_client_ip(request: Request) -> str:
    """
    Resolve the real client IP.
    Checks X-Forwarded-For first (set by Nginx / load balancers),
    then falls back to the direct connection address.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list; the first is the client
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=[],      # no global default — each route declares its own
    headers_enabled=False,  # Retry-After headers require response: Response param on each route
)
