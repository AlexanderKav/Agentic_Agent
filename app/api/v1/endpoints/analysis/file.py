# app/api/v1/endpoints/analysis/file.py
import math
import os
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models.analysis import AnalysisHistory
from app.api.v1.models.responses import FileUploadResponse
from app.api.v1.models.user import User
from app.core.analysis import AnalysisOrchestrator
from app.core.data_source import DataSourceHandler
from app.core.database import get_db

from .utils import (
    MAX_FILE_SIZE,
    deep_clean_for_json,
    sanitize_for_json,
    validate_dataframe,
)

router = APIRouter()
orchestrator = AnalysisOrchestrator()


@router.post("/validate-schema")
async def validate_file_schema(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Validate file schema without running full analysis."""
    temp_file_path = None
    try:
        print(f"\n{'='*60}")
        print(f"🔍 VALIDATING FILE: {file.filename}")
        print(f"User: {current_user.username}")
        print(f"📏 File size: {file.size} bytes")
        print(f"📁 Content type: {file.content_type}")
        print(f"{'='*60}")

        file_type = file.filename.split('.')[-1].lower()
        allowed_extensions = ['csv', 'xlsx', 'xls']

        if file_type not in allowed_extensions:
            return {
                "valid": False,
                "message": f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            }

        temp_file_path = await DataSourceHandler.save_upload_file(file)

        if file_type == 'csv':
            df = pd.read_csv(temp_file_path, nrows=5)
        else:
            if file_type == 'xlsx':
                df = pd.read_excel(temp_file_path, nrows=5, engine='openpyxl')
            else:
                df = pd.read_excel(temp_file_path, nrows=5, engine='xlrd')

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
            return {
                "valid": False,
                "message": f"Missing required columns: {', '.join(missing)}. Your file must contain 'date' and 'revenue' columns.",
                "found_columns": list(df.columns)
            }

        date_col = found_columns['date']
        try:
            parsed_dates = pd.to_datetime(df[date_col], errors='coerce')
            invalid_dates = parsed_dates.isna().sum()
            if invalid_dates > 0:
                return {
                    "valid": False,
                    "message": f"The '{date_col}' column contains {invalid_dates} invalid date format(s)."
                }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Could not parse dates in column '{date_col}'. Error: {str(e)}"
            }

        revenue_col = found_columns['revenue']
        try:
            numeric_revenue = pd.to_numeric(df[revenue_col], errors='coerce')
            invalid_revenue = numeric_revenue.isna().sum()
            if invalid_revenue > 0:
                return {
                    "valid": False,
                    "message": f"The '{revenue_col}' column contains {invalid_revenue} non-numeric value(s)."
                }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Could not parse revenue in column '{revenue_col}'. Error: {str(e)}"
            }

        return {
            "valid": True,
            "message": "Schema validation passed",
            "columns": list(df.columns),
            "found_columns": found_columns
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "valid": False,
            "message": f"Validation error: {str(e)}"
        }
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    question: str | None = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a file (CSV/Excel) and analyze it."""
    orchestrator = AnalysisOrchestrator(user_id=current_user.id)
    temp_file_path = None

    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        file_type = file.filename.split('.')[-1].lower()
        allowed_extensions = ['csv', 'xlsx', 'xls']
        if file_type not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )

        print(f"📁 File upload from user {current_user.username}: {file.filename}")

        temp_file_path = await DataSourceHandler.save_upload_file(file)

        if file_type == 'csv':
            df = pd.read_csv(temp_file_path)
        elif file_type in ['xlsx', 'xls']:
            if file_type == 'xlsx':
                df = pd.read_excel(temp_file_path, engine='openpyxl')
            else:
                df = pd.read_excel(temp_file_path, engine='xlrd')
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

        validate_dataframe(df)

        preview_data = df.head(5).to_dict('records')
        cleaned_preview = [sanitize_for_json(row) for row in preview_data]

        results, exec_time = await orchestrator.analyze_dataframe(df, question or "")

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
            "data_summary": results.get("data_summary", {
                "rows": len(df),
                "columns": list(df.columns)
            }),
            "execution_time": exec_time,
            "is_generic_overview": results.get("is_generic_overview", False)
        }

        cleaned_results = deep_clean_for_json(analysis_results)

        history = AnalysisHistory(
            user_id=current_user.id,
            analysis_type="file",
            question=question or "General Overview",
            raw_results=cleaned_results,
            data_source={
                "filename": file.filename,
                "file_type": file_type,
                "rows": len(df),
                "columns": list(df.columns)
            }
        )
        db.add(history)
        db.commit()

        return FileUploadResponse(
            filename=file.filename,
            rows=len(df),
            columns=list(df.columns),
            preview=cleaned_preview,
            analysis_results=cleaned_results
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


__all__ = ['router']