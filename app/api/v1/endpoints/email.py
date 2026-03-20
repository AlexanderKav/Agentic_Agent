from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models.user import User
from app.api.v1.models.analysis import AnalysisHistory
from app.core.database import get_db
from app.services.email import EmailService

router = APIRouter(prefix="/api/v1/email", tags=["Email"])

class EmailRequest(BaseModel):
    to_email: EmailStr
    analysis_id: Optional[int] = None
    include_charts: bool = True

@router.post("/send-analysis")
async def send_analysis(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send analysis results via email"""
    
    # Get analysis
    if request.analysis_id:
        analysis = db.query(AnalysisHistory).filter(
            AnalysisHistory.id == request.analysis_id,
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
    
    # Send email in background
    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_analysis_results,
        request.to_email,
        analysis.question,
        analysis.results,
        {}  # Charts would come from storage
    )
    
    return {"message": "Email queued for sending"}