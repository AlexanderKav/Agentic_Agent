# app/api/v1/endpoints/monitoring.py
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from agents.monitoring import get_audit_logger, get_cost_tracker, get_performance_tracker
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models import User
from app.services.key_rotation import get_key_rotation_service

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.get("/costs")
@limiter.limit("30/minute")
async def get_costs(request: Request, days: int = 7) -> dict:
    """
    Get cost tracking data for OpenAI API usage.
    
    Args:
        days: Number of days to look back (default: 7)
    """
    # Validate days parameter
    if days < 1:
        days = 1
    if days > 90:
        days = 90
    
    tracker = get_cost_tracker()
    report = tracker.get_cost_report(days=days)
    
    logger.info(f"Cost report requested for {days} days")
    
    return report


@router.get("/performance")
@limiter.limit("30/minute")
async def get_performance(request: Request) -> dict:
    """Get performance metrics for all agents."""
    tracker = get_performance_tracker()
    stats = tracker.get_all_stats()
    
    logger.info("Performance metrics requested")
    
    return stats


@router.get("/audit")
@limiter.limit("20/minute")
async def get_audit_logs(
    request: Request,
    user: Optional[str] = None,
    agent: Optional[str] = None,
    action: Optional[str] = None,
    days: int = 7
) -> dict:
    """
    Get audit logs for system actions.
    
    Args:
        user: Filter by username
        agent: Filter by agent name
        action: Filter by action type
        days: Number of days to look back (default: 7, max: 90)
    """
    # Validate days parameter
    if days < 1:
        days = 1
    if days > 90:
        days = 90
    
    audit_logger = get_audit_logger()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    logs = audit_logger.query_audit(
        user=user,
        agent=agent,
        action_type=action,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    logger.info(f"Audit logs requested for days={days}, user={user}, agent={agent}, action={action}")
    
    return logs


@router.get("/key-rotation-status")
@limiter.limit("10/minute")
async def get_key_rotation_status(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get key rotation status for all tracked keys.
    
    This endpoint requires admin privileges.
    """
    # Check if user is admin
    if not current_user.is_admin:
        logger.warning(
            f"Non-admin user '{current_user.username}' (ID: {current_user.id}) "
            "attempted to access key rotation status"
        )
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    rotation_service = get_key_rotation_service()
    status = rotation_service.get_all_rotation_status()
    
    logger.info(f"Admin user '{current_user.username}' accessed key rotation status")
    
    return status


# Optional: Add a health check for monitoring services
@router.get("/health")
async def monitoring_health() -> dict:
    """Check if monitoring services are healthy."""
    try:
        cost_tracker = get_cost_tracker()
        perf_tracker = get_performance_tracker()
        audit_logger = get_audit_logger()
        
        return {
            "status": "healthy",
            "services": {
                "cost_tracking": cost_tracker is not None,
                "performance_tracking": perf_tracker is not None,
                "audit_logging": audit_logger is not None
            }
        }
    except Exception as e:
        logger.error(f"Monitoring health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


__all__ = ['router']