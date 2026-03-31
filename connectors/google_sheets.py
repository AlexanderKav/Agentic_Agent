# connectors/google_sheets.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import pandas as pd
from dotenv import load_dotenv
import math
import numpy as np
import json

load_dotenv()
# Add at top
from app.services.secrets_manager import get_secrets_manager

def _get_credentials(self):
    """Get credentials from secrets manager"""
    secrets = get_secrets_manager()
    
    # Try to get from secrets manager first
    creds_json = secrets.get('GOOGLE_CREDENTIALS')
    
    if creds_json:
        creds_info = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=self.SCOPES
        )
    else:
        # Fallback to file for backward compatibility
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            raise ValueError("Google credentials not found in secrets manager or env")
        return service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=self.SCOPES
        )
class GoogleSheetsConnector:
    # Use read-only scope to limit what we can do
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self, sheet_id: str, sheet_range: str = "A1:Z1000"):
        self.sheet_id = sheet_id
        self.sheet_range = sheet_range
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.service = self._connect_to_sheets()
        self.has_write_access = None
        self.sheet_title = None

    def _connect_to_sheets(self):
        """Connect to Google Sheets with read-only credentials"""
        if not self.creds_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        
        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(f"Credentials file not found: {self.creds_path}")
        
        try:
            # Use read-only scopes
            creds = service_account.Credentials.from_service_account_file(
                self.creds_path, 
                scopes=self.SCOPES
            )
            service = build('sheets', 'v4', credentials=creds)
            return service.spreadsheets()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Google Sheets API: {str(e)}")

    def _check_permissions(self):
        """Check if the service account has proper read access and detect write access"""
        try:
            # Get spreadsheet metadata - this works with both Viewer and Editor
            spreadsheet = self.service.get(spreadsheetId=self.sheet_id).execute()
            self.sheet_title = spreadsheet.get('properties', {}).get('title', 'Unknown')
            print(f"✅ Connected to sheet: {self.sheet_title}")
            
            # Try a different approach to detect write access
            # Attempt to get the spreadsheet's developer metadata (requires edit permissions)
            try:
                # Try to get developer metadata - this requires edit access
                metadata = self.service.developerMetadata().get(
                    spreadsheetId=self.sheet_id,
                    metadataId=1  # Try to get any metadata (will fail if no edit access)
                ).execute()
                # If we get here, we have edit access
                self.has_write_access = True
                print("⚠️ WARNING: Service account has EDITOR (write) access!")
            except HttpError as e:
                # If we get a 403 error, we don't have edit access
                if e.resp.status == 403:
                    self.has_write_access = False
                    print("✅ Service account has VIEWER (read-only) access")
                elif e.resp.status == 404:
                    # 404 means no metadata found, but we might still have edit access
                    # Try a different test
                    self._test_write_access_via_batch_update()
                else:
                    # Re-raise other errors
                    raise
                    
        except HttpError as e:
            if e.resp.status == 403:
                raise PermissionError(
                    f"Access denied. Please share your Google Sheet with the service account email "
                    f"and give it at least 'Viewer' (read-only) access.\n"
                    f"Sheet ID: {self.sheet_id}"
                )
            elif e.resp.status == 404:
                raise ValueError(f"Sheet not found. Please check the Sheet ID: {self.sheet_id}")
            raise
        
        return self.sheet_title

    def _test_write_access_via_batch_update(self):
        """Test write access using a batch update (won't actually modify anything)"""
        try:
            # Create a harmless batch update request that doesn't actually change anything
            # This tests if we have write permissions without making changes
            body = {
                'requests': [
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': 0,
                                'startRowIndex': 0,
                                'endRowIndex': 0,
                                'startColumnIndex': 0,
                                'endColumnIndex': 1
                            },
                            'cell': {
                                'userEnteredValue': None
                            },
                            'fields': 'userEnteredValue'
                        }
                    }
                ]
            }
            # This will fail if we don't have write access
            self.service.batchUpdate(
                spreadsheetId=self.sheet_id,
                body=body
            ).execute()
            # If we get here, we have write access
            self.has_write_access = True
            print("⚠️ WARNING: Service account has EDITOR (write) access!")
        except HttpError as e:
            if e.resp.status == 403:
                self.has_write_access = False
                print("✅ Service account has VIEWER (read-only) access")
            else:
                # If we can't determine, assume read-only
                self.has_write_access = False
                print("✅ Assuming VIEWER (read-only) access")

    def _test_read_access(self):
        """Simple test to verify read access"""
        try:
            # Try to read a small range
            self.service.values().get(
                spreadsheetId=self.sheet_id,
                range="A1:A1"
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 403:
                return False
            raise

    def fetch_sheet(self) -> pd.DataFrame:
        """Fetch sheet data with read-only permissions"""
        try:
            # First check permissions
            self._check_permissions()
            print(f"📊 Fetching data from sheet: {self.sheet_title}")
            print(f"📍 Range: {self.sheet_range}")
            
            # Fetch the data
            result = self.service.values().get(
                spreadsheetId=self.sheet_id,
                range=self.sheet_range
            ).execute()

            values = result.get('values', [])

            if not values:
                print("⚠️ No data found in sheet.")
                return pd.DataFrame()

            headers = values[0]
            data = values[1:]

            # Normalize row lengths
            normalized_data = []
            for row in data:
                if len(row) < len(headers):
                    row = row + [None] * (len(headers) - len(row))
                
                # Convert empty strings to None and try to convert numbers
                cleaned_row = []
                for cell in row:
                    if cell == '' or cell is None:
                        cleaned_row.append(None)
                    else:
                        # Try to convert to number if possible
                        try:
                            if isinstance(cell, str):
                                # Remove currency symbols and commas
                                cleaned = cell.replace('$', '').replace(',', '').strip()
                                if cleaned.replace('.', '').replace('-', '').isdigit():
                                    cleaned_row.append(float(cleaned))
                                else:
                                    cleaned_row.append(cell)
                            else:
                                cleaned_row.append(cell)
                        except:
                            cleaned_row.append(cell)
                normalized_data.append(cleaned_row)

            df = pd.DataFrame(normalized_data, columns=headers)
            
            # Replace NaN/Inf with None in the entire DataFrame
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.where(pd.notnull(df), None)
            
            print(f"✅ Loaded {len(df)} rows with {len(headers)} columns")
            
            return df
            
        except HttpError as e:
            if e.resp.status == 403:
                raise PermissionError(
                    "Access denied. Please ensure you've shared your Google Sheet with the service account email "
                    "and given it at least 'Viewer' (read-only) access.\n\n"
                    "1. Open your Google Sheet\n"
                    "2. Click 'Share'\n"
                    "3. Add the service account email\n"
                    "4. Choose 'Viewer' (recommended) or 'Editor'\n"
                    "5. Click 'Share'"
                )
            elif e.resp.status == 404:
                raise ValueError(f"Sheet not found. Please check the Sheet ID: {self.sheet_id}")
            else:
                raise ConnectionError(f"Google Sheets API error: {str(e)}")
        except Exception as e:
            raise

    def get_permission_warning(self) -> str | None:
        """Return warning if service account has write access"""
        if self.has_write_access:
            return "⚠️ Your service account has EDITOR (write) access to this sheet. For security, consider changing to 'Viewer' (read-only) access."
        return None
    
    def get_permission_status(self) -> str:
        """Return the permission status as a string"""
        if self.has_write_access is True:
            return "editor"
        elif self.has_write_access is False:
            return "viewer"
        else:
            return "unknown"