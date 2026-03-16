"""Unified data loader for all data sources."""

import os
import pandas as pd
from .csv_sheets import CSVConnector
from .google_sheets import GoogleSheetsConnector
from .database_connector import DatabaseConnector

class DataLoader:
    """Unified data loader for CSV, Google Sheets, and Databases"""
    
    def __init__(self):
        self.sources = {
            'csv': self._load_csv,
            'excel': self._load_excel,  # Add this line
            'google_sheets': self._load_sheets,
            'database': self._load_database
        }
    
    def load(self, source_type, source_config):
        """Load data from specified source"""
        if source_type not in self.sources:
            raise ValueError(f"Unknown source type: {source_type}. Use: csv, google_sheets, or database")
        
        loader = self.sources[source_type]
        print(f"Loading data from {source_type}...")
        return loader(source_config)
    
    def _load_csv(self, config):
        """Load from CSV file"""
        if isinstance(config, str):
            # Simple string path
            connector = CSVConnector(config)
        else:
            # Dict with options
            path = config.get('path')
            connector = CSVConnector(path)
        return connector.fetch_data()
    
    def _load_excel(self, config):
        """Load from Excel file"""
        if isinstance(config, str):
            # Simple string path
            from .excel_connector import ExcelConnector  # You'll need this
            connector = ExcelConnector(config)
        else:
            # Dict with options
            path = config.get('path')
            sheet_name = config.get('sheet_name', 0)  # First sheet by default
            from .excel_connector import ExcelConnector
            connector = ExcelConnector(path, sheet_name=sheet_name)
        return connector.fetch_data()
        
    def _load_sheets(self, config):
        """Load from Google Sheets"""
        if isinstance(config, str):
            # Simple sheet ID
            connector = GoogleSheetsConnector(config)
        else:
            # Dict with options
            sheet_id = config.get('sheet_id')
            sheet_range = config.get('range', 'A1:Z1000')
            connector = GoogleSheetsConnector(sheet_id, sheet_range)
        return connector.fetch_sheet()
    
    def _load_database(self, config):
        """Load from database"""
        # config can be connection string or dict with options
        if isinstance(config, str):
            connector = DatabaseConnector(config)
            # Default to fetching all tables? Need query or table name
            raise ValueError("For database, please provide a dict with 'table' or 'query'")
        else:
            connection = config.get('connection_string')
            query = config.get('query')
            table = config.get('table')
            
            connector = DatabaseConnector(connection)
            
            if query:
                return connector.fetch_query(query)
            elif table:
                return connector.fetch_table(table)
            else:
                raise ValueError("Database config must include either 'query' or 'table'")
    
    def load_from_env(self):
        """Load data based on environment variables"""
        source_type = os.getenv('DATA_SOURCE_TYPE', 'csv')
        
        if source_type == 'csv':
            path = os.getenv('CSV_PATH', 'data.csv')
            return self.load('csv', path)
        
        elif source_type == 'google_sheets':
            sheet_id = os.getenv('SHEET_ID')
            if not sheet_id:
                raise ValueError("SHEET_ID environment variable not set")
            return self.load('google_sheets', sheet_id)
        
        elif source_type == 'database':
            conn_string = os.getenv('DB_CONNECTION')
            db_query = os.getenv('DB_QUERY')
            db_table = os.getenv('DB_TABLE')
            
            if not conn_string:
                raise ValueError("DB_CONNECTION environment variable not set")
            
            config = {'connection_string': conn_string}
            if db_query:
                config['query'] = db_query
            elif db_table:
                config['table'] = db_table
            else:
                raise ValueError("Either DB_QUERY or DB_TABLE must be set")
            
            return self.load('database', config)
        
        else:
            raise ValueError(f"Unknown DATA_SOURCE_TYPE: {source_type}")


# Convenience functions for common use cases
def load_csv(path):
    """Quick load CSV"""
    return DataLoader().load('csv', path)

def load_database(conn_string, table=None, query=None):
    """Quick load database"""
    config = {'connection_string': conn_string}
    if table:
        config['table'] = table
    elif query:
        config['query'] = query
    return DataLoader().load('database', config)

def load_sheets(sheet_id):
    """Quick load Google Sheets"""
    return DataLoader().load('google_sheets', sheet_id)