# connectors/google_sheets.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import pandas as pd
from dotenv import load_dotenv

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
            normalized_data.append(row)

        df = pd.DataFrame(normalized_data, columns=headers)
        return df