# app/api/v1/endpoints/monitoring.py
from fastapi import APIRouter
from datetime import datetime, timedelta

from app.api.v1.models.responses import HealthResponse
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from agents.monitoring import get_cost_tracker, get_performance_tracker, get_audit_logger
from app.services.key_rotation import get_key_rotation_service
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models import User

# ✅ Make sure this line is present
router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

@router.get("/costs")
async def get_costs(days: int = 7):
    """Get cost tracking data"""
    tracker = get_cost_tracker()
    return tracker.get_cost_report(days=days)

@router.get("/performance")
async def get_performance():
    """Get performance metrics"""
    tracker = get_performance_tracker()
    return tracker.get_all_stats()

@router.get("/audit")
async def get_audit_logs(
    user: str = None,
    agent: str = None,
    action: str = None,
    days: int = 7
):
    """Get audit logs"""
    logger = get_audit_logger()
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return logger.query_audit(
        user=user,
        agent=agent,
        action_type=action,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )



@router.get("/key-rotation-status")
async def get_key_rotation_status(
    current_user: User = Depends(get_current_user)
):
    """Get key rotation status (admin only)"""
    # In production, add admin check
    rotation_service = get_key_rotation_service()
    return rotation_service.get_all_rotation_status()