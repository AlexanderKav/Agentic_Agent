from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint"""
    success: bool
    insights: str
    raw_insights: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    charts: Optional[Dict[str, str]] = None
    execution_time: Optional[float] = None


class FileUploadResponse(BaseModel):
    """Response after file upload"""
    filename: str
    rows: int
    columns: List[str]
    preview: List[Dict[str, Any]]
    analysis_results: Optional[Dict[str, Any]] = Field(default_factory=dict)
    


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str

class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str
    error_code: Optional[str] = None