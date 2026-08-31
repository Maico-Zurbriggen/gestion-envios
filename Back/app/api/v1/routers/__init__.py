from app.api.v1.routers.admin import router as admin_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.health import router as health_router

__all__ = ["admin_router", "auth_router", "health_router"]

