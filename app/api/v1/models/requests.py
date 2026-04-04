# app/api/v1/models/requests.py
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


class DataSourceType(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    DATABASE = "database"
    GOOGLE_SHEETS = "google_sheets"


class AnalysisRequest(BaseModel):
    """Request model for analysis endpoint"""
    question: str = Field(..., description="The question to analyze")
    data_source: DataSourceType = Field(..., description="Type of data source")
    source_config: dict[str, Any] = Field(..., description="Configuration for the data source")

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
    connection_config: dict[str, Any] = Field(..., description="Database connection configuration")

    @validator('connection_config')
    def validate_connection_config(cls, v: dict) -> dict:
        """Validate database connection configuration"""
        required_fields = ['db_type', 'host', 'database', 'username']
        db_type = v.get('db_type')
        
        if db_type == 'sqlite':
            if 'database' not in v:
                raise ValueError("SQLite requires 'database' field with file path")
        elif db_type in ['postgresql', 'mysql']:
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Missing required field: {field} for {db_type} connection")
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        return v


class DatabaseTestRequest(BaseModel):
    """Request model for testing database connection"""
    db_type: str
    host: str | None = "localhost"
    port: str | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    table: str | None = None
    query: str | None = None
    use_query: bool | None = False

    @validator('db_type')
    def validate_db_type(cls, v: str) -> str:
        allowed = ['postgresql', 'mysql', 'sqlite']
        if v not in allowed:
            raise ValueError(f"Database type must be one of: {allowed}")
        return v

    @validator('host')
    def validate_host(cls, v: str | None) -> str | None:
        if v:
            # Allow localhost, IP addresses, and hostnames
            if not re.match(r'^[a-zA-Z0-9\.\-_]+$', v):
                raise ValueError("Invalid host format. Use only letters, numbers, dots, hyphens, and underscores.")
        return v

    @validator('port')
    def validate_port(cls, v: str | None) -> str | None:
        if v:
            try:
                port_num = int(v)
                if port_num < 1024 or port_num > 65535:
                    raise ValueError("Port must be between 1024 and 65535")
            except ValueError:
                raise ValueError("Invalid port number")
        return v

    @validator('database')
    def validate_database(cls, v: str | None, values: dict) -> str | None:
        """Validate database name/path based on db_type"""
        db_type = values.get('db_type')

        if v is None:
            raise ValueError("Database name is required")

        if db_type == 'sqlite':
            # SQLite accepts full file paths
            v = v.strip('"\'')

            if not re.match(r'^[a-zA-Z0-9_\ \-\.\\/:]+$', v):
                raise ValueError("Invalid database file path. Use only letters, numbers, spaces, and path characters.")
        else:
            # PostgreSQL/MySQL database names
            if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
                raise ValueError("Database name contains invalid characters. Use only letters, numbers, underscores, and hyphens.")

        return v

    @validator('table')
    def validate_table(cls, v: str | None) -> str | None:
        if v:
            v = v.strip()
            if not re.match(r'^[a-zA-Z0-9_]+$', v):
                raise ValueError("Invalid table name. Use only letters, numbers, and underscores")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "db_type": "postgresql",
                "host": "localhost",
                "port": "5432",
                "database": "sales_db",
                "username": "analyst_user",
                "password": "secure_password",
                "table": "sales_data",
                "use_query": False
            }
        }


class GoogleSheetsRequest(BaseModel):
    """Request model for Google Sheets analysis"""
    question: str
    sheet_config: dict

    @validator('sheet_config')
    def validate_sheet_config(cls, v: dict) -> dict:
        """Validate Google Sheets configuration"""
        if 'sheet_id' not in v:
            raise ValueError("sheet_config must contain 'sheet_id'")
        return v


class GoogleSheetsTestRequest(BaseModel):
    """Request model for testing Google Sheets connection"""
    sheet_id: str
    sheet_range: str | None = "A1:Z1000"

    @validator('sheet_id')
    def validate_sheet_id(cls, v: str) -> str:
        """Validate Google Sheet ID format"""
        # Extract ID from URL if full URL is provided
        if 'spreadsheets/d/' in v:
            match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', v)
            if match:
                return match.group(1)
        
        # Validate format
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError("Invalid Sheet ID format. Use only letters, numbers, hyphens, and underscores.")
        return v

    @validator('sheet_range')
    def validate_sheet_range(cls, v: str | None) -> str | None:
        """Validate sheet range format"""
        if v:
            # Basic validation for range format (e.g., A1:Z1000)
            if not re.match(r'^[A-Z]+[0-9]+:[A-Z]+[0-9]+$', v):
                # Allow named ranges
                if not re.match(r'^[A-Za-z0-9_]+$', v):
                    raise ValueError("Invalid sheet range format. Use format like 'A1:Z1000' or a named range")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "sheet_id": "1aBcDeFgHiJkLmNoPqRsTuVwXyZ",
                "sheet_range": "Sheet1!A1:Z1000"
            }
        }