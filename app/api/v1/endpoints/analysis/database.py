# app/api/v1/endpoints/analysis/database.py
import os
import traceback
import pandas as pd
import numpy as np

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models.analysis import AnalysisHistory
from app.api.v1.models.requests import DatabaseConnectionRequest, DatabaseTestRequest
from app.api.v1.models.responses import FileUploadResponse
from app.api.v1.models.user import User
from app.core.analysis import AnalysisOrchestrator
from app.core.database import get_db
from connectors.database_connector import DatabaseConnector

from .utils import (
    convert_to_native,
    sanitize_for_json,
    validate_database_config,
    validate_dataframe,
)

router = APIRouter()


@router.post("/database", response_model=FileUploadResponse)
async def analyze_database(
    request: Request,
    db_request: DatabaseConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect to a database and analyze data."""
    orchestrator = AnalysisOrchestrator(user_id=current_user.id)

    try:
        config = db_request.connection_config
        validate_database_config(config)

        db_type = config.get('db_type')

        if db_type == 'postgresql':
            conn_string = f"postgresql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port')}/{config.get('database')}"
        elif db_type == 'mysql':
            conn_string = f"mysql+pymysql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port')}/{config.get('database')}"
        elif db_type == 'sqlite':
            original_path = config.get('database')
            if os.path.isabs(original_path):
                abs_path = os.path.normpath(original_path)
            else:
                abs_path = os.path.normpath(os.path.abspath(original_path))

            if not os.path.exists(abs_path):
                raise HTTPException(status_code=400, detail=f"SQLite database file not found: {abs_path}")
            if not os.access(abs_path, os.R_OK):
                raise HTTPException(status_code=400, detail=f"Cannot read SQLite file: {abs_path}")

            path_for_uri = abs_path.replace('\\', '/')
            conn_string = f"sqlite:///{path_for_uri}?mode=ro"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

        connector = DatabaseConnector(conn_string)

        if not connector.test_connection():
            raise HTTPException(status_code=400, detail="Could not connect to database")

        if config.get('use_query') and config.get('query'):
            df = connector.fetch_query(config['query'])
        else:
            table = config.get('table')
            if table:
                table = table.strip()
                config['table'] = table
            if not table:
                raise HTTPException(status_code=400, detail="Table name is required")
            df = connector.fetch_table(table)

        validate_dataframe(df)

        preview_data = df.head(5).to_dict('records')
        cleaned_preview = [sanitize_for_json(row) for row in preview_data]

        results, exec_time = await orchestrator.analyze_dataframe(df, db_request.question or "")

        if results is None:
            results = {}

        analysis_results = {
            "success": results.get("success", False),
            "insights": sanitize_for_json(results.get("insights", "")),
            "raw_insights": sanitize_for_json(results.get("raw_insights", {})),
            "results": sanitize_for_json(results.get("results", {})),
            "plan": sanitize_for_json(results.get("plan", {"plan": []})),
            "warnings": sanitize_for_json(results.get("warnings", [])),
            "mapping": sanitize_for_json(results.get("mapping", {})),
            "data_summary": {
                "rows": len(df),
                "columns": list(df.columns)
            },
            "execution_time": exec_time,
            "is_generic_overview": results.get("is_generic_overview", False)
        }

        data_source = {
            "db_type": db_type,
            "table": config.get('table') if not config.get('use_query') else None,
            "query": config.get('query')[:100] if config.get('use_query') and config.get('query') else None,
            "database": config.get('database'),
            "host": config.get('host') if db_type != 'sqlite' else None
        }

        cleaned_results = sanitize_for_json(analysis_results)
        cleaned_data_source = sanitize_for_json(data_source)

        history = AnalysisHistory(
            user_id=current_user.id,
            analysis_type="database",
            question=db_request.question or "General Overview",
            raw_results=cleaned_results,
            data_source=cleaned_data_source
        )
        db.add(history)
        db.commit()

        return FileUploadResponse(
            filename=f"database_{config.get('table', 'query')}",
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


@router.post("/test-connection")
async def test_database_connection(
    request: Request,
    db_request: DatabaseTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Test database connection and validate schema without running analysis."""
    try:
        # Build connection string
        conn_string = None

        if db_request.db_type == 'postgresql':
            conn_string = f"postgresql://{db_request.username}:{db_request.password}@{db_request.host}:{db_request.port}/{db_request.database}"
        elif db_request.db_type == 'mysql':
            conn_string = f"mysql+pymysql://{db_request.username}:{db_request.password}@{db_request.host}:{db_request.port}/{db_request.database}"
        elif db_request.db_type == 'sqlite':
            original_path = db_request.database
            if os.path.isabs(original_path):
                abs_path = os.path.normpath(original_path)
            else:
                abs_path = os.path.normpath(os.path.abspath(original_path))

            if not os.path.exists(abs_path):
                raise HTTPException(status_code=400, detail=f"SQLite database file not found: {abs_path}")
            if not os.access(abs_path, os.R_OK):
                raise HTTPException(status_code=400, detail=f"Cannot read SQLite file: {abs_path}")

            path_for_uri = abs_path.replace('\\', '/')
            conn_string = f"sqlite:///{path_for_uri}?mode=ro"
        else:
            raise ValueError(f"Unsupported database type: {db_request.db_type}")

        connector = DatabaseConnector(conn_string)

        if not connector.test_connection():
            raise HTTPException(status_code=400, detail="Failed to connect to database")

        table_name = db_request.table.strip() if db_request.table else None

        if table_name and not db_request.use_query:
            with connector.engine.connect() as conn:
                from sqlalchemy import text

                if db_request.db_type == 'sqlite':
                    tables_result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
                    available_tables = [row[0] for row in tables_result]

                    if not available_tables:
                        return sanitize_for_json({
                            "status": "warning",
                            "message": "Connected but no tables found.",
                            "tables_found": [],
                            "database": abs_path
                        })

                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"), {"table_name": table_name})
                    if not result.fetchone():
                        tables_list = ", ".join(available_tables) if available_tables else "no tables found"
                        raise HTTPException(status_code=400, detail=f"Table '{table_name}' not found. Available tables: {tables_list}")

                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    column_count = len(result.fetchall())
                else:
                    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = :table_name"), {"table_name": table_name})
                    column_count = result.scalar()
                    column_count = convert_to_native(column_count)

                max_columns = 1000
                if column_count > max_columns:
                    raise HTTPException(status_code=400, detail=f"Table has {column_count} columns. Maximum allowed is {max_columns}.")

                if db_request.db_type == 'postgresql':
                    quoted_table = f'"{table_name}"'
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                else:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = convert_to_native(result.scalar())

                max_rows = 100000
                if row_count > max_rows:
                    raise HTTPException(status_code=400, detail=f"Table has {row_count:,} rows. Maximum allowed is {max_rows:,}.")

                if db_request.db_type == 'postgresql':
                    quoted_table = f'"{table_name}"'
                    df = connector.fetch_query(f"SELECT * FROM {quoted_table} LIMIT 5")
                else:
                    df = connector.fetch_query(f"SELECT * FROM {table_name} LIMIT 5")

                if len(df) == 0:
                    return sanitize_for_json({
                        "status": "success",
                        "message": f"Connected but table '{table_name}' is empty",
                        "rows_preview": 0,
                        "columns": []
                    })

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
                    raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}.")

                date_col = found_columns['date']
                pd.to_datetime(df[date_col], errors='raise')

                revenue_col = found_columns['revenue']
                pd.to_numeric(df[revenue_col], errors='raise')

                # ✅ FIX 1: Clean the dataframe before converting
                # Replace any infinity values with NaN
                df = df.replace([np.inf, -np.inf], np.nan)
                
                # Convert datetime columns to string to avoid serialization issues
                for col in df.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

                preview_data = df.head(3).to_dict('records')
                # ✅ FIX 2: Use sanitize_for_json instead of convert_to_native
                cleaned_preview = [sanitize_for_json(row) for row in preview_data]

                # ✅ FIX 3: Convert all numeric values to native Python types
                response_data = {
                    "status": "success",
                    "message": f"✅ Successfully connected! Table '{table_name}' has valid schema.",
                    "rows_preview": int(len(df)),  # Convert to int
                    "columns": list(df.columns),   # Already strings
                    "preview": cleaned_preview,
                    "found_columns": sanitize_for_json(found_columns),  # Sanitize dict
                    "size_info": {
                        "columns": int(column_count) if column_count else 0,
                        "rows": int(row_count) if row_count else 0
                    }
                }
                
                # ✅ FIX 4: Sanitize the entire response
                return sanitize_for_json(response_data)

        elif db_request.use_query and db_request.query:
            df = connector.fetch_query(f"{db_request.query} LIMIT 5")
            
            # ✅ FIX 5: Clean the dataframe before converting
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # Convert datetime columns to string
            for col in df.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            preview_data = df.head(3).to_dict('records')
            # ✅ FIX 6: Use sanitize_for_json instead of convert_to_native
            cleaned_preview = [sanitize_for_json(row) for row in preview_data]

            response_data = {
                "status": "success",
                "message": f"✅ Query executed successfully. Found {len(df)} rows.",
                "rows_preview": int(len(df)),
                "columns": list(df.columns),
                "preview": cleaned_preview
            }
            
            # ✅ FIX 7: Sanitize the entire response
            return sanitize_for_json(response_data)

        # ✅ FIX 8: Sanitize simple response
        return sanitize_for_json({
            "status": "success",
            "message": "✅ Successfully connected to database"
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ['router']