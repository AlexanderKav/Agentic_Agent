# app/api/v1/endpoints/analysis/__init__.py
"""Analysis endpoints package."""

from fastapi import APIRouter
from slowapi import Limiter
from slowapi.util import get_remote_address

from .chart import router as chart_router
from .database import router as database_router
from .file import router as file_router
from .google_sheets import router as google_sheets_router
from .history import router as history_router
from .sqlite import router as sqlite_router

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# Create main router
router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

# Include all sub-routers
router.include_router(chart_router)
router.include_router(database_router)
router.include_router(file_router)
router.include_router(google_sheets_router)
router.include_router(history_router)
router.include_router(sqlite_router)

__all__ = ['router', 'limiter']