from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from typing import Optional, List, Dict, Any
from loguru import logger
import os
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class GoogleSheetsService:
    def __init__(self):
        """Initialize Google Sheets service with credentials."""
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials = self._get_credentials()
        self._initialize_service()
        logger.add("logs/sheets_service.log", rotation="500 MB")

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
            result = await asyncio.to_thread(
                self.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute
            )
            
            values = result.get('values', [])
            if not values:
                raise ValueError("No data found in sheet")
                
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch sheet data: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_new_sheet(self, title: str) -> str:
        """Create a new Google Sheet."""
        try:
            spreadsheet = {
                'properties': {
                    'title': title,
                    'locale': 'en_US',
                    'timeZone': 'UTC'
                },
                'sheets': [{
                    'properties': {
                        'title': 'Sheet1',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 26,
                            'frozenRowCount': 1
                        }
                    }
                }]
            }
            
            response = await asyncio.to_thread(
                self.service.spreadsheets().create(
                    body=spreadsheet
                ).execute
            )
            
            sheet_id = response.get('spreadsheetId')
            if not sheet_id:
                raise ValueError("Failed to get spreadsheet ID from response")
                
            return sheet_id
            
        except Exception as e:
            logger.error(f"Failed to create new sheet: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def update_sheet(self, spreadsheet_id: str, range_name: str, 
                         values: List[List[Any]], value_input_option: str = 'USER_ENTERED') -> None:
        """Update Google Sheet with new values."""
        try:
            # Format values for sheet update
            formatted_values = []
            for row in values:
                formatted_row = []
                for value in row:
                    if value is None:
                        formatted_row.append('')
                    elif isinstance(value, (dict, list)):
                        formatted_row.append(str(value))
                    else:
                        formatted_row.append(value)
                formatted_values.append(formatted_row)

            body = {
                'values': formatted_values,
                'majorDimension': 'ROWS'
            }

            await asyncio.to_thread(
                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body
                ).execute
            )
            
        except Exception as e:
            logger.error(f"Failed to update sheet: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
                                    'red': 0.95,
                                    'green': 0.95,
                                    'blue': 0.95
                                },
                                'textFormat': {
                                    'bold': True,
                                    'fontSize': 11
                                },
                                'verticalAlignment': 'MIDDLE',
                                'horizontalAlignment': 'CENTER',
                                'wrapStrategy': 'WRAP'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,verticalAlignment,horizontalAlignment,wrapStrategy)'
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
                },
                {
                    'updateSheetProperties': {
                        'properties': {
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }
            ]
            
            await asyncio.to_thread(
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute
            )
            
        except Exception as e:
            logger.error(f"Failed to format sheet: {str(e)}")
            raise