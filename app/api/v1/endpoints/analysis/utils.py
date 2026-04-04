# app/api/v1/endpoints/analysis/utils.py
"""Shared utility functions for analysis endpoints."""

import math
import re
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROWS = 100000
MAX_QUERY_LENGTH = 2000
DANGEROUS_SQL_KEYWORDS = [
    'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
    'INSERT', 'UPDATE', 'MERGE', 'REPLACE', 'GRANT',
    'REVOKE', 'EXEC', 'EXECUTE'
]


def sanitize_for_json(obj: Any) -> Any:
    """Sanitize objects for JSON serialization, handling NaN, Inf, and numpy types."""
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
        return obj.isoformat()
    if isinstance(obj, dict):
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


def validate_database_config(config: dict) -> bool:
    """Validate database configuration for security."""
    db_type = config.get('db_type', 'postgresql')

    # Validate table name
    table_name = config.get('table', '')
    if table_name:
        table_name = table_name.strip()
        config['table'] = table_name

        if db_type == 'postgresql':
            if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid PostgreSQL table name '{table_name}'. Use only letters, numbers, and underscores."
                )
        elif db_type == 'mysql':
            if not re.match(r'^[a-zA-Z0-9_$]+$', table_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid MySQL table name '{table_name}'. Use only letters, numbers, underscores, and $."
                )
        elif db_type == 'sqlite':
            if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid SQLite table name '{table_name}'. Use only letters, numbers, and underscores."
                )

        if len(table_name) > 63:
            raise HTTPException(
                status_code=400,
                detail=f"Table name too long ({len(table_name)} chars). Maximum is 63 characters."
            )

    # Validate query
    query = config.get('query', '')
    if query and len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long. Maximum {MAX_QUERY_LENGTH} characters"
        )

    if query:
        query_upper = query.upper()
        for keyword in DANGEROUS_SQL_KEYWORDS:
            if keyword in query_upper:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dangerous SQL keyword '{keyword}' not allowed. Only SELECT queries are permitted."
                )

    # Validate host
    host = config.get('host', '')
    if host:
        if not re.match(r'^[a-zA-Z0-9\.\-_]+$', host):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid host format: '{host}'. Hostnames can only contain letters, numbers, dots, hyphens, and underscores."
            )

    # Validate port
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


def validate_dataframe(df: pd.DataFrame) -> bool:
    """Validate dataframe for security and acceptability."""
    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many rows. Maximum is {MAX_ROWS}"
        )

    for col in df.columns:
        if df[col].dtype == 'object':
            max_len = df[col].astype(str).str.len().max()
            if max_len > 10000:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column '{col}' contains suspiciously long strings"
                )

    return True


def deep_clean_for_json(obj: Any) -> Any:
    """Recursively clean data for JSON serialization."""
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
        except Exception:
            return None


def convert_to_native(obj: Any) -> Any:
    """Convert numpy/pandas types to Python native types."""
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


__all__ = [
    'MAX_FILE_SIZE',
    'MAX_ROWS',
    'MAX_QUERY_LENGTH',
    'DANGEROUS_SQL_KEYWORDS',
    'sanitize_for_json',
    'validate_database_config',
    'validate_dataframe',
    'deep_clean_for_json',
    'convert_to_native',
]