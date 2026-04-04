# app/api/v1/endpoints/analysis/google_sheets.py
import math
import os
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models.analysis import AnalysisHistory
from app.api.v1.models.requests import GoogleSheetsRequest, GoogleSheetsTestRequest
from app.api.v1.models.responses import FileUploadResponse
from app.api.v1.models.user import User
from app.core.analysis import AnalysisOrchestrator
from app.core.database import get_db
from connectors.google_sheets import GoogleSheetsConnector

from .utils import validate_dataframe

router = APIRouter()


def deep_clean_for_db(obj):
    """Recursively clean objects for database JSON serialization."""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            str_key = str(k) if not isinstance(k, (str, int, float, bool)) else k
            if isinstance(str_key, int):
                str_key = str(str_key)
            cleaned[str_key] = deep_clean_for_db(v)
        return cleaned
    elif isinstance(obj, (list, tuple, set)):
        return [deep_clean_for_db(item) for item in obj]
    elif isinstance(obj, pd.Series):
        return deep_clean_for_db(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return deep_clean_for_db(obj.to_dict('records'))
    else:
        try:
            return str(obj)
        except Exception:
            return None


@router.post("/google-sheets", response_model=FileUploadResponse)
async def analyze_google_sheets(
    request: Request,
    sheets_request: GoogleSheetsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect to Google Sheets and analyze data."""
    orchestrator = AnalysisOrchestrator(user_id=current_user.id)

    try:
        config = sheets_request.sheet_config

        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise HTTPException(status_code=500, detail="Google credentials not configured")

        sheet_id = config.get('sheet_id')
        sheet_range = config.get('sheet_range', 'A1:Z1000')

        connector = GoogleSheetsConnector(sheet_id, sheet_range)
        df = connector.fetch_sheet()

        validate_dataframe(df)

        preview_data = df.head(5).to_dict('records')
        cleaned_preview = []
        for row in preview_data:
            cleaned_row = {}
            for key, value in row.items():
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    cleaned_row[key] = None
                elif isinstance(value, pd.Timestamp):
                    cleaned_row[key] = value.isoformat()
                else:
                    cleaned_row[key] = value
            cleaned_preview.append(cleaned_row)

        results, exec_time = await orchestrator.analyze_dataframe(df, sheets_request.question or "")

        if results is None:
            results = {}

        analysis_results = {
            "success": results.get("success", False),
            "insights": results.get("insights", ""),
            "raw_insights": results.get("raw_insights", {}),
            "results": results.get("results", {}),
            "plan": results.get("plan", {"plan": []}),
            "warnings": results.get("warnings", []),
            "mapping": results.get("mapping", {}),
            "data_summary": {
                "rows": len(df),
                "columns": list(df.columns)
            },
            "execution_time": exec_time,
            "is_generic_overview": results.get("is_generic_overview", False)
        }

        cleaned_results = deep_clean_for_db(analysis_results)

        data_source = {
            "sheet_id": sheet_id[:8] + "...",
            "sheet_range": sheet_range,
            "rows": len(df),
            "columns": list(df.columns)
        }
        cleaned_data_source = deep_clean_for_db(data_source)

        history = AnalysisHistory(
            user_id=current_user.id,
            analysis_type="google_sheets",
            question=sheets_request.question or "General Overview",
            raw_results=cleaned_results,
            data_source=cleaned_data_source
        )
        db.add(history)
        db.commit()

        final_results = deep_clean_for_db(analysis_results)

        return FileUploadResponse(
            filename=f"google_sheet_{sheet_id[:8]}",
            rows=len(df),
            columns=list(df.columns),
            preview=cleaned_preview,
            analysis_results=final_results
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-google-sheets")
async def test_google_sheets_connection(
    request: Request,
    sheets_request: GoogleSheetsTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Test Google Sheets connection and validate schema."""
    try:
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise HTTPException(status_code=500, detail="Google credentials not configured")

        connector = GoogleSheetsConnector(sheets_request.sheet_id, sheets_request.sheet_range)
        df = connector.fetch_sheet()

        if len(df) == 0:
            return {
                "status": "success",
                "message": "Connected but sheet is empty",
                "permission_status": connector.get_permission_status(),
                "permission_warning": connector.get_permission_warning()
            }

        required_columns = ['date', 'revenue']
        df_columns_lower = [col.lower() for col in df.columns]

        missing = []
        found_columns = {}

        for req_col in required_columns:
            if req_col in df_columns_lower:
                original_col = df.columns[df_columns_lower.index(req_col)]
                found_columns[req_col] = original_col
            else:
                missing.append(req_col)

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing)}. Your sheet must contain 'date' and 'revenue' columns."
            )

        date_col = found_columns['date']
        pd.to_datetime(df[date_col], errors='raise')

        revenue_col = found_columns['revenue']
        pd.to_numeric(df[revenue_col], errors='raise')

        preview_data = df.head(3).to_dict('records')
        cleaned_preview = []
        for row in preview_data:
            cleaned_row = {}
            for key, value in row.items():
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    cleaned_row[key] = None
                elif isinstance(value, pd.Timestamp):
                    cleaned_row[key] = value.isoformat()
                else:
                    cleaned_row[key] = value
            cleaned_preview.append(cleaned_row)

        response = {
            "status": "success",
            "message": f"Successfully connected! Found {len(df)} rows with valid schema.",
            "columns": list(df.columns),
            "preview": cleaned_preview,
            "found_columns": found_columns,
            "permission_status": connector.get_permission_status()
        }

        permission_warning = connector.get_permission_warning()
        if permission_warning:
            response["warning"] = permission_warning

        return response

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ['router']