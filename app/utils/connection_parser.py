# app/utils/connection_parser.py
import re
from typing import Any, Optional
from urllib.parse import urlparse


def parse_connection_string(connection_string: str) -> dict[str, Any]:
    """
    Parse various database connection string formats.
    
    Supported formats:
    - PostgreSQL: postgresql://user:pass@host:port/db
    - MySQL: mysql://user:pass@host:port/db
    - SQLite: sqlite:///path/to/db.sqlite
    - Environment variables: DB_TYPE=postgresql DB_HOST=localhost DB_PORT=5432 DB_NAME=mydb
    """
    if not connection_string or not isinstance(connection_string, str):
        raise ValueError("Connection string must be a non-empty string")
    
    connection_string = connection_string.strip()
    
    # PostgreSQL format: postgresql://user:pass@host:port/db
    if connection_string.startswith('postgresql://'):
        parsed = urlparse(connection_string)
        return {
            'type': 'postgresql',
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'username': parsed.username,
            'password': parsed.password,
            'ssl': parsed.query == 'sslmode=require'
        }

    # MySQL format: mysql://user:pass@host:port/db
    elif connection_string.startswith('mysql://'):
        parsed = urlparse(connection_string)
        return {
            'type': 'mysql',
            'host': parsed.hostname,
            'port': parsed.port or 3306,
            'database': parsed.path.lstrip('/'),
            'username': parsed.username,
            'password': parsed.password,
            'ssl': False
        }

    # SQLite format: sqlite:///path/to/db.sqlite
    elif connection_string.startswith('sqlite://'):
        parsed = urlparse(connection_string)
        return {
            'type': 'sqlite',
            'host': None,
            'port': None,
            'database': parsed.path,
            'username': None,
            'password': None,
            'ssl': False
        }

    # Environment variable format: DB_TYPE=postgresql DB_HOST=localhost ...
    elif 'DB_HOST' in connection_string or 'DB_TYPE' in connection_string:
        # Parse key=value pairs
        pairs = dict(re.findall(r'(\w+)=([^;\n]+)', connection_string))
        
        db_type = pairs.get('DB_TYPE', 'postgresql').lower()
        
        # Validate required fields based on type
        if db_type == 'sqlite':
            if 'DB_NAME' not in pairs:
                raise ValueError("SQLite requires DB_NAME (file path)")
        else:
            if not all(k in pairs for k in ['DB_HOST', 'DB_NAME']):
                raise ValueError(f"Missing required fields for {db_type}. Need DB_HOST and DB_NAME")
        
        result = {
            'type': db_type,
            'host': pairs.get('DB_HOST'),
            'port': int(pairs.get('DB_PORT', 5432 if db_type == 'postgresql' else 3306)),
            'database': pairs.get('DB_NAME'),
            'username': pairs.get('DB_USER'),
            'password': pairs.get('DB_PASSWORD'),
            'ssl': pairs.get('DB_SSL', 'false').lower() == 'true'
        }
        
        # Clean up None values for SQLite
        if db_type == 'sqlite':
            result['host'] = None
            result['port'] = None
            result['username'] = None
            result['password'] = None
        
        return result

    raise ValueError(f"Unsupported connection string format: {connection_string}")


# Optional: Helper function to build a connection string
def build_connection_string(config: dict[str, Any]) -> str:
    """
    Build a connection string from a configuration dictionary.
    
    Args:
        config: Dictionary with keys: type, host, port, database, username, password
        
    Returns:
        Connection string in the appropriate format
    """
    db_type = config.get('type', 'postgresql').lower()
    
    if db_type == 'sqlite':
        return f"sqlite:///{config['database']}"
    
    username = config.get('username', '')
    password = config.get('password', '')
    host = config.get('host', 'localhost')
    port = config.get('port', 5432 if db_type == 'postgresql' else 3306)
    database = config.get('database', '')
    
    auth = f"{username}:{password}@" if username else ""
    
    if db_type == 'postgresql':
        return f"postgresql://{auth}{host}:{port}/{database}"
    elif db_type == 'mysql':
        return f"mysql://{auth}{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


__all__ = ['parse_connection_string', 'build_connection_string']