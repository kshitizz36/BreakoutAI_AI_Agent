from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from typing import Optional, List, Dict
from loguru import logger
import os
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

class SheetData(BaseModel):
    sheet_id: str
    data: List[List[str]]
    total_rows: int
    total_columns: int

class GoogleSheetsService:
    def __init__(self):
        """Initialize Google Sheets service with credentials."""
        self.logger = logger.add("logs/sheets_service.log", rotation="500 MB")
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials = self._get_credentials()
        self._initialize_service()

    def _get_credentials(self):
        """Get credentials from service account file."""
        creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
        if not creds_file:
            raise ValueError("GOOGLE_CREDENTIALS_FILE not found in environment variables")
            
        try:
            return service_account.Credentials.from_service_account_file(
                creds_file, 
                scopes=self.scopes
            )
        except Exception as e:
            logger.error(f"Failed to initialize credentials: {str(e)}")
            raise

    def _initialize_service(self):
        """Initialize the Google Sheets service."""
        try:
            self.service = build(
                'sheets', 
                'v4', 
                credentials=self.credentials,
                cache_discovery=False
            )
        except Exception as e:
            logger.error(f"Failed to initialize service: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_sheet_data(self, spreadsheet_id: str, range_name: str = 'A1:Z1000') -> pd.DataFrame:
        """Fetch data from Google Sheets and return as DataFrame."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                raise ValueError("No data found in sheet")
                
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
            
        except HttpError as e:
            logger.error(f"Failed to fetch sheet data: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def update_sheet(self, spreadsheet_id: str, range_name: str, values: List[List], 
                   value_input_option: str = 'RAW') -> None:
        """Update Google Sheet with new values."""
        try:
            body = {
                'values': values
            }
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            
        except HttpError as e:
            logger.error(f"Failed to update sheet: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_new_sheet(self, title: str) -> str:
        """Create a new Google Sheet."""
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            response = self.service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            return response.get('spreadsheetId')
            
        except HttpError as e:
            logger.error(f"Failed to create new sheet: {str(e)}")
            raise

    async def format_sheet(self, spreadsheet_id: str) -> None:
        """Apply formatting to the sheet."""
        try:
            requests = [
                {
                    'repeatCell': {
                        'range': {
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 0.9,
                                    'green': 0.9,
                                    'blue': 0.9
                                },
                                'textFormat': {
                                    'bold': True
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                },
                {
                    'autoResizeDimensions': {
                        'dimensions': {
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': 26
                        }
                    }
                }
            ]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
        except HttpError as e:
            logger.error(f"Failed to format sheet: {str(e)}")
            raise