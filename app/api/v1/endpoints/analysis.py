# app/api/v1/endpoints/analysis.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Request, Depends
from typing import Optional
import pandas as pd
import tempfile
import os
import time
import re
import math
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from datetime import datetime

# Rate limiting imports
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1.models.requests import AnalysisRequest, DatabaseConnectionRequest, DatabaseTestRequest, GoogleSheetsRequest, GoogleSheetsTestRequest
from app.api.v1.models.responses import AnalysisResponse, FileUploadResponse, HealthResponse
from app.core.analysis import AnalysisOrchestrator
from app.core.data_source import DataSourceHandler
from app.core.database import get_db
from app.api.v1.models.analysis import AnalysisHistory, AnalysisMetric, AnalysisInsight
from app.api.v1.models.user import User
from app.api.v1.endpoints.auth import get_current_user
from connectors.database_connector import DatabaseConnector
from connectors.google_sheets import GoogleSheetsConnector
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
orchestrator = AnalysisOrchestrator()

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# ==================== CONSTANTS & CONFIGURATION ====================
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROWS = 100000  # Maximum rows to process
MAX_QUERY_LENGTH = 2000  # Maximum SQL query length

# SECURITY: Host validation - empty list means allow all hosts (for production SaaS)
# In production, users connect to their own databases, so we don't restrict hostnames.
# Security is handled by authentication, rate limiting, and connection validation.
# For private/internal deployments, you can set a whitelist via environment variable.
ALLOWED_DB_HOSTS = []  # Empty = allow any host

# Alternative: Read from environment for private deployments
# import os
# ALLOWED_DB_HOSTS = os.getenv("ALLOWED_DB_HOSTS", "").split(",") if os.getenv("ALLOWED_DB_HOSTS") else []

DANGEROUS_SQL_KEYWORDS = [
    'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 
    'INSERT', 'UPDATE', 'MERGE', 'REPLACE', 'GRANT',
    'REVOKE', 'EXEC', 'EXECUTE'
]

# ==================== HELPER FUNCTIONS ====================

def clean_for_json(obj):
    """Recursively clean data for JSON serialization"""
    if obj is None:
        return None
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
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
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, pd.Series):
        return clean_for_json(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return clean_for_json(obj.to_dict('records'))
    return obj

def sanitize_for_json(obj):
    """Sanitize objects for JSON serialization, handling NaN, Inf, and numpy types"""
    if obj is None:
        return None
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.bool_)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, np.datetime64, datetime)):
        return obj.isoformat()  # Convert Timestamp to ISO format string
    if isinstance(obj, dict):
        # Convert any non-string keys to strings
        cleaned = {}
        for k, v in obj.items():
            str_key = str(k) if not isinstance(k, (str, int, float, bool)) else k
            cleaned[str_key] = sanitize_for_json(v)
        return cleaned
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]
    if isinstance(obj, pd.Series):
        return sanitize_for_json(obj.to_dict())
    if isinstance(obj, pd.DataFrame):
        return sanitize_for_json(obj.to_dict('records'))
    return obj

# ==================== VALIDATION FUNCTIONS ====================

def validate_database_config(config: dict):
    """Validate database configuration for security"""
    
    db_type = config.get('db_type', 'postgresql')
    
    # 1. Validate table name (if provided)
    table_name = config.get('table', '')
    if table_name:
        # Strip whitespace
        table_name = table_name.strip()
        config['table'] = table_name
        
        if db_type == 'postgresql':
            # PostgreSQL: letters, numbers, underscores (can start with numbers)
            if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid PostgreSQL table name '{table_name}'. Use only letters, numbers, and underscores."
                )
        elif db_type == 'mysql':
            # MySQL: same as PostgreSQL but also allows $
            if not re.match(r'^[a-zA-Z0-9_$]+$', table_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid MySQL table name '{table_name}'. Use only letters, numbers, underscores, and $."
                )
        elif db_type == 'sqlite':
            # SQLite: most permissive, but we'll keep it safe
            if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid SQLite table name '{table_name}'. Use only letters, numbers, and underscores for safety."
                )
        
        # Optional: Add length check (PostgreSQL limit is 63 bytes)
        if len(table_name) > 63:
            raise HTTPException(
                status_code=400,
                detail=f"Table name too long ({len(table_name)} chars). Maximum is 63 characters."
            )
    
    # 2. Validate and sanitize query (if provided)
    query = config.get('query', '')
    if query and len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long. Maximum {MAX_QUERY_LENGTH} characters"
        )
    
    # 3. Check for dangerous SQL keywords
    if query:
        query_upper = query.upper()
        for keyword in DANGEROUS_SQL_KEYWORDS:
            if keyword in query_upper:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dangerous SQL keyword '{keyword}' not allowed. Only SELECT queries are permitted."
                )
    
    # 4. Validate host format (prevent injection, but don't restrict allowed hosts)
    host = config.get('host', '')
    if host:
        # Basic format validation - only allow valid hostname characters
        # This prevents injection but doesn't restrict which hosts users can connect to
        if not re.match(r'^[a-zA-Z0-9\.\-_]+$', host):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid host format: '{host}'. Hostnames can only contain letters, numbers, dots, hyphens, and underscores."
            )
        
        # Optional: Block private IP ranges in production (add this if you want)
        # if os.getenv("ENVIRONMENT") == "production":
        #     try:
        #         import ipaddress
        #         ip = ipaddress.ip_address(host)
        #         if ip.is_private:
        #             raise HTTPException(
        #                 status_code=400,
        #                 detail="Cannot connect to private/internal IP addresses for security reasons. Use a public hostname instead."
        #             )
        #     except ValueError:
        #         # Not an IP, assume it's a public hostname
        #         pass
    
    # 5. Validate port range
    port = config.get('port', '')
    if port:
        try:
            port_num = int(port)
            if port_num < 1024 or port_num > 65535:
                raise HTTPException(
                    status_code=400,
                    detail="Port must be between 1024 and 65535"
                )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid port number")
    
    return True


def validate_dataframe(df: pd.DataFrame):
    """Validate dataframe for security and acceptability"""
    
    # Check row limit
    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many rows. Maximum is {MAX_ROWS}"
        )
    
    # Check for obviously malicious data in string columns
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check for extremely long strings (potential injection)
            max_len = df[col].astype(str).str.len().max()
            if max_len > 10000:  # 10KB per cell max
                raise HTTPException(
                    status_code=400,
                    detail=f"Column '{col}' contains suspiciously long strings"
                )
    
    return True

# ==================== DATABASE ENDPOINTS ====================

@router.post("/database", response_model=FileUploadResponse)
@limiter.limit("20/minute")
async def analyze_database(
    request: Request,
    db_request: DatabaseConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect to a database and analyze data
    """
    try:
        config = db_request.connection_config
        
        # 🔐 VALIDATE THE CONFIGURATION
        validate_database_config(config)
        
        print(f"\n{'='*60}")
        print(f"📊 DATABASE ANALYSIS REQUESTED")
        print(f"{'='*60}")
        print(f"Database type: {config.get('db_type')}")
        print(f"Question: {db_request.question[:50] if db_request.question else 'No question (overview)'}")
        print(f"User: {current_user.username} (ID: {current_user.id})")
        print(f"{'='*60}\n")
        
        # Build connection string based on database type
        db_type = config.get('db_type')
        
        if db_type == 'postgresql':
            conn_string = f"postgresql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port')}/{config.get('database')}"
        elif db_type == 'mysql':
            conn_string = f"mysql+pymysql://{config.get('username')}:{config.get('password')}@{config.get('host')}:{config.get('port')}/{config.get('database')}"
        elif db_type == 'sqlite':
            import os
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
            if table:
                table = table.strip()
                config['table'] = table
            if not table:
                raise HTTPException(status_code=400, detail="Table name is required")
            print(f"📋 Fetching table: '{table}'")
            df = connector.fetch_table(table)
        
        # 🔐 VALIDATE THE DATAFRAME
        validate_dataframe(df)
        
        print(f"✅ Loaded {len(df)} rows from database")
        
        # Create preview (5 rows) with sanitized values
        preview_data = df.head(5).to_dict('records')
        cleaned_preview = [sanitize_for_json(row) for row in preview_data]
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, db_request.question or "")
        
        # Ensure results is a dictionary
        if results is None:
            results = {}
        
        # Create the analysis_results structure with sanitized values
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
        
        # Create data_source dictionary
        data_source = {
            "db_type": db_type,
            "table": config.get('table') if not config.get('use_query') else None,
            "query": config.get('query')[:100] if config.get('use_query') and config.get('query') else None,
            "database": config.get('database'),
            "host": config.get('host') if db_type != 'sqlite' else None
        }
        
        # Sanitize everything
        cleaned_results = sanitize_for_json(analysis_results)
        cleaned_data_source = sanitize_for_json(data_source)
        
        # Save to history
        history = AnalysisHistory(
            user_id=current_user.id,
            analysis_type="database",
            question=db_request.question or "General Overview",
            raw_results=cleaned_results,
            data_source=cleaned_data_source
        )
        db.add(history)
        db.commit()
        
        print(f"💾 Analysis saved to history (ID: {history.id})")
        
        # Return properly formatted response
        return FileUploadResponse(
            filename=f"database_{table if 'table' in locals() else 'query'}",
            rows=len(df),
            columns=list(df.columns),
            preview=cleaned_preview,
            analysis_results=cleaned_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-connection")
@limiter.limit("30/minute")
async def test_database_connection(
    request: Request,
    db_request: DatabaseTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Test database connection and validate schema without running analysis
    """
    # Helper function to convert numpy/pandas types to Python native types
    def convert_to_native(obj):
        """Convert numpy/pandas types to Python native types for JSON serialization"""
        import numpy as np
        import pandas as pd
        
        if obj is None:
            return None
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        if isinstance(obj, (np.bool_)):
            return bool(obj)
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
        if isinstance(obj, dict):
            return {convert_to_native(k): convert_to_native(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert_to_native(item) for item in obj]
        return obj
    
    try:
        print(f"\n{'='*60}")
        print(f"🔍 TEST CONNECTION REQUEST RECEIVED")
        print(f"{'='*60}")
        print(f"Database type: {db_request.db_type}")
        print(f"Database: {db_request.database}")
        print(f"Table: {db_request.table}")
        print(f"Host: {db_request.host}")
        print(f"Port: {db_request.port}")
        print(f"Username: {db_request.username}")
        print(f"User: {current_user.username} (ID: {current_user.id})")
        print(f"Use query: {db_request.use_query}")
        if db_request.use_query:
            print(f"Query: {db_request.query[:100]}...")
        print(f"{'='*60}\n")
        
        # Strip table name
        table_name = db_request.table.strip() if db_request.table else None
        
        # Build connection string based on database type
        conn_string = None
        
        if db_request.db_type == 'postgresql':
            conn_string = f"postgresql://{db_request.username}:{db_request.password}@{db_request.host}:{db_request.port}/{db_request.database}"
            
        elif db_request.db_type == 'mysql':
            # Build MySQL connection string without SSL parameter
            conn_string = f"mysql+pymysql://{db_request.username}:{db_request.password}@{db_request.host}:{db_request.port}/{db_request.database}"
            print(f"🔌 MySQL connection string (password masked): {conn_string.replace(db_request.password, '****')}")
                    
        elif db_request.db_type == 'sqlite':
            import os
            original_path = db_request.database
            print(f"📁 Original path from user: {original_path}")
            
            # Get absolute path and normalize
            if os.path.isabs(original_path):
                abs_path = os.path.normpath(original_path)
            else:
                abs_path = os.path.normpath(os.path.abspath(original_path))
            
            print(f"📁 Absolute path: {abs_path}")
            
            # Check if file exists
            if not os.path.exists(abs_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"SQLite database file not found: {abs_path}"
                )
            
            # Check file permissions
            if not os.access(abs_path, os.R_OK):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot read SQLite file: {abs_path}"
                )
            
            print(f"✅ SQLite file exists: {abs_path}")
            print(f"📏 File size: {os.path.getsize(abs_path)} bytes")
            
            # Convert backslashes to forward slashes
            path_for_uri = abs_path.replace('\\', '/')
            
            # Use read-only mode
            conn_string = f"sqlite:///{path_for_uri}?mode=ro"
            print(f"🔌 Connection string: {conn_string}")
        
        else:
            raise ValueError(f"Unsupported database type: {db_request.db_type}")
        
        # Create connector and test connection
        connector = DatabaseConnector(conn_string)
        
        if not connector.test_connection():
            print("❌ Failed to connect to database")
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        print("✅ Successfully connected to database")
        
        # If table name provided, validate schema
        if table_name and not db_request.use_query:
            print(f"📋 Validating table: '{table_name}'")
            
            with connector.engine.connect() as conn:
                # For SQLite, first check if any tables exist
                if db_request.db_type == 'sqlite':
                    # Check if there are any tables at all
                    tables_result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                    ))
                    available_tables = [row[0] for row in tables_result]
                    
                    if not available_tables:
                        return {
                            "status": "warning",
                            "message": f"Connected to SQLite database, but no tables found. Please ensure your database contains tables.",
                            "tables_found": [],
                            "database": abs_path
                        }
                    
                    # Check if specific table exists
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
                    ), {"table_name": table_name})
                    table_exists = result.fetchone()
                    
                    if not table_exists:
                        tables_list = ", ".join(available_tables) if available_tables else "no tables found"
                        raise HTTPException(
                            status_code=400,
                            detail=f"Table '{table_name}' not found. Available tables: {tables_list}"
                        )
                    
                    # Get column count
                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    columns = result.fetchall()
                    column_count = len(columns)
                    print(f"📊 SQLite table has {column_count} columns")
                    
                elif db_request.db_type == 'postgresql':
                    # PostgreSQL validation
                    result = conn.execute(text("""
                        SELECT COUNT(*) 
                        FROM information_schema.columns 
                        WHERE table_name = :table_name
                    """), {"table_name": table_name})
                    column_count = result.scalar()
                    column_count = convert_to_native(column_count)
                    print(f"📊 PostgreSQL table has {column_count} columns")
                    
                elif db_request.db_type == 'mysql':
                    # MySQL validation
                    result = conn.execute(text("""
                        SELECT COUNT(*) 
                        FROM information_schema.columns 
                        WHERE table_name = :table_name
                    """), {"table_name": table_name})
                    column_count = result.scalar()
                    column_count = convert_to_native(column_count)
                    print(f"📊 MySQL table has {column_count} columns")
                    
                else:
                    column_count = 0
                
                # Define limits
                MAX_COLUMNS = 1000
                if column_count > MAX_COLUMNS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Table has {column_count} columns. Maximum allowed is {MAX_COLUMNS}. Your table is too wide."
                    )
                
                # Get row count - QUOTE the table name for PostgreSQL
                try:
                    if db_request.db_type == 'postgresql':
                        quoted_table = f'"{table_name}"'
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                    else:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = result.scalar()
                    row_count = convert_to_native(row_count)
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not query table '{table_name}'. Error: {str(e)}"
                    )
                
                MAX_ROWS = 100000
                if row_count > MAX_ROWS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Table has {row_count:,} rows. Maximum allowed is {MAX_ROWS:,}."
                    )
                
                print(f"✅ Size validation passed: {column_count} columns, {row_count} rows")
                
                # Read sample for schema validation - QUOTE for PostgreSQL
                try:
                    if db_request.db_type == 'postgresql':
                        quoted_table = f'"{table_name}"'
                        df = connector.fetch_query(f"SELECT * FROM {quoted_table} LIMIT 5")
                    else:
                        df = connector.fetch_query(f"SELECT * FROM {table_name} LIMIT 5")
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not read data from table '{table_name}'. Error: {str(e)}"
                    )
                
                if len(df) == 0:
                    return {
                        "status": "success", 
                        "message": f"Connected to database but table '{table_name}' is empty",
                        "rows_preview": 0,
                        "columns": []
                    }
                
                # Validate schema
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
                        detail=f"Schema validation failed: Missing required columns: {', '.join(missing)}. Your table must contain 'date' and 'revenue' columns."
                    )
                
                # Validate date column
                date_col = found_columns['date']
                try:
                    pd.to_datetime(df[date_col], errors='raise')
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Schema validation failed: Column '{date_col}' contains invalid date formats."
                    )
                
                # Validate revenue column
                revenue_col = found_columns['revenue']
                try:
                    pd.to_numeric(df[revenue_col], errors='raise')
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Schema validation failed: Column '{revenue_col}' contains non-numeric values."
                    )
                
                # Clean preview data - convert all numpy/pandas types
                preview_data = df.head(3).to_dict('records')
                cleaned_preview = []
                for row in preview_data:
                    cleaned_row = {}
                    for key, value in row.items():
                        cleaned_row[key] = convert_to_native(value)
                    cleaned_preview.append(cleaned_row)
                
                # Convert columns and found_columns to native types
                columns_list = [convert_to_native(col) for col in df.columns]
                found_columns_clean = {k: convert_to_native(v) for k, v in found_columns.items()}
                
                return {
                    "status": "success", 
                    "message": f"✅ Successfully connected! Table '{table_name}' has valid schema.",
                    "rows_preview": sanitize_for_json(len(df)),
                    "columns": [sanitize_for_json(col) for col in df.columns],
                    "preview": [sanitize_for_json(row) for row in preview_data],
                    "found_columns": sanitize_for_json(found_columns),
                    "size_info": {
                        "columns": sanitize_for_json(column_count),
                        "rows": sanitize_for_json(row_count)
                    }
                }
        
        # If custom query provided
        elif db_request.use_query and db_request.query:
            print(f"📝 Testing custom query")
            try:
                df = connector.fetch_query(f"{db_request.query} LIMIT 5")
                
                # Clean preview data - convert all numpy/pandas types
                preview_data = df.head(3).to_dict('records')
                cleaned_preview = []
                for row in preview_data:
                    cleaned_row = {}
                    for key, value in row.items():
                        cleaned_row[key] = convert_to_native(value)
                    cleaned_preview.append(cleaned_row)
                
                return {
                    "status": "success", 
                    "message": f"✅ Query executed successfully. Found {len(df)} rows.",
                    "rows_preview": convert_to_native(len(df)),
                    "columns": [convert_to_native(col) for col in df.columns],
                    "preview": cleaned_preview
                }
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query execution failed: {str(e)}"
                )
        
        else:
            # Just connection test, no table validation
            return {
                "status": "success", 
                "message": "✅ Successfully connected to database"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FILE UPLOAD ENDPOINT ====================

@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    question: Optional[str] = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a file (CSV/Excel/SQLite) and analyze it"""
    temp_file_path = None
    try:
        # Check file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Check file extension
        file_type = file.filename.split('.')[-1].lower()
        allowed_extensions = ['csv', 'xlsx', 'xls', 'db', 'sqlite', 'sqlite3']
        if file_type not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        
        print(f"📁 File upload from user {current_user.username}: {file.filename}")
        print(f"📁 File type detected: {file_type}")
        
        # Save file temporarily
        temp_file_path = await DataSourceHandler.save_upload_file(file)
        
        # Read data based on file type
        df = None
        
        if file_type in ['db', 'sqlite', 'sqlite3']:
            # Handle SQLite files
            print("📊 Reading SQLite file...")
            import sqlite3
            
            # Connect to the SQLite file
            conn = sqlite3.connect(temp_file_path)
            
            # Get list of tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                conn.close()
                raise HTTPException(status_code=400, detail="SQLite file contains no tables")
            
            # Use the first table (or let user specify table name in the future)
            table_name = tables[0][0]
            print(f"📊 Reading table: {table_name}")
            
            # Read the table
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            
            print(f"✅ Loaded {len(df)} rows from SQLite table '{table_name}'")
            
        elif file_type == 'csv':
            # Handle CSV files
            print("📊 Reading CSV file...")
            df = pd.read_csv(temp_file_path)
            print(f"✅ Loaded {len(df)} rows from CSV")
            
        elif file_type in ['xlsx', 'xls']:
            # Handle Excel files
            print("📊 Reading Excel file...")
            # Specify engine explicitly to avoid warnings
            if file_type == 'xlsx':
                df = pd.read_excel(temp_file_path, engine='openpyxl')
            else:
                df = pd.read_excel(temp_file_path, engine='xlrd')
            print(f"✅ Loaded {len(df)} rows from Excel")
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_type}"
            )
        
        # 🔐 VALIDATE THE DATAFRAME
        validate_dataframe(df)
        
        # Create preview (5 rows) and clean NaN values
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
        
        # Create response with preview
        response = FileUploadResponse(
            filename=file.filename,
            rows=len(df),
            columns=list(df.columns),
            preview=cleaned_preview,
            analysis_results={}
        )
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, question or "")
        
        # Ensure results is a dictionary
        if results is None:
            results = {}
        
        # Create the analysis_results structure
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
        
        # DEEP CLEAN - recursively clean all Timestamp objects
        print("🧹 Deep cleaning analysis_results for JSON serialization...")
        
        def deep_clean_for_json(obj):
            """Even more aggressive cleaning for JSON serialization"""
            if obj is None:
                return None
            elif isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj) if isinstance(obj, np.floating) else int(obj)
            elif isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {str(k): deep_clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple, set)):
                return [deep_clean_for_json(item) for item in obj]
            elif isinstance(obj, pd.Series):
                return deep_clean_for_json(obj.to_dict())
            elif isinstance(obj, pd.DataFrame):
                return deep_clean_for_json(obj.to_dict('records'))
            else:
                try:
                    return str(obj)
                except:
                    return None
        
        cleaned_results = deep_clean_for_json(analysis_results)
        
        # Save to history
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
        
        print(f"💾 Analysis saved to history (ID: {history.id})")
        
        response.analysis_results = cleaned_results
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"🧹 Cleaned up temp file: {temp_file_path}")

# ==================== GOOGLE SHEETS ENDPOINTS ====================

@router.post("/google-sheets", response_model=FileUploadResponse)
@limiter.limit("20/minute")
async def analyze_google_sheets(
    request: Request,
    sheets_request: GoogleSheetsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect to Google Sheets and analyze data
    """
    try:
        config = sheets_request.sheet_config
        print(f"📊 Google Sheets analysis requested for: {config.get('sheet_id')}")
        print(f"User: {current_user.username} (ID: {current_user.id})")
        
        # Get credentials path from environment
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise HTTPException(status_code=500, detail="Google credentials not configured")
        
        # Connect to Google Sheets
        sheet_id = config.get('sheet_id')
        sheet_range = config.get('sheet_range', 'A1:Z1000')
        
        connector = GoogleSheetsConnector(sheet_id, sheet_range)
        df = connector.fetch_sheet()
        
        # 🔐 VALIDATE THE DATAFRAME
        validate_dataframe(df)
        
        print(f"✅ Loaded {len(df)} rows from Google Sheets")
        
        # Create preview (5 rows) and clean NaN values
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
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, sheets_request.question or "")
        
        # Ensure results is a dictionary
        if results is None:
            results = {}
        
        # Create the analysis_results structure
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
        
        # DEEP CLEAN - recursively clean all Timestamp objects and numpy types
        def deep_clean_for_db(obj):
            """Recursively clean all objects for database JSON serialization"""
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
                # CRITICAL: Convert any non-string keys to strings
                cleaned = {}
                for k, v in obj.items():
                    # Convert key to string if needed
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
                except:
                    return None
        
        # Clean the results for database storage
        cleaned_results = deep_clean_for_db(analysis_results)
        
        # Also clean the data_source
        data_source = {
            "sheet_id": sheet_id[:8] + "...",
            "sheet_range": sheet_range,
            "rows": len(df),
            "columns": list(df.columns)
        }
        cleaned_data_source = deep_clean_for_db(data_source)
        
        # Save to history
        history = AnalysisHistory(
            user_id=current_user.id,
            analysis_type="google_sheets",
            question=sheets_request.question or "General Overview",
            raw_results=cleaned_results,
            data_source=cleaned_data_source
        )
        db.add(history)
        db.commit()
        
        print(f"💾 Analysis saved to history (ID: {history.id})")
        
        # Clean the analysis_results for API response (same cleaning)
        final_results = deep_clean_for_db(analysis_results)
        
        return FileUploadResponse(
            filename=f"google_sheet_{sheet_id[:8]}",
            rows=len(df),
            columns=list(df.columns),
            preview=cleaned_preview,
            analysis_results=final_results
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-google-sheets")
@limiter.limit("30/minute")
async def test_google_sheets_connection(
    request: Request,
    sheets_request: GoogleSheetsTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Test Google Sheets connection and validate schema
    """
    try:
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise HTTPException(status_code=500, detail="Google credentials not configured")
        
        print(f"🔍 Google Sheets test by user {current_user.username}: {sheets_request.sheet_id[:8]}...")
        
        connector = GoogleSheetsConnector(sheets_request.sheet_id, sheets_request.sheet_range)
        df = connector.fetch_sheet()
        
        if len(df) == 0:
            return {
                "status": "success", 
                "message": "Connected but sheet is empty",
                "permission_status": connector.get_permission_status(),
                "permission_warning": connector.get_permission_warning()
            }
        
        # 🔐 VALIDATE SCHEMA
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
                detail=f"Schema validation failed: Missing required columns: {', '.join(missing)}. Your sheet must contain 'date' and 'revenue' columns."
            )
        
        # Check date column can be parsed
        date_col = found_columns['date']
        try:
            pd.to_datetime(df[date_col], errors='raise')
        except:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Column '{date_col}' contains invalid date formats."
            )
        
        # Check revenue column is numeric
        revenue_col = found_columns['revenue']
        try:
            pd.to_numeric(df[revenue_col], errors='raise')
        except:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Column '{revenue_col}' contains non-numeric values."
            )
        
        # Clean preview data
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
        
        # Build response with permission info
        response = {
            "status": "success", 
            "message": f"Successfully connected! Found {len(df)} rows with valid schema.",
            "columns": list(df.columns),
            "preview": cleaned_preview,
            "found_columns": found_columns,
            "permission_status": connector.get_permission_status()
        }
        
        # Add warning if service account has write access
        permission_warning = connector.get_permission_warning()
        if permission_warning:
            response["warning"] = permission_warning
            response["message"] = f"Connected! {permission_warning}"
        
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HISTORY ENDPOINTS ====================

@router.get("/history")
async def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """Get user's analysis history with optional metric filters"""
    # Build base query
    query = db.query(AnalysisHistory).filter(
        AnalysisHistory.user_id == current_user.id
    )
    
    # Get total count for pagination
    total = query.count()
    
    # Get paginated results
    history = query.order_by(
        AnalysisHistory.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Build response with additional stats
    result = []
    for h in history:
        # Get summary metrics for this analysis (if available)
        summary_metrics = {}
        if h.metrics:
            # Get key metrics for quick display
            revenue_metric = next((m for m in h.metrics if m.metric_type == 'total_revenue'), None)
            profit_metric = next((m for m in h.metrics if m.metric_type == 'profit_margin'), None)
            
            if revenue_metric:
                summary_metrics['total_revenue'] = float(revenue_metric.metric_value)
            if profit_metric:
                summary_metrics['profit_margin'] = float(profit_metric.metric_value)
        
        # Get insight count
        insight_count = len(h.insights) if h.insights else 0
        
        result.append({
            "id": h.id,
            "type": h.analysis_type,
            "question": h.question,
            "created_at": h.created_at.isoformat(),
            "data_source": h.data_source,
            "summary_metrics": summary_metrics,
            "insight_count": insight_count
        })
    
    return {
        "items": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/history/{history_id}")
async def get_analysis_by_id(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_raw: bool = False
):
    """Get specific analysis by ID with optional structured data"""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Build base response
    response = {
        "id": analysis.id,
        "type": analysis.analysis_type,
        "question": analysis.question,
        "created_at": analysis.created_at.isoformat(),
        "data_source": analysis.data_source,
        "structured_metrics": [],
        "insights": [],
        "charts": []
    }
    
    # Add structured metrics if available
    if analysis.metrics:
        metrics_by_category = {}
        for metric in analysis.metrics:
            metric_dict = {
                "metric_type": metric.metric_type,
                "metric_value": float(metric.metric_value) if metric.metric_value else None,
                "category": metric.category,
                "category_name": metric.category_name
            }
            if metric.metric_date:
                metric_dict["metric_date"] = metric.metric_date.isoformat()
            
            # Group by category for better organization
            cat_key = metric.category or "general"
            if cat_key not in metrics_by_category:
                metrics_by_category[cat_key] = []
            metrics_by_category[cat_key].append(metric_dict)
        
        response["structured_metrics"] = metrics_by_category
    
    # Add structured insights if available
    if analysis.insights:
        insights_by_type = {}
        for insight in analysis.insights:
            insight_dict = {
                "text": insight.insight_text,
                "confidence_score": float(insight.confidence_score) if insight.confidence_score else None
            }
            
            if insight.insight_type not in insights_by_type:
                insights_by_type[insight.insight_type] = []
            insights_by_type[insight.insight_type].append(insight_dict)
        
        response["insights"] = insights_by_type
    
    # Add chart references if available
    if analysis.charts:
        response["charts"] = [
            {
                "type": chart.chart_type,
                "path": chart.chart_path,
                "data": chart.chart_data
            }
            for chart in analysis.charts
        ]
    
    # Include raw results if requested (for full context)
    if include_raw and analysis.raw_results:
        response["raw_results"] = analysis.raw_results
    elif analysis.raw_results:
        # Include a summary instead of full raw results
        response["raw_results_summary"] = {
            "has_raw_data": True,
            "note": "Use ?include_raw=true to get full raw results"
        }
    
    return response


@router.get("/history/{history_id}/metrics")
async def get_analysis_metrics(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    metric_type: Optional[str] = None,
    category: Optional[str] = None
):
    """Get only structured metrics for an analysis (lightweight)"""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Query metrics
    query = db.query(AnalysisMetric).filter(AnalysisMetric.analysis_id == history_id)
    
    if metric_type:
        query = query.filter(AnalysisMetric.metric_type == metric_type)
    if category:
        query = query.filter(AnalysisMetric.category == category)
    
    metrics = query.all()
    
    return {
        "analysis_id": history_id,
        "metrics": [
            {
                "type": m.metric_type,
                "value": float(m.metric_value) if m.metric_value else None,
                "category": m.category,
                "category_name": m.category_name,
                "date": m.metric_date.isoformat() if m.metric_date else None
            }
            for m in metrics
        ]
    }


@router.get("/history/{history_id}/insights")
async def get_analysis_insights(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    insight_type: Optional[str] = None
):
    """Get only insights for an analysis (lightweight)"""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Query insights
    query = db.query(AnalysisInsight).filter(AnalysisInsight.analysis_id == history_id)
    
    if insight_type:
        query = query.filter(AnalysisInsight.insight_type == insight_type)
    
    insights = query.all()
    
    return {
        "analysis_id": history_id,
        "insights": [
            {
                "text": i.insight_text,
                "type": i.insight_type,
                "confidence": float(i.confidence_score) if i.confidence_score else None
            }
            for i in insights
        ]
    }


@router.get("/history/{history_id}/charts")
async def get_analysis_charts(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chart references for an analysis"""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "analysis_id": history_id,
        "charts": [
            {
                "type": chart.chart_type,
                "path": chart.chart_path,
                "data": chart.chart_data,
                "url": f"/api/v1/analysis/chart/{chart.chart_path.split('/')[-1]}"
            }
            for chart in analysis.charts
        ]
    }


@router.delete("/history/{history_id}")
async def delete_analysis(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an analysis and all related data"""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Also delete associated chart files
    import os
    for chart in analysis.charts:
        if chart.chart_path and os.path.exists(chart.chart_path):
            try:
                os.remove(chart.chart_path)
                print(f"Deleted chart file: {chart.chart_path}")
            except Exception as e:
                print(f"Could not delete chart file: {e}")
    
    # Delete the analysis (cascades to metrics, insights, charts)
    db.delete(analysis)
    db.commit()
    
    return {"message": "Analysis deleted successfully"}


@router.get("/history/aggregate/metrics")
async def get_aggregate_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    metric_type: str = "total_revenue",
    days: int = 30
):
    """Get aggregated metrics across all analyses (for dashboards)"""
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    metrics = db.query(AnalysisMetric).join(
        AnalysisHistory
    ).filter(
        AnalysisHistory.user_id == current_user.id,
        AnalysisHistory.created_at >= cutoff_date,
        AnalysisMetric.metric_type == metric_type
    ).all()
    
    if not metrics:
        return {"metric_type": metric_type, "values": [], "trend": None}
    
    # Group by date
    from collections import defaultdict
    daily_values = defaultdict(list)
    
    for metric in metrics:
        if metric.metric_date:
            date_key = metric.metric_date.isoformat()
        else:
            # Use analysis creation date for non-time-series metrics
            analysis = db.query(AnalysisHistory).filter(
                AnalysisHistory.id == metric.analysis_id
            ).first()
            if analysis:
                date_key = analysis.created_at.date().isoformat()
            else:
                continue
        daily_values[date_key].append(float(metric.metric_value))
    
    # Calculate average per day
    aggregated = [
        {"date": date, "value": sum(values) / len(values)}
        for date, values in sorted(daily_values.items())
    ]
    
    # Calculate trend
    trend = None
    if len(aggregated) >= 2:
        first_value = aggregated[0]["value"]
        last_value = aggregated[-1]["value"]
        if first_value > 0:
            percent_change = ((last_value - first_value) / first_value) * 100
            trend = {
                "direction": "up" if last_value > first_value else "down",
                "percent_change": round(percent_change, 1)
            }
    
    return {
        "metric_type": metric_type,
        "values": aggregated,
        "trend": trend,
        "period_days": days
    }


# ==================== CHART & HEALTH ENDPOINTS ====================

@router.get("/chart/{filename}")
async def get_chart(filename: str, key: int = 0):
    """Serve chart images with cache busting"""
    charts_dir = os.path.join(os.getcwd(), "agents", "charts")
    file_path = os.path.join(charts_dir, filename)
    
    # Security: Prevent directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chart not found")
    
    return FileResponse(file_path, media_type="image/png", filename=filename)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (no rate limit needed)"""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/validate-schema")
@limiter.limit("30/minute")
async def validate_file_schema(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Validate file schema without running full analysis
    """
    temp_file_path = None
    try:
        print(f"\n{'='*60}")
        print(f"🔍 VALIDATING FILE: {file.filename}")
        print(f"User: {current_user.username}")
        print(f"📏 File size: {file.size} bytes")
        print(f"📁 Content type: {file.content_type}")
        print(f"{'='*60}")
        
        # Check file extension
        file_type = file.filename.split('.')[-1].lower()
        allowed_extensions = ['csv', 'xlsx', 'xls', 'db', 'sqlite', 'sqlite3']
        print(f"📋 Detected file type: {file_type}")
        
        if file_type not in allowed_extensions:
            print(f"❌ Invalid file type: {file_type}")
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save file temporarily
        print(f"💾 Saving file temporarily...")
        temp_file_path = await DataSourceHandler.save_upload_file(file)
        print(f"✅ File saved to: {temp_file_path}")
        print(f"📏 Saved file size: {os.path.getsize(temp_file_path)} bytes")
        
        # Read just the first few rows based on file type
        print(f"📖 Reading file as {file_type}...")
        try:
            if file_type in ['db', 'sqlite', 'sqlite3']:
                # For SQLite, read the first table
                import sqlite3
                conn = sqlite3.connect(temp_file_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                if tables:
                    table_name = tables[0][0]
                    df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
                else:
                    df = pd.DataFrame()
                conn.close()
                print(f"✅ SQLite read successfully")
            elif file_type == 'csv':
                df = pd.read_csv(temp_file_path, nrows=5)
                print(f"✅ CSV read successfully")
            else:
                # Excel files
                if file_type == 'xlsx':
                    df = pd.read_excel(temp_file_path, nrows=5, engine='openpyxl')
                else:
                    df = pd.read_excel(temp_file_path, nrows=5, engine='xlrd')
                print(f"✅ Excel read successfully")
        except Exception as e:
            print(f"❌ Failed to read file: {str(e)}")
            return {
                "valid": False,
                "message": f"Could not read file: {str(e)}"
            }
        
        
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📋 Columns found: {list(df.columns)}")
        
        # Check for required columns (case-insensitive)
        required_columns = ['date', 'revenue']
        df_columns_lower = [col.lower() for col in df.columns]
        
        print(f"🔤 Lowercase columns: {df_columns_lower}")
        
        missing = []
        found_columns = {}
        
        for req_col in required_columns:
            if req_col in df_columns_lower:
                original_col = df.columns[df_columns_lower.index(req_col)]
                found_columns[req_col] = original_col
                print(f"✅ Found '{req_col}' as column '{original_col}'")
            else:
                missing.append(req_col)
                print(f"❌ Missing required column: '{req_col}'")
        
        if missing:
            print(f"❌ Validation failed: Missing columns {missing}")
            return {
                "valid": False,
                "message": f"Missing required columns: {', '.join(missing)}. Your file must contain 'date' and 'revenue' columns.",
                "found_columns": list(df.columns)
            }
        
        # Check date column can be parsed
        date_col = found_columns['date']
        print(f"📅 Validating date column: '{date_col}'")
        
        try:
            parsed_dates = pd.to_datetime(df[date_col], errors='coerce')
            invalid_dates = parsed_dates.isna().sum()
            
            if invalid_dates > 0:
                print(f"⚠️ Found {invalid_dates} invalid dates")
                return {
                    "valid": False,
                    "message": f"The '{date_col}' column contains {invalid_dates} invalid date format(s).",
                    "found_columns": list(df.columns)
                }
            print(f"✅ All dates are valid")
        except Exception as e:
            print(f"❌ Date parsing error: {str(e)}")
            return {
                "valid": False,
                "message": f"Could not parse dates in column '{date_col}'. Error: {str(e)}",
                "found_columns": list(df.columns)
            }
        
        # Check revenue column is numeric
        revenue_col = found_columns['revenue']
        print(f"💰 Validating revenue column: '{revenue_col}'")
        
        try:
            numeric_revenue = pd.to_numeric(df[revenue_col], errors='coerce')
            invalid_revenue = numeric_revenue.isna().sum()
            
            if invalid_revenue > 0:
                print(f"⚠️ Found {invalid_revenue} non-numeric revenue values")
                return {
                    "valid": False,
                    "message": f"The '{revenue_col}' column contains {invalid_revenue} non-numeric value(s).",
                    "found_columns": list(df.columns)
                }
            print(f"✅ All revenue values are numeric")
        except Exception as e:
            print(f"❌ Revenue parsing error: {str(e)}")
            return {
                "valid": False,
                "message": f"Could not parse revenue in column '{revenue_col}'. Error: {str(e)}",
                "found_columns": list(df.columns)
            }
        
        print(f"\n{'='*60}")
        print(f"✅✅✅ VALIDATION PASSED! File is ready for analysis.")
        print(f"{'='*60}\n")
        
        # Clean the preview data to remove NaN values
        preview_data = df.head(2).to_dict('records')
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
            "valid": True,
            "message": "Schema validation passed",
            "columns": list(df.columns),
            "preview": cleaned_preview,
            "found_columns": found_columns
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"🧹 Cleaned up temp file: {temp_file_path}")


@router.post("/test-sqlite-connection")
@limiter.limit("20/minute")
async def test_sqlite_connection(
    request: Request,
    file: UploadFile = File(...),
    table: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """
    Test SQLite file connection and validate schema
    """
    temp_file_path = None
    try:
        print(f"\n{'='*60}")
        print(f"🔍 TEST SQLITE CONNECTION REQUEST RECEIVED")
        print(f"{'='*60}")
        print(f"File: {file.filename}")
        print(f"Table: {table}")
        print(f"User: {current_user.username} (ID: {current_user.id})")
        print(f"{'='*60}\n")
        
        # Check file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Save file temporarily
        temp_file_path = await DataSourceHandler.save_upload_file(file)
        print(f"📁 File saved to: {temp_file_path}")
        
        # Connect to SQLite
        import sqlite3
        print(f"🔌 Connecting to SQLite database...")
        conn = sqlite3.connect(temp_file_path)
        cursor = conn.cursor()
        
        # Check if table exists
        print(f"📋 Checking if table '{table}' exists...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"Table '{table}' not found in database")
        
        # Get column count
        print(f"📊 Getting column info for table '{table}'...")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        column_count = len(columns)
        print(f"📊 Table has {column_count} columns")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        print(f"📊 Table has {row_count} rows")
        
        # Read sample data
        print(f"📖 Reading sample data...")
        df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 5", conn)
        conn.close()
        
        if len(df) == 0:
            return {
                "success": True,
                "message": f"Connected to SQLite database but table '{table}' is empty",
                "rows_preview": 0,
                "columns": list(df.columns) if len(df.columns) > 0 else []
            }
        
        # Validate schema
        required_columns = ['date', 'revenue']
        df_columns_lower = [col.lower() for col in df.columns]
        
        missing = []
        found_columns = {}
        
        for req_col in required_columns:
            if req_col in df_columns_lower:
                original_col = df.columns[df_columns_lower.index(req_col)]
                found_columns[req_col] = original_col
                print(f"✅ Found '{req_col}' as column '{original_col}'")
            else:
                missing.append(req_col)
                print(f"❌ Missing required column: '{req_col}'")
        
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Missing required columns: {', '.join(missing)}. Your table must contain 'date' and 'revenue' columns."
            )
        
        # Validate date column
        date_col = found_columns['date']
        print(f"📅 Validating date column '{date_col}'...")
        try:
            pd.to_datetime(df[date_col], errors='raise')
            print("✅ Date column valid")
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Column '{date_col}' contains invalid date formats."
            )
        
        # Validate revenue column
        revenue_col = found_columns['revenue']
        print(f"💰 Validating revenue column '{revenue_col}'...")
        try:
            pd.to_numeric(df[revenue_col], errors='raise')
            print("✅ Revenue column valid")
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Column '{revenue_col}' contains non-numeric values."
            )
        
        # Clean preview data
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
            "size_info": {
                "columns": column_count,
                "rows": row_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"🧹 Cleaned up temp file: {temp_file_path}")

@router.post("/sqlite-tables")
@limiter.limit("30/minute")
async def get_sqlite_tables(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Get list of tables from uploaded SQLite file"""
    temp_file_path = None
    try:
        print(f"📁 SQLite tables request from user {current_user.username}")
        
        # Save file temporarily
        temp_file_path = await DataSourceHandler.save_upload_file(file)
        
        # Connect to SQLite
        import sqlite3
        conn = sqlite3.connect(temp_file_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return {"tables": tables}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


# app/api/v1/endpoints/analysis.py

@router.post("/upload-sqlite", response_model=FileUploadResponse)
@limiter.limit("10/minute")
async def upload_sqlite_file(
    request: Request,
    file: UploadFile = File(...),
    question: Optional[str] = Form(""),
    table: Optional[str] = Form(""),  # Change from None to empty string
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a SQLite file and analyze a specific table
    """
    temp_file_path = None
    try:
        print(f"\n{'='*60}")
        print(f"📊 SQLITE FILE ANALYSIS REQUESTED")
        print(f"{'='*60}")
        print(f"File: {file.filename}")
        print(f"Table: '{table}'")  # Print with quotes to see exact value
        print(f"Question: {question[:50] if question else 'No question (overview)'}")
        print(f"User: {current_user.username} (ID: {current_user.id})")
        print(f"{'='*60}\n")
        
        # Check file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Check file extension
        file_type = file.filename.split('.')[-1].lower()
        allowed_extensions = ['db', 'sqlite', 'sqlite3']
        if file_type not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save file temporarily
        import tempfile
        import os
        
        # Create a temporary file with the original extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_file_path = tmp_file.name
        
        print(f"📁 File saved to: {temp_file_path}")
        print(f"📏 File size: {os.path.getsize(temp_file_path)} bytes")
        
        # Read SQLite file
        print(f"📊 Reading SQLite file...")
        import sqlite3
        import pandas as pd
        
        # Connect to the SQLite file
        conn = sqlite3.connect(temp_file_path)
        
        # If table not specified or empty string, get first table
        if not table or not table.strip():
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = cursor.fetchall()
            if not tables:
                conn.close()
                raise HTTPException(status_code=400, detail="SQLite file contains no tables")
            table = tables[0][0]
            print(f"📊 No table specified, using first table: {table}")
        
        # Clean the table name (remove any extra spaces)
        table = table.strip()
        
        # Check if table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            available_tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Table '{table}' not found. Available tables: {', '.join(available_tables)}"
            )
        
        # Read the table
        print(f"📋 Reading table: {table}")
        df = pd.read_sql_query(f"SELECT * FROM [{table}]" if ' ' in table else f"SELECT * FROM {table}", conn)
        conn.close()
        
        print(f"✅ Loaded {len(df)} rows from SQLite table '{table}'")
        
        if len(df) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Table '{table}' is empty. Please select a table with data."
            )
        
        # 🔐 VALIDATE THE DATAFRAME
        validate_dataframe(df)
        
        # Create preview (5 rows) and clean NaN values
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
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, question or "")
        
        # Ensure results is a dictionary
        if results is None:
            results = {}
        
        # Create the analysis_results structure
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
        
        # Deep clean for JSON serialization
        def deep_clean_for_json(obj):
            if obj is None:
                return None
            elif isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj) if isinstance(obj, np.floating) else int(obj)
            elif isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {str(k): deep_clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple, set)):
                return [deep_clean_for_json(item) for item in obj]
            elif isinstance(obj, pd.Series):
                return deep_clean_for_json(obj.to_dict())
            elif isinstance(obj, pd.DataFrame):
                return deep_clean_for_json(obj.to_dict('records'))
            else:
                try:
                    return str(obj)
                except:
                    return None
        
        cleaned_results = deep_clean_for_json(analysis_results)
        
        # Save to history
        from app.api.v1.models.analysis import AnalysisHistory
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
        
        print(f"💾 Analysis saved to history (ID: {history.id})")
        
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
        import traceback
        traceback.print_exc()
        # Return a clean error message (string, not object)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"🧹 Cleaned up temp file: {temp_file_path}")
            except:
                pass