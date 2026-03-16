# connectors/google_sheets.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import pandas as pd
from dotenv import load_dotenv
import math
import numpy as np

load_dotenv()

class GoogleSheetsConnector:
    def __init__(self, sheet_id: str, sheet_range: str = "A1:Z1000"):
        self.sheet_id = sheet_id
        self.sheet_range = sheet_range
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.service = self._connect_to_sheets()

    def _connect_to_sheets(self):
        creds = service_account.Credentials.from_service_account_file(self.creds_path)
        service = build('sheets', 'v4', credentials=creds)
        return service.spreadsheets()

    def fetch_sheet(self) -> pd.DataFrame:
        result = self.service.values().get(
            spreadsheetId=self.sheet_id,
            range=self.sheet_range
        ).execute()

        values = result.get('values', [])

        if not values:
            print("No data found in sheet.")
            return pd.DataFrame()

        headers = values[0]
        data = values[1:]

        # Normalize row lengths
        normalized_data = []
        for row in data:
            if len(row) < len(headers):
                row = row + [None] * (len(headers) - len(row))
            
            # Convert empty strings to None
            cleaned_row = []
            for cell in row:
                if cell == '':
                    cleaned_row.append(None)
                else:
                    # Try to convert to number if possible
                    try:
                        if isinstance(cell, str) and cell.replace('.', '').replace('-', '').isdigit():
                            cleaned_row.append(float(cell))
                        else:
                            cleaned_row.append(cell)
                    except:
                        cleaned_row.append(cell)
            normalized_data.append(cleaned_row)

        df = pd.DataFrame(normalized_data, columns=headers)
        
        # Replace NaN/Inf with None in the entire DataFrame
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.where(pd.notnull(df), None)
        
        return df