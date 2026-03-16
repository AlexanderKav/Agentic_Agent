"""Excel file connector for fetching data."""

import pandas as pd
import os

class ExcelConnector:
    """Simple connector to load data from Excel files."""
    
    def __init__(self, file_path: str, sheet_name=0):
        """
        Initialize Excel connector.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Sheet name or index (default: 0 = first sheet)
        """
        self.file_path = file_path
        self.sheet_name = sheet_name
        
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch data from Excel file.
        
        Returns:
            pandas DataFrame containing the Excel data
            
        Raises:
            FileNotFoundError: If the Excel file doesn't exist
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")
        
        return pd.read_excel(self.file_path, sheet_name=self.sheet_name)
    
    def test_connection(self) -> bool:
        """
        Test if file exists and is readable.
        
        Returns:
            True if file exists and is readable, False otherwise
        """
        return os.path.exists(self.file_path) and os.access(self.file_path, os.R_OK)