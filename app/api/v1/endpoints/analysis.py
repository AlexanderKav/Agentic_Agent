# app/api/v1/endpoints/analysis.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import pandas as pd
import tempfile
import os
from fastapi.responses import FileResponse

from app.api.v1.models.requests import AnalysisRequest, DataSourceType
from app.api.v1.models.responses import AnalysisResponse, FileUploadResponse, HealthResponse
from app.core.analysis import AnalysisOrchestrator
from app.core.data_source import DataSourceHandler

# ✅ Make sure this line is present
router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

orchestrator = AnalysisOrchestrator()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """
    Analyze data based on a question
    """
    try:
        results, exec_time = await orchestrator.analyze(
            question=request.question,
            source_type=request.data_source.value,
            source_config=request.source_config
        )
        
        return AnalysisResponse(
            success=results.get("success", False),
            insights=results.get("insights", ""),
            raw_insights=results.get("raw_insights"),
            results=results.get("results"),
            plan=results.get("plan"),
            warnings=results.get("warnings"),
            charts=results.get("charts"),
            execution_time=exec_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    question: Optional[str] = Form(None)
):
    """
    Upload a file (CSV/Excel) and optionally analyze it
    """
    temp_file_path = None
    try:
        # Validate file type
        file_type = file.filename.split('.')[-1].lower()
        if file_type not in ['csv', 'xlsx', 'xls']:
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
        # Save uploaded file
        temp_file_path = await DataSourceHandler.save_upload_file(file)
        
        # Read data
        df = DataSourceHandler.read_uploaded_file(temp_file_path, file_type)
        
        response = FileUploadResponse(
            filename=file.filename,
            rows=len(df),
            columns=list(df.columns),
            preview=df.head(5).to_dict('records')
        )
        
        # If question provided, analyze automatically
        if question:
            results, _ = await orchestrator.analyze(
                question=question,
                source_type="csv" if file_type == 'csv' else "excel",
                source_config={"path": temp_file_path}
            )
            # Add analysis_results to response if you have that field
            if hasattr(response, 'analysis_results'):
                response.analysis_results = results
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/chart/{filename}")
async def get_chart(filename: str):
    """Serve chart images"""
    # Define the charts directory
    charts_dir = os.path.join(os.getcwd(), "agents", "charts")
    file_path = os.path.join(charts_dir, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chart not found")
    
    return FileResponse(file_path, media_type="image/png", filename=filename)