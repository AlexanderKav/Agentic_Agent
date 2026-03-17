from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
import re
import os

class DataSourceType(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    DATABASE = "database"
    GOOGLE_SHEETS = "google_sheets"

class AnalysisRequest(BaseModel):
    """Request model for analysis endpoint"""
    question: str = Field(..., description="The question to analyze")
    data_source: DataSourceType = Field(..., description="Type of data source")
    source_config: Dict[str, Any] = Field(..., description="Configuration for the data source")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What were our top products by revenue?",
                "data_source": "database",
                "source_config": {
                    "connection_string": "postgresql://user:pass@localhost:5432/db",
                    "table": "sales"
                }
            }
        }

class DatabaseConnectionRequest(BaseModel):
    """Request model for database connection with analysis"""
    question: str = Field(..., description="The question to analyze")
    connection_config: Dict[str, Any] = Field(..., description="Database connection configuration")

class DatabaseTestRequest(BaseModel):
    """Request model for testing database connection"""
    db_type: str
    host: Optional[str] = None
    port: Optional[str] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    table: Optional[str] = None
    query: Optional[str] = None
    use_query: Optional[bool] = False
    
    @validator('db_type')
    def validate_db_type(cls, v):
        allowed = ['postgresql', 'mysql', 'sqlite']
        if v not in allowed:
            raise ValueError(f"Database type must be one of: {allowed}")
        return v
    
    @validator('port')
    def validate_port(cls, v):
        if v:
            try:
                port_num = int(v)
                if port_num < 1024 or port_num > 65535:
                    raise ValueError("Port must be between 1024 and 65535")
            except ValueError:
                raise ValueError("Invalid port number")
        return v
    
    @validator('database')
    def validate_database(cls, v, values):
        """Validate database name/path based on db_type"""
        db_type = values.get('db_type')
        
        if db_type == 'sqlite':
            # SQLite accepts full file paths
            # Remove any surrounding quotes that might be present
            v = v.strip('"\'')
            
            # Allow Windows and Unix paths
            if not re.match(r'^[a-zA-Z0-9_\ \-\.\\/:]+$', v):
                raise ValueError("Invalid database file path. Use only letters, numbers, spaces, and path characters (:, \\, /, ., -, _)")
            
            # Ensure it ends with .db
            if not v.endswith('.db'):
                raise ValueError("SQLite database file must end with .db extension")
        else:
            # PostgreSQL/MySQL database names are more restrictive
            if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
                raise ValueError("Database name contains invalid characters. Use only letters, numbers, underscores, and hyphens.")
        
        return v
    
    @validator('table')
    def validate_table(cls, v):
        if v and not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid table name. Use only letters, numbers, and underscores")
        return v

class GoogleSheetsRequest(BaseModel):
    """Request model for Google Sheets analysis"""
    question: str
    sheet_config: dict

class GoogleSheetsTestRequest(BaseModel):
    """Request model for testing Google Sheets connection"""
    sheet_id: str
    sheet_range: Optional[str] = "A1:Z1000"