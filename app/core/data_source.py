import pandas as pd
import tempfile
import os
from typing import BinaryIO

class DataSourceHandler:
    """Handles file uploads and temporary storage"""
    
    @staticmethod
    async def save_upload_file(upload_file) -> str:
        """Save uploaded file temporarily and return path"""
        try:
            # Create temp file with correct extension
            file_ext = os.path.splitext(upload_file.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                content = await upload_file.read()
                tmp_file.write(content)
                return tmp_file.name
        except Exception as e:
            raise Exception(f"Error saving file: {str(e)}")
    
    @staticmethod
    def read_uploaded_file(file_path: str, file_type: str) -> pd.DataFrame:
        """Read uploaded file into DataFrame"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            print(f"📖 Reading {file_type} file from: {file_path}")
            
            if file_type == 'csv':
                df = pd.read_csv(file_path)
                
            elif file_type == 'xlsx':
                # For .xlsx files, use openpyxl
                print("📊 Using openpyxl engine for .xlsx file")
                df = pd.read_excel(file_path, engine='openpyxl')
                
            elif file_type == 'xls':
                # For older .xls files, use xlrd
                print("📊 Using xlrd engine for .xls file")
                df = pd.read_excel(file_path, engine='xlrd')
                
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            print(f"✅ Successfully read {len(df)} rows and {len(df.columns)} columns")
            return df
            
        except ImportError as e:
            if 'openpyxl' in str(e):
                raise Exception("Please install openpyxl: pip install openpyxl")
            elif 'xlrd' in str(e):
                raise Exception("Please install xlrd: pip install xlrd")
            else:
                raise Exception(f"Missing dependency: {str(e)}")
                
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")