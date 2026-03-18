"""Database connector for fetching data from SQL databases."""

import pandas as pd
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

class DatabaseConnector:
    """
    Connector for SQL databases (PostgreSQL, MySQL, SQLite, etc.)
    
    Examples:
        # PostgreSQL
        conn = DatabaseConnector('postgresql://user:pass@localhost:5432/dbname')
        
        # MySQL
        conn = DatabaseConnector('mysql+pymysql://user:pass@localhost/dbname')
        
        # SQLite
        conn = DatabaseConnector('sqlite:///C:/path/to/database.db?mode=ro&uri=true')
        
        # With query
        df = conn.fetch_query("SELECT * FROM table WHERE date > '2024-01-01'")
        
        # Fetch entire table
        df = conn.fetch_table('table_name')
    """
    
    def __init__(self, connection_string=None, **kwargs):
        """
        Initialize database connector.
        
        Args:
            connection_string: Full SQLAlchemy connection string
                               e.g., 'postgresql://user:pass@localhost:5432/dbname'
            **kwargs: Alternative to pass individual parameters:
                     db_type, host, port, database, username, password
        """
        self.connection_string = connection_string
        self.engine = None
        self.connection = None
        
        # Build connection string from parts if provided
        if not connection_string and kwargs:
            self.connection_string = self._build_connection_string(kwargs)
        
        # Flag to track if this is a SQLite connection
        self.is_sqlite = self.connection_string and 'sqlite' in self.connection_string
        
        # For SQLite, extract and normalize the file path
        if self.is_sqlite:
            # Remove any URI parameters for path extraction
            base_string = self.connection_string.split('?')[0]
            # Handle standard sqlite:/// format
            raw_path = base_string.replace('sqlite:///', '')
            # Normalize path for file system checks
            self.sqlite_path = os.path.normpath(raw_path)
            # Keep forward slashes version for URIs
            self.sqlite_path_uri = self.sqlite_path.replace('\\', '/')
    
    def _check_sqlite_file_exists(self):
        """Check if SQLite file exists before attempting connection"""
        if not self.is_sqlite:
            return True
        
        if not os.path.exists(self.sqlite_path):
            print(f"❌ SQLite file does not exist: {self.sqlite_path}")
            return False
        
        if not os.access(self.sqlite_path, os.R_OK):
            print(f"❌ Cannot read SQLite file: {self.sqlite_path}")
            return False
        
        print(f"✅ SQLite file exists and is readable: {self.sqlite_path}")
        print(f"📏 File size: {os.path.getsize(self.sqlite_path)} bytes")
        return True
    
    def _create_sqlite_engine(self, read_only=True):
        """Create SQLite engine with optional read-only mode"""
        if read_only:
            # Use the working format WITHOUT uri=true
            # From your tests: sqlite:///path?mode=ro works perfectly
            uri = f"sqlite:///{self.sqlite_path_uri}?mode=ro"
            print(f"🔌 Creating read-only SQLite engine: {uri}")
            # Don't pass uri=True in connect_args
            return create_engine(uri, connect_args={'check_same_thread': False})
        else:
            # Regular read-write mode
            conn_str = f"sqlite:///{self.sqlite_path_uri}"
            print(f"🔌 Creating read-write SQLite engine: {conn_str}")
            return create_engine(conn_str, connect_args={'check_same_thread': False})
        
    def _build_connection_string(self, params):
        """Build connection string from individual parameters"""
        db_type = params.get('db_type', 'postgresql')
        username = params.get('username')
        password = params.get('password')
        host = params.get('host', 'localhost')
        port = params.get('port')
        database = params.get('database')
        
        # Handle SQLite specially
        if db_type == 'sqlite':
            # For SQLite, normalize the path
            if database:
                # Convert backslashes to forward slashes for SQLAlchemy
                normalized_path = database.replace('\\', '/')
                return f"sqlite:///{normalized_path}"
            return "sqlite://"
        
        # Build auth part
        auth = f"{username}:{password}@" if username and password else ""
        
        # Add port if specified
        port_part = f":{port}" if port else ""
        
        return f"{db_type}://{auth}{host}{port_part}/{database}"
    
    def connect(self, read_only=True):
        """
        Establish database connection.
        
        Args:
            read_only: For SQLite, open in read-only mode to prevent file creation
        """
        try:
            if not self.connection_string:
                raise ValueError("No connection string provided")
            
            # Special handling for SQLite
            if self.is_sqlite:
                # Check if file exists first
                if not self._check_sqlite_file_exists():
                    return False
                
                # OPTION 2: Use standard engine creation for ALL platforms
                self.engine = self._create_sqlite_engine(read_only=read_only)
            else:
                # For other databases, create engine normally
                self.engine = create_engine(self.connection_string)
            
            self.connection = self.engine.connect()
            return True
        except SQLAlchemyError as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    def fetch_query(self, query: str, params: dict = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.
        """
        if not self.engine:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            # Current:
            if params:
                return pd.read_sql_query(text(query), self.engine, params=params)
            else:
                return pd.read_sql_query(text(query), self.engine)
                
            # If your query contains table names that need quoting,
            # you need to ensure they're quoted in the query string itself
            # This depends on how you build the query
        except SQLAlchemyError as e:
            print(f"❌ Query execution error: {e}")
            print(f"Query: {query}")
            return pd.DataFrame()
    
    def fetch_table(self, table_name: str, schema: str = None) -> pd.DataFrame:
        """
        Fetch entire table as DataFrame.
        """
        if not self.engine:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            # Current:
            if schema:
                return pd.read_sql_table(table_name, self.engine, schema=schema)
            else:
                return pd.read_sql_table(table_name, self.engine)
                
            # Note: pd.read_sql_table handles quoting automatically!
            # No change needed here - pandas does the right thing
        except SQLAlchemyError as e:
            print(f"❌ Table fetch error: {e}")
            print(f"Table: {table_name}")
            return pd.DataFrame()
    
    def execute_query(self, query: str, params: dict = None):
        """
        Execute a query that doesn't return results (INSERT, UPDATE, DELETE).
        
        Note: For SQLite in read-only mode, this will fail.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
        """
        if not self.engine:
            if not self.connect(read_only=False):  # Need write mode for modifications
                return
        
        try:
            with self.engine.connect() as conn:
                if params:
                    conn.execute(text(query), params)
                else:
                    conn.execute(text(query))
                conn.commit()
        except SQLAlchemyError as e:
            print(f"❌ Query execution error: {e}")
    
    def get_table_names(self) -> list:
        """Get list of all table names in the database"""
        if not self.engine:
            if not self.connect():
                return []
        
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            print(f"❌ Error getting table names: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test if database connection works"""
        try:
            if not self.engine:
                if not self.connect():
                    return False
            
            # Try a simple query
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.fetchone()[0] == 1
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.engine:
            self.engine.dispose()
            self.engine = None
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# For testing
if __name__ == "__main__":
    # Test with Windows path
    test_path = r"C:\Users\alexk\Desktop\agentic-analyst\test_files\test_validation.db"
    print(f"🔌 Testing with path: {test_path}")
    
    # Normalize the path for testing
    normalized = test_path.replace('\\', '/')
    conn = DatabaseConnector(f"sqlite:///{normalized}?mode=ro&uri=true")
    
    if conn.test_connection():
        print("✅ Connection successful!")
        
        # Get table names
        tables = conn.get_table_names()
        print(f"📋 Tables found: {tables}")
        
        conn.close()
    else:
        print("❌ Connection failed")