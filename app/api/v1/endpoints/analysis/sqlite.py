# app/api/v1/endpoints/analysis/sqlite.py
import math
import os
import sqlite3
import tempfile
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

from .utils import MAX_FILE_SIZE, deep_clean_for_json, validate_dataframe

router = APIRouter()
orchestrator = AnalysisOrchestrator()


@router.post("/test-sqlite-connection")
async def test_sqlite_connection(
    request: Request,
    file: UploadFile = File(...),
    table: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """Test SQLite file connection and validate schema."""
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

        temp_file_path = await DataSourceHandler.save_upload_file(file)

        conn = sqlite3.connect(temp_file_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Table '{table}' not found in database")

        df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 5", conn)
        conn.close()

        if len(df) == 0:
            return {
                "success": True,
                "message": f"Connected but table '{table}' is empty",
                "rows_preview": 0,
                "columns": list(df.columns) if len(df.columns) > 0 else []
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
                detail=f"Missing required columns: {', '.join(missing)}."
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

        return {
            "success": True,
            "message": f"✅ Successfully connected! Table '{table}' has valid schema.",
            "rows_preview": len(df),
            "columns": list(df.columns),
            "preview": cleaned_preview,
            "found_columns": found_columns,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post("/sqlite-tables")
async def get_sqlite_tables(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Get list of tables from uploaded SQLite file."""
    temp_file_path = None
    try:
        temp_file_path = await DataSourceHandler.save_upload_file(file)

        conn = sqlite3.connect(temp_file_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        return {"tables": tables}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post("/upload-sqlite", response_model=FileUploadResponse)
async def upload_sqlite_file(
    request: Request,
    file: UploadFile = File(...),
    question: str | None = Form(""),
    table: str | None = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a SQLite file and analyze a specific table."""
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
        allowed_extensions = ['db', 'sqlite', 'sqlite3']
        if file_type not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_file_path = tmp_file.name

        conn = sqlite3.connect(temp_file_path)

        if not table or not table.strip():
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = cursor.fetchall()
            if not tables:
                conn.close()
                raise HTTPException(status_code=400, detail="SQLite file contains no tables")
            table = tables[0][0]

        table = table.strip()

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            available_tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Table '{table}' not found. Available tables: {', '.join(available_tables)}"
            )

        df = pd.read_sql_query(f"SELECT * FROM [{table}]" if ' ' in table else f"SELECT * FROM {table}", conn)
        conn.close()

        if len(df) == 0:
            raise HTTPException(status_code=400, detail=f"Table '{table}' is empty.")

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
            analysis_type="sqlite",
            question=question or "General Overview",
            raw_results=cleaned_results,
            data_source={
                "filename": file.filename,
                "table": table,
                "rows": len(df),
                "columns": list(df.columns)
            }
        )
        db.add(history)
        db.commit()
        db.refresh(history)

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
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass


__all__ = ['router']