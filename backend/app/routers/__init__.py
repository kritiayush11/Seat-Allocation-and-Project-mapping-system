from .employees import router as employees_router
from .projects import router as projects_router
from .seats import router as seats_router
from .dashboard import router as dashboard_router
from .ai_assistant import router as ai_router
from .seed import router as seed_router
from .auth import router as auth_router

__all__ = [
    "employees_router", "projects_router", "seats_router",
    "dashboard_router", "ai_router", "seed_router", "auth_router",
]
