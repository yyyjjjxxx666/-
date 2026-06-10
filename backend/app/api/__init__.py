from fastapi import APIRouter
from .auth import router as auth_router
from .clubs import router as clubs_router
from .activities import router as activities_router
from .ai_services import router as ai_router
from .notifications import router as notifications_router
from .admin import router as admin_router

api_router = APIRouter(redirect_slashes=True)
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(clubs_router, prefix="/clubs")
api_router.include_router(activities_router, prefix="/activities")
api_router.include_router(ai_router, prefix="/ai")
api_router.include_router(notifications_router, prefix="/notifications")
api_router.include_router(admin_router, prefix="/admin")
