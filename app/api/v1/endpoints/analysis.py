from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional
import pandas as pd
import tempfile
import os
import time
from fastapi.responses import FileResponse

from app.api.v1.models.requests import AnalysisRequest, DatabaseConnectionRequest, DatabaseTestRequest
from app.api.v1.models.responses import AnalysisResponse, FileUploadResponse, HealthResponse
from app.core.analysis import AnalysisOrchestrator
from app.core.data_source import DataSourceHandler
from connectors.database_connector import DatabaseConnector
from pydantic import BaseModel
from connectors.google_sheets import GoogleSheetsConnector


router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
orchestrator = AnalysisOrchestrator()

@router.post("/database", response_model=FileUploadResponse)
async def analyze_database(request: DatabaseConnectionRequest):
    """
    Connect to a database and analyze data
    """
    try:
        config = request.connection_config
        print(f"📊 Database analysis requested for: {config.get('db_type')}")
        
        # Build connection string based on database type
        db_type = config.get('db_type')
        
        if db_type == 'postgresql':
            conn_string = f"postgresql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port')}/{config.get('database')}"
        elif db_type == 'mysql':
            conn_string = f"mysql+pymysql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port')}/{config.get('database')}"
        elif db_type == 'sqlite':
            conn_string = f"sqlite:///{config.get('database')}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        print(f"🔌 Connecting to database...")
        
        # Connect and fetch data
        connector = DatabaseConnector(conn_string)
        
        if not connector.test_connection():
            raise HTTPException(status_code=400, detail="Could not connect to database")
        
        # Use either table or custom query
        if config.get('use_query') and config.get('query'):
            print(f"📝 Executing custom query")
            df = connector.fetch_query(config['query'])
        else:
            table = config.get('table')
            if not table:
                raise HTTPException(status_code=400, detail="Table name is required")
            print(f"📋 Fetching table: {table}")
            df = connector.fetch_table(table)
        
        print(f"✅ Loaded {len(df)} rows from database")
        
        # Create preview (5 rows)
        preview = df.head(5).to_dict('records')
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, request.question)
        
        # DEBUG: Print the structure of results
        print("\n" + "="*60)
        print("🗄️ DATABASE RESULTS STRUCTURE")
        print("="*60)
        print(f"Results keys: {results.keys()}")
        
        # IMPORTANT: Don't flatten the insights - preserve the full structure
        # The frontend expects the full insights object, not just a string
        insights_data = results.get("insights", {})
        raw_insights_data = results.get("raw_insights", {})
        
        print(f"Insights type: {type(insights_data)}")
        print(f"Insights preview: {str(insights_data)[:200]}...")
        print("="*60 + "\n")
        
        # Create the analysis_results structure - PRESERVE the original structure
        analysis_results = {
            "success": results.get("success", False),
            "insights": insights_data,  # Keep as original - don't convert to string!
            "raw_insights": raw_insights_data,
            "results": results.get("results", {}),
            "plan": results.get("plan", {"plan": []}),
            "warnings": results.get("warnings", []),
            "mapping": results.get("mapping", {}),
            "data_summary": results.get("data_summary", {
                "rows": len(df),
                "columns": list(df.columns)
            }),
            "execution_time": exec_time,
            "is_generic_overview": results.get("is_generic_overview", False)
        }
        
        return FileUploadResponse(
            filename="database_query",
            rows=len(df),
            columns=list(df.columns),
            preview=preview,
            analysis_results=analysis_results
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-connection")
async def test_database_connection(request: DatabaseTestRequest):
    """
    Test database connection without running analysis
    """
    try:
        # Build connection string
        if request.db_type == 'postgresql':
            conn_string = f"postgresql://{request.username}:{request.password}@{request.host}:{request.port}/{request.database}"
        elif request.db_type == 'mysql':
            conn_string = f"mysql+pymysql://{request.username}:{request.password}@{request.host}:{request.port}/{request.database}"
        elif request.db_type == 'sqlite':
            conn_string = f"sqlite:///{request.database}"
        else:
            raise ValueError(f"Unsupported database type: {request.db_type}")
        
        connector = DatabaseConnector(conn_string)
        
        if connector.test_connection():
            return {"status": "success", "message": "Successfully connected to database"}
        else:
            raise HTTPException(status_code=400, detail="Failed to connect to database")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    question: Optional[str] = Form("")
):
    """Upload a file (CSV/Excel) and analyze it"""
    temp_file_path = None
    try:
        file_type = file.filename.split('.')[-1].lower()
        if file_type not in ['csv', 'xlsx', 'xls']:
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
        temp_file_path = await DataSourceHandler.save_upload_file(file)
        df = DataSourceHandler.read_uploaded_file(temp_file_path, file_type)
        
        response = FileUploadResponse(
            filename=file.filename,
            rows=len(df),
            columns=list(df.columns),
            preview=df.head(5).to_dict('records')
        )
        
        results, exec_time = await orchestrator.analyze_dataframe(df, question or "")
        response.analysis_results = results
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.get("/chart/{filename}")
async def get_chart(filename: str, key: int = 0):
    """Serve chart images with cache busting"""
    charts_dir = os.path.join(os.getcwd(), "agents", "charts")
    file_path = os.path.join(charts_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chart not found")
    
    return FileResponse(file_path, media_type="image/png", filename=filename)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

class GoogleSheetsRequest(BaseModel):
    question: str
    sheet_config: dict

class GoogleSheetsTestRequest(BaseModel):
    sheet_id: str
    sheet_range: Optional[str] = "A1:Z1000"

import math
import numpy as np

def clean_for_json(obj):
    """Recursively clean data for JSON serialization"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None  # Convert NaN/Inf to null
        return obj
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    return obj

@router.post("/google-sheets", response_model=FileUploadResponse)
async def analyze_google_sheets(request: GoogleSheetsRequest):
    """
    Connect to Google Sheets and analyze data
    """
    try:
        config = request.sheet_config
        print(f"📊 Google Sheets analysis requested for: {config.get('sheet_id')}")
        
        # Get credentials path from environment
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise HTTPException(status_code=500, detail="Google credentials not configured")
        
        # Connect to Google Sheets
        sheet_id = config.get('sheet_id')
        sheet_range = config.get('sheet_range', 'A1:Z1000')
        
        connector = GoogleSheetsConnector(sheet_id, sheet_range)
        df = connector.fetch_sheet()
        
        print(f"✅ Loaded {len(df)} rows from Google Sheets")
        
        # Create preview
        preview = df.head(5).to_dict('records')
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, request.question)
        
        return FileUploadResponse(
            filename=f"google_sheet_{sheet_id[:8]}",
            rows=len(df),
            columns=list(df.columns),
            preview=preview,
            analysis_results=results
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-google-sheets")
async def test_google_sheets_connection(request: GoogleSheetsTestRequest):
    """
    Test Google Sheets connection without running analysis
    """
    try:
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise HTTPException(status_code=500, detail="Google credentials not configured")
        
        connector = GoogleSheetsConnector(request.sheet_id, request.sheet_range)
        df = connector.fetch_sheet()
        
        if len(df) > 0:
            # Convert DataFrame to dict and clean NaN values
            preview_data = df.head(3).to_dict('records')
            cleaned_preview = clean_for_json(preview_data)
            cleaned_columns = clean_for_json(list(df.columns))
            
            return {
                "status": "success", 
                "message": f"Successfully connected! Found {len(df)} rows",
                "columns": cleaned_columns,
                "preview": cleaned_preview
            }
        else:
            return {"status": "success", "message": "Connected but sheet is empty"}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
