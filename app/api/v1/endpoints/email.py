import logging
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models.analysis import AnalysisHistory
from app.api.v1.models.user import User
from app.core.database import get_db
from app.services.email import EmailService

router = APIRouter(prefix="/api/v1/email", tags=["Email"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


class EmailRequest(BaseModel):
    """Request model for sending analysis via email."""
    to_email: EmailStr
    analysis_id: int | None = None
    include_charts: bool = True

    @field_validator('to_email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not v or '@' not in v:
            raise ValueError('Invalid email address')
        return v


@router.post("/send-analysis")
@limiter.limit("10/minute")
async def send_analysis(
    request: Request,
    email_request: EmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Send analysis results via email.
    
    If analysis_id is provided, sends that specific analysis.
    Otherwise, sends the most recent analysis for the user.
    """
    # 🔥 UPDATED: Check if SendGrid is configured instead of SMTP
    if not os.getenv("SENDGRID_API_KEY"):
        logger.error("Email service not configured - SendGrid API key missing")
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Please contact administrator."
        )

    # Get analysis
    if email_request.analysis_id:
        analysis = db.query(AnalysisHistory).filter(
            AnalysisHistory.id == email_request.analysis_id,
            AnalysisHistory.user_id == current_user.id
        ).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
    else:
        # Get most recent analysis
        analysis = db.query(AnalysisHistory).filter(
            AnalysisHistory.user_id == current_user.id
        ).order_by(AnalysisHistory.created_at.desc()).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="No analysis found")

    # Use raw_results instead of results
    results_data = analysis.raw_results if analysis.raw_results else {}

    # Extract charts from results if they exist
    charts = results_data.get('results', {}).get('charts', {})
    if email_request.include_charts and not charts:
        charts = results_data.get('charts', {})

    # Send email in background
    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_analysis_results,
        email_request.to_email,
        analysis.question,
        results_data,
        charts if email_request.include_charts else {}
    )

    logger.info(
        f"Analysis email queued for {email_request.to_email} "
        f"(user: {current_user.username}, analysis_id: {analysis.id})"
    )

    return {
        "message": "Email queued for sending",
        "analysis_id": analysis.id,
        "to_email": email_request.to_email
    }


@router.post("/test-email")
@limiter.limit("3/minute")
async def test_email(
    request: Request,
    email_request: EmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Send a test email to verify configuration."""
    # 🔥 UPDATED: Check if SendGrid is configured
    if not os.getenv("SENDGRID_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Please add SENDGRID_API_KEY."
        )
    
    email_service = EmailService()
    
    background_tasks.add_task(
        email_service.send_analysis_results,
        email_request.to_email,
        "Test Email",
        {"insights": "This is a test email from Agentic Analyst.", "results": {}},
        {}
    )
    
    logger.info(f"Test email queued for {email_request.to_email}")
    
    return {"message": "Test email queued for sending"}


__all__ = ['router']