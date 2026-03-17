"""Database connector for fetching data from SQL databases."""

import pandas as pd
import os
from sqlalchemy import create_engine, text
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
        conn = DatabaseConnector('sqlite:///path/to/database.db')
        
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

    def create_readonly_connection(self):
        """Create a read-only database connection"""
        if 'postgresql' in self.connection_string:
            # PostgreSQL read-only mode
            self.engine = create_engine(
                self.connection_string,
                connect_args={'options': '-c default_transaction_read_only=on'}
            )
        elif 'mysql' in self.connection_string:
            # MySQL read-only user - create separate user with SELECT only
            pass
    
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
            return f"sqlite:///{database}"
        
        # Build auth part
        auth = f"{username}:{password}@" if username and password else ""
        
        # Add port if specified
        port_part = f":{port}" if port else ""
        
        return f"{db_type}://{auth}{host}{port_part}/{database}"
    
    def connect(self):
        """Establish database connection"""
        try:
            if not self.connection_string:
                raise ValueError("No connection string provided")
            
            self.engine = create_engine(self.connection_string)
            self.connection = self.engine.connect()
            return True
        except SQLAlchemyError as e:
            print(f" Database connection error: {e}")
            return False
    
    def fetch_query(self, query: str, params: dict = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            
        Returns:
            pandas DataFrame with query results
        """
        if not self.engine:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            if params:
                return pd.read_sql_query(text(query), self.engine, params=params)
            else:
                return pd.read_sql_query(text(query), self.engine)
        except SQLAlchemyError as e:
            print(f" Query execution error: {e}")
            print(f"Query: {query}")
            return pd.DataFrame()
    
    def fetch_table(self, table_name: str, schema: str = None) -> pd.DataFrame:
        """
        Fetch entire table as DataFrame.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            pandas DataFrame with table contents
        """
        if not self.engine:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            if schema:
                return pd.read_sql_table(table_name, self.engine, schema=schema)
            else:
                return pd.read_sql_table(table_name, self.engine)
        except SQLAlchemyError as e:
            print(f" Table fetch error: {e}")
            print(f"Table: {table_name}")
            return pd.DataFrame()
    
    def execute_query(self, query: str, params: dict = None):
        """
        Execute a query that doesn't return results (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
        """
        if not self.engine:
            if not self.connect():
                return
        
        try:
            with self.engine.connect() as conn:
                if params:
                    conn.execute(text(query), params)
                else:
                    conn.execute(text(query))
                conn.commit()
        except SQLAlchemyError as e:
            print(f" Query execution error: {e}")
    
    def get_table_names(self) -> list:
        """Get list of all table names in the database"""
        if not self.engine:
            if not self.connect():
                return []
        
        try:
            inspector = sqlalchemy.inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            print(f"❌ Error getting table names: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test if database connection works"""
        try:
            if not self.engine:
                self.connect()
            
            # Try a simple query
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.fetchone()[0] == 1
        except:
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
    

# For backwards compatibility with your main2.py
if __name__ == "__main__":
    # Test the connector
    print("🔌 Testing DatabaseConnector...")
    
    # Test with PostgreSQL (your Docker container)
    conn = DatabaseConnector('postgresql://postgres:testpass@localhost:5432/testdb')
    
    if conn.test_connection():
        print(" Connection successful!")
        
        # Fetch data
        df = conn.fetch_table('sales')
        print(f"\n Fetched {len(df)} rows from 'sales' table:")
        print(df.head())
        
        # Try a custom query
        df_us = conn.fetch_query("SELECT * FROM sales WHERE region = 'US'")
        print(f"\n🇺🇸 US sales: {len(df_us)} rows")
        
        conn.close()
    else:
        print(" Connection failed. Is Docker running?")