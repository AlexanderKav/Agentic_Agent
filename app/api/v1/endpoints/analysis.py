from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from typing import Optional
import pandas as pd
import tempfile
import os
import time
import re
import math
import numpy as np
from sqlalchemy import text 
from fastapi.responses import FileResponse

# Rate limiting imports
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1.models.requests import AnalysisRequest, DatabaseConnectionRequest, DatabaseTestRequest
from app.api.v1.models.responses import AnalysisResponse, FileUploadResponse, HealthResponse
from app.core.analysis import AnalysisOrchestrator
from app.core.data_source import DataSourceHandler
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
ALLOWED_DB_HOSTS = ['localhost', '127.0.0.1', '::1', '0.0.0.0']  # Add your allowed hosts
DANGEROUS_SQL_KEYWORDS = [
    'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 
    'INSERT', 'UPDATE', 'MERGE', 'REPLACE', 'GRANT',
    'REVOKE', 'EXEC', 'EXECUTE'
]

# ==================== VALIDATION FUNCTIONS ====================

def validate_database_config(config: dict):
    """Validate database configuration for security"""
    
    # 1. Validate table name (if provided)
    table_name = config.get('table', '')
    if table_name:
        # Only allow alphanumeric and underscores
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise HTTPException(
                status_code=400,
                detail="Invalid table name. Use only letters, numbers, and underscores"
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
    
    # 4. Validate host (prevent SSRF attacks)
    host = config.get('host', '')
    if host and host not in ALLOWED_DB_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=f"Host '{host}' not in allowed list. Contact admin to add new hosts."
        )
    
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

# ==================== DATABASE ENDPOINTS ====================

@router.post("/database", response_model=FileUploadResponse)
@limiter.limit("20/minute")  # 20 database analyses per minute
async def analyze_database(
    request: Request,  # Required for rate limiting
    db_request: DatabaseConnectionRequest
):
    """
    Connect to a database and analyze data
    """
    try:
        config = db_request.connection_config
        
        # 🔐 VALIDATE THE CONFIGURATION
        validate_database_config(config)
        
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
        
        # 🔐 VALIDATE THE DATAFRAME
        validate_dataframe(df)
        
        print(f"✅ Loaded {len(df)} rows from database")
        
        # Create preview (5 rows)
        preview = df.head(5).to_dict('records')
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, db_request.question)
        
        # DEBUG: Print the structure of results
        print("\n" + "="*60)
        print("🗄️ DATABASE RESULTS STRUCTURE")
        print("="*60)
        print(f"Results keys: {results.keys()}")
        
        # IMPORTANT: Don't flatten the insights - preserve the full structure
        insights_data = results.get("insights", {})
        raw_insights_data = results.get("raw_insights", {})
        
        print(f"Insights type: {type(insights_data)}")
        print(f"Insights preview: {str(insights_data)[:200]}...")
        print("="*60 + "\n")
        
        # Create the analysis_results structure - PRESERVE the original structure
        analysis_results = {
            "success": results.get("success", False),
            "insights": insights_data,
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
@limiter.limit("30/minute")
async def test_database_connection(
    request: Request,
    db_request: DatabaseTestRequest
):
    """
    Test database connection and validate schema without running analysis
    """
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
        print(f"Password: {'*' * len(db_request.password) if db_request.password else 'None'}")
        print(f"Use query: {db_request.use_query}")
        if db_request.use_query:
            print(f"Query: {db_request.query[:100]}...")
        print(f"{'='*60}\n")
        
        # Build connection string with validation
        if db_request.db_type == 'postgresql':
            conn_string = f"postgresql://{db_request.username}:{db_request.password}@{db_request.host}:{db_request.port}/{db_request.database}"
        elif db_request.db_type == 'mysql':
            conn_string = f"mysql+pymysql://{db_request.username}:{db_request.password}@{db_request.host}:{db_request.port}/{db_request.database}"
        elif db_request.db_type == 'sqlite':
            # ========== SQLITE PATH VALIDATION WITH ABSOLUTE PATH ==========
            import os
            
            original_path = db_request.database
            print(f"📁 Original path: {original_path}")
            
            # Convert to absolute path
            if not os.path.isabs(original_path):
                # Get the absolute path relative to current working directory
                abs_path = os.path.abspath(original_path)
                print(f"📁 Converted to absolute path: {abs_path}")
            else:
                abs_path = original_path
                print(f"📁 Using absolute path: {abs_path}")
            
            # 1. Check for .db extension
            if not abs_path.endswith('.db'):
                raise HTTPException(
                    status_code=400,
                    detail=f"SQLite file must end with .db extension. Got: {abs_path}"
                )
            
            # 2. Get directory path
            directory = os.path.dirname(abs_path)
            
            # 3. If directory is specified, check if it exists
            if directory and not os.path.exists(directory):
                raise HTTPException(
                    status_code=400,
                    detail=f"Directory does not exist: {directory}. Please create the directory first."
                )
            
            # 4. Check if file exists and has proper permissions
            file_exists = os.path.exists(abs_path)
            if file_exists:
                # File exists - check permissions
                if not os.access(abs_path, os.R_OK):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot read SQLite file: {abs_path}. Check file permissions."
                    )
                if not os.access(abs_path, os.W_OK):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot write to SQLite file: {abs_path}. Check file permissions."
                    )
                print(f"✅ SQLite file exists and is accessible: {abs_path}")
                print(f"📏 File size: {os.path.getsize(abs_path)} bytes")
            else:
                # File doesn't exist - check if we can create it
                if directory and not os.access(directory, os.W_OK):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot write to directory: {directory}. Cannot create SQLite file."
                    )
                print(f"⚠️ SQLite file doesn't exist yet. It will be created when connecting: {abs_path}")
            
            # Update the database path to the absolute path
            db_request.database = abs_path
            conn_string = f"sqlite:///{abs_path}"
            # ========== END SQLITE PATH VALIDATION ==========
            
        else:
            raise ValueError(f"Unsupported database type: {db_request.db_type}")
        
        print(f"🔌 Connection string: {conn_string}")
        
        # Create connector and test connection
        connector = DatabaseConnector(conn_string)
        
        if not connector.test_connection():
            print("❌ Failed to connect to database")
            
            # Provide more specific error for SQLite
            if db_request.db_type == 'sqlite':
                db_path = db_request.database
                if not os.path.exists(db_path):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot create SQLite database at: {db_path}. Check directory permissions."
                    )
                elif os.path.exists(db_path) and not os.access(db_path, os.W_OK):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot write to SQLite database at: {db_path}. Check file permissions."
                    )
            
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        print("✅ Successfully connected to database")
        
        # If table name provided, validate schema
        if db_request.table and not db_request.use_query:
            print(f"📋 Validating table: {db_request.table}")
            
            # ========== DATABASE-AGNOSTIC SIZE VALIDATION ==========
            with connector.engine.connect() as conn:
                # Get column count based on database type
                try:
                    if db_request.db_type == 'sqlite':
                        # SQLite uses PRAGMA table_info
                        result = conn.execute(text(f"PRAGMA table_info({db_request.table})"))
                        columns = result.fetchall()
                        column_count = len(columns)
                        print(f"📊 SQLite table has {column_count} columns")
                    elif db_request.db_type == 'postgresql':
                        # PostgreSQL uses information_schema
                        result = conn.execute(text("""
                            SELECT COUNT(*) 
                            FROM information_schema.columns 
                            WHERE table_name = :table_name
                        """), {"table_name": db_request.table})
                        column_count = result.scalar()
                        print(f"📊 PostgreSQL table has {column_count} columns")
                    elif db_request.db_type == 'mysql':
                        # MySQL also uses information_schema
                        result = conn.execute(text("""
                            SELECT COUNT(*) 
                            FROM information_schema.columns 
                            WHERE table_name = :table_name
                        """), {"table_name": db_request.table})
                        column_count = result.scalar()
                        print(f"📊 MySQL table has {column_count} columns")
                    else:
                        column_count = 0
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not access table '{db_request.table}'. Error: {str(e)}"
                    )
                
                # Define limits
                MAX_COLUMNS = 1000
                if column_count > MAX_COLUMNS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Table has {column_count} columns. Maximum allowed is {MAX_COLUMNS}. Your table is too wide."
                    )
                
                # Get row count (works for all databases)
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {db_request.table}"))
                    row_count = result.scalar()
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not query table '{db_request.table}'. Error: {str(e)}"
                    )
                
                MAX_ROWS = 100000
                if row_count > MAX_ROWS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Table has {row_count:,} rows. Maximum allowed is {MAX_ROWS:,}."
                    )
                
                print(f"✅ Size validation passed: {column_count} columns, {row_count} rows")
            # ========== END SIZE VALIDATION ==========
            
            # Now it's safe to read a small sample for schema validation
            try:
                df = connector.fetch_query(f"SELECT * FROM {db_request.table} LIMIT 5")
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not read data from table '{db_request.table}'. Error: {str(e)}"
                )
            
            if len(df) == 0:
                return {
                    "status": "success", 
                    "message": f"Connected to database but table '{db_request.table}' is empty"
                }
            
            # 🔐 VALIDATE SCHEMA
            required_columns = ['date', 'revenue']
            df_columns_lower = [col.lower() for col in df.columns]
            
            print(f"📊 Found columns: {df_columns_lower}")
            
            missing = []
            for req_col in required_columns:
                if req_col not in df_columns_lower:
                    missing.append(req_col)
            
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Schema validation failed: Missing required columns: {', '.join(missing)}. Your table must contain 'date' and 'revenue' columns."
                )
            
            # Check date column can be parsed
            date_col = df.columns[df_columns_lower.index('date')]
            print(f"📅 Validating date column: '{date_col}'")
            try:
                pd.to_datetime(df[date_col], errors='raise')
                print("✅ Date column valid")
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Schema validation failed: Column '{date_col}' contains invalid date formats. Error: {str(e)}"
                )
            
            # Check revenue column is numeric
            revenue_col = df.columns[df_columns_lower.index('revenue')]
            print(f"💰 Validating revenue column: '{revenue_col}'")
            try:
                pd.to_numeric(df[revenue_col], errors='raise')
                print("✅ Revenue column valid")
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Schema validation failed: Column '{revenue_col}' contains non-numeric values. Error: {str(e)}"
                )
            
            return {
                "status": "success", 
                "message": f"✅ Successfully connected! Table '{db_request.table}' has valid schema.",
                "rows_preview": len(df),
                "columns": list(df.columns),
                "size_info": {
                    "columns": column_count,
                    "rows": row_count
                }
            }
        
        # If custom query provided
        elif db_request.use_query and db_request.query:
            print(f"📝 Testing custom query")
            try:
                df = connector.fetch_query(f"{db_request.query} LIMIT 5")
                return {
                    "status": "success", 
                    "message": f"✅ Query executed successfully. Found {len(df)} rows.",
                    "rows_preview": len(df)
                }
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query execution failed: {str(e)}"
                )
        
        else:
            return {"status": "success", "message": "✅ Successfully connected to database"}
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ==================== FILE UPLOAD ENDPOINT ====================

@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit("10/minute")  # 10 uploads per minute
async def upload_file(
    request: Request,  # Required for rate limiting
    file: UploadFile = File(...),
    question: Optional[str] = Form("")
):
    """Upload a file (CSV/Excel) and analyze it"""
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
        allowed_extensions = ['csv', 'xlsx', 'xls']
        if file_type not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save and scan file
        temp_file_path = await DataSourceHandler.save_upload_file(file)
        
        # Read data
        df = DataSourceHandler.read_uploaded_file(temp_file_path, file_type)
        
        # 🔐 VALIDATE THE DATAFRAME
        validate_dataframe(df)
        
        # Create response with preview
        response = FileUploadResponse(
            filename=file.filename,
            rows=len(df),
            columns=list(df.columns),
            preview=df.head(5).to_dict('records')
        )
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, question or "")
        response.analysis_results = results
        
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


# ==================== GOOGLE SHEETS ENDPOINTS ====================

class GoogleSheetsRequest(BaseModel):
    question: str
    sheet_config: dict


class GoogleSheetsTestRequest(BaseModel):
    sheet_id: str
    sheet_range: Optional[str] = "A1:Z1000"


@router.post("/google-sheets", response_model=FileUploadResponse)
@limiter.limit("20/minute")  # 20 Google Sheets analyses per minute
async def analyze_google_sheets(
    request: Request,  # Required for rate limiting
    sheets_request: GoogleSheetsRequest
):
    """
    Connect to Google Sheets and analyze data
    """
    try:
        config = sheets_request.sheet_config
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
        
        # 🔐 VALIDATE THE DATAFRAME
        validate_dataframe(df)
        
        print(f"✅ Loaded {len(df)} rows from Google Sheets")
        
        # Create preview
        preview = df.head(5).to_dict('records')
        
        # Run analysis
        results, exec_time = await orchestrator.analyze_dataframe(df, sheets_request.question)
        
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
@limiter.limit("30/minute")
async def test_google_sheets_connection(
    request: Request,
    sheets_request: GoogleSheetsTestRequest
):
    """
    Test Google Sheets connection and validate schema
    """
    try:
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise HTTPException(status_code=500, detail="Google credentials not configured")
        
        connector = GoogleSheetsConnector(sheets_request.sheet_id, sheets_request.sheet_range)
        df = connector.fetch_sheet()
        
        if len(df) == 0:
            return {"status": "success", "message": "Connected but sheet is empty"}
        
        # 🔐 VALIDATE SCHEMA
        required_columns = ['date', 'revenue']
        df_columns_lower = [col.lower() for col in df.columns]
        
        missing = []
        for req_col in required_columns:
            if req_col not in df_columns_lower:
                missing.append(req_col)
        
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Missing required columns: {', '.join(missing)}. Your sheet must contain 'date' and 'revenue' columns."
            )
        
        # Check date column can be parsed
        date_col = df.columns[df_columns_lower.index('date')]
        try:
            pd.to_datetime(df[date_col], errors='raise')
        except:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Column '{date_col}' contains invalid date formats."
            )
        
        # Check revenue column is numeric
        revenue_col = df.columns[df_columns_lower.index('revenue')]
        try:
            pd.to_numeric(df[revenue_col], errors='raise')
        except:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: Column '{revenue_col}' contains non-numeric values."
            )
        
        # Convert DataFrame to dict and clean NaN values
        preview_data = df.head(3).to_dict('records')
        cleaned_preview = clean_for_json(preview_data)
        cleaned_columns = clean_for_json(list(df.columns))
        
        return {
            "status": "success", 
            "message": f"Successfully connected! Found {len(df)} rows with valid schema.",
            "columns": cleaned_columns,
            "preview": cleaned_preview
        }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
    file: UploadFile = File(...)
):
    """
    Validate file schema without running full analysis
    """
    temp_file_path = None
    try:
        print(f"\n{'='*60}")
        print(f"🔍 VALIDATING FILE: {file.filename}")
        print(f"📏 File size: {file.size} bytes")
        print(f"📁 Content type: {file.content_type}")
        print(f"{'='*60}")
        
        # Check file extension
        file_type = file.filename.split('.')[-1].lower()
        allowed_extensions = ['csv', 'xlsx', 'xls']
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
        
        # Read just the first few rows to check schema
        print(f"📖 Reading file as {file_type}...")
        try:
            if file_type == 'csv':
                df = pd.read_csv(temp_file_path, nrows=5)
                print(f"✅ CSV read successfully")
            else:
                df = pd.read_excel(temp_file_path, nrows=5)
                print(f"✅ Excel read successfully")
        except Exception as e:
            print(f"❌ Failed to read file: {str(e)}")
            return {
                "valid": False,
                "message": f"Could not read file: {str(e)}"
            }
        
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📋 Columns found: {list(df.columns)}")
        print(f"🔍 First row: {df.iloc[0].to_dict() if len(df) > 0 else 'No data'}")
        
        # Check for required columns (case-insensitive)
        required_columns = ['date', 'revenue']
        df_columns_lower = [col.lower() for col in df.columns]
        
        print(f"🔤 Lowercase columns: {df_columns_lower}")
        
        missing = []
        found_columns = {}
        
        for req_col in required_columns:
            if req_col in df_columns_lower:
                # Find the original column name
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
        print(f"📅 Sample date values: {df[date_col].head(3).tolist()}")
        
        try:
            # Try to parse dates
            parsed_dates = pd.to_datetime(df[date_col], errors='coerce')
            invalid_dates = parsed_dates.isna().sum()
            print(f"📅 Parsed dates: {parsed_dates.tolist()}")
            
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
        print(f"💰 Sample revenue values: {df[revenue_col].head(3).tolist()}")
        
        try:
            # Try to convert to numeric
            numeric_revenue = pd.to_numeric(df[revenue_col], errors='coerce')
            invalid_revenue = numeric_revenue.isna().sum()
            print(f"💰 Parsed revenue: {numeric_revenue.tolist()}")
            
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
        cleaned_preview = clean_for_json(preview_data)
        
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