from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from typing import Optional, List, Dict, Any
from loguru import logger
import os
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime
from pathlib import Path

class GoogleSheetsService:
    def __init__(self):
        """Initialize Google Sheets service with credentials."""
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]
        self._setup_logging()
        self.credentials = self._get_credentials()
        self._initialize_service()

    def _setup_logging(self):
        """Set up logging configuration."""
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)
        logger.add(
            "logs/sheets_service.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level="INFO",
            rotation="500 MB",
            retention="30 days"
        )

    def _get_credentials(self):
        """Get credentials from service account file with proper error handling."""
        try:
            creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
            if not creds_file:
                logger.error("GOOGLE_CREDENTIALS_FILE not found in environment variables")
                raise ValueError("Google credentials file not configured")
            
            if not os.path.exists(creds_file):
                logger.error(f"Credentials file not found at: {creds_file}")
                raise FileNotFoundError(f"Credentials file not found: {creds_file}")
                
            return service_account.Credentials.from_service_account_file(
                creds_file, 
                scopes=self.scopes
            )
        except Exception as e:
            logger.error(f"Failed to initialize credentials: {str(e)}")
            raise

    def _initialize_service(self):
        """Initialize the Google Sheets and Drive services with retry logic."""
        try:
            self.sheets_service = build(
                'sheets', 
                'v4', 
                credentials=self.credentials,
                cache_discovery=False
            )
            self.drive_service = build(
                'drive',
                'v3',
                credentials=self.credentials,
                cache_discovery=False
            )
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise

    async def _set_public_access(self, file_id: str) -> None:
        """Set file permissions to be publicly readable."""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader',
                'allowFileDiscovery': False
            }
            await asyncio.wait_for(
                asyncio.to_thread(
                    self.drive_service.permissions().create(
                        fileId=file_id,
                        body=permission,
                        fields='id'
                    ).execute
                ),
                timeout=30
            )
            logger.info(f"Public access set for file {file_id}")
        except Exception as e:
            logger.error(f"Failed to set public access: {str(e)}")
            logger.warning("Continuing without public access")

    async def share_with_user(self, file_id: str, email: str, role: str = 'writer') -> None:
        """Share a file with a specific user."""
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            await asyncio.wait_for(
                asyncio.to_thread(
                    self.drive_service.permissions().create(
                        fileId=file_id,
                        body=permission,
                        sendNotificationEmail=True
                    ).execute
                ),
                timeout=30
            )
            logger.info(f"Sheet shared with {email}")
        except Exception as e:
            logger.error(f"Failed to share with user: {str(e)}")
            logger.warning(f"Continuing without sharing to {email}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_sheet_data(self, spreadsheet_id: str, range_name: str = 'A1:Z1000') -> pd.DataFrame:
        """Fetch data from Google Sheets with improved error handling."""
        try:
            if not spreadsheet_id or not isinstance(spreadsheet_id, str):
                raise ValueError("Invalid spreadsheet ID")

            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.sheets_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=range_name
                    ).execute
                ),
                timeout=30
            )
            
            values = result.get('values', [])
            if not values:
                logger.warning(f"No data found in sheet: {spreadsheet_id}")
                return pd.DataFrame()
                
            df = pd.DataFrame(values[1:], columns=values[0])
            df = df.replace('', pd.NA)
            df = df.dropna(how='all')
            
            return df
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching sheet data: {spreadsheet_id}")
            raise TimeoutError("Request to Google Sheets timed out")
        except Exception as e:
            logger.error(f"Failed to fetch sheet data: {str(e)}")
            raise

    def _format_values_for_sheets(self, values: List[List[Any]]) -> List[List[Any]]:
        """Format values for Google Sheets with proper handling of special cases."""
        formatted_values = []
        for row in values:
            formatted_row = []
            for value in row:
                if value is None:
                    formatted_row.append('')
                elif isinstance(value, (dict, list)):
                    formatted_row.append(str(value))
                elif isinstance(value, (int, float)):
                    formatted_row.append(value)
                else:
                    formatted_row.append(str(value).replace('\x00', ''))
            formatted_values.append(formatted_row)
        return formatted_values

    async def _update_sheet_data(self, sheet_id: str, values: List[List[Any]]) -> None:
        """Update sheet with data using batched updates for large datasets."""
        try:
            BATCH_SIZE = 1000
            for i in range(0, len(values), BATCH_SIZE):
                batch = values[i:i + BATCH_SIZE]
                range_name = f'A{i+1}'
                
                body = {
                    'values': batch,
                    'majorDimension': 'ROWS'
                }

                await asyncio.wait_for(
                    asyncio.to_thread(
                        self.sheets_service.spreadsheets().values().update(
                            spreadsheetId=sheet_id,
                            range=range_name,
                            valueInputOption='USER_ENTERED',
                            body=body
                        ).execute
                    ),
                    timeout=30
                )
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to update sheet data: {str(e)}")
            raise

    async def _apply_formatting(self, sheet_id: str) -> None:
        """Apply formatting to the sheet with error handling."""
        try:
            sheet_metadata = await asyncio.wait_for(
                asyncio.to_thread(
                    self.sheets_service.spreadsheets().get(
                        spreadsheetId=sheet_id
                    ).execute
                ),
                timeout=30
            )
            
            first_sheet_id = sheet_metadata['sheets'][0]['properties']['sheetId']
            
            requests = [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': first_sheet_id,
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
                            'sheetId': first_sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': 26
                        }
                    }
                },
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': first_sheet_id,
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }
            ]

            await asyncio.wait_for(
                asyncio.to_thread(
                    self.sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body={'requests': requests}
                    ).execute
                ),
                timeout=30
            )

        except Exception as e:
            logger.error(f"Failed to apply formatting: {str(e)}")
            logger.warning("Continuing without formatting")

    async def export_to_sheets(
        self, 
        df: pd.DataFrame, 
        sheet_title: Optional[str] = None,
        make_public: bool = True,
        share_with_email: Optional[str] = None
    ) -> str:
        """Export DataFrame to a new Google Sheet with sharing options."""
        try:
            if df is None or df.empty:
                raise ValueError("No data to export")

            sheet_title = sheet_title or f"AI Agent Results {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            spreadsheet = {
                'properties': {
                    'title': sheet_title,
                    'locale': 'en_US',
                    'timeZone': 'UTC'
                },
                'sheets': [{
                    'properties': {
                        'title': 'Sheet1',
                        'gridProperties': {
                            'rowCount': max(1000, len(df) + 10),
                            'columnCount': len(df.columns) + 5,
                            'frozenRowCount': 1
                        }
                    }
                }]
            }

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.sheets_service.spreadsheets().create(
                        body=spreadsheet
                    ).execute
                ),
                timeout=30
            )

            sheet_id = response.get('spreadsheetId')
            if not sheet_id:
                raise ValueError("Failed to get spreadsheet ID from response")

            headers = df.columns.tolist()
            data = df.values.tolist()
            values = [headers] + data
            formatted_values = self._format_values_for_sheets(values)
            await self._update_sheet_data(sheet_id, formatted_values)
            await self._apply_formatting(sheet_id)

            if make_public:
                await self._set_public_access(sheet_id)
            
            if share_with_email:
                await self.share_with_user(sheet_id, share_with_email)

            return sheet_id

        except Exception as e:
            logger.error(f"Failed to export to sheets: {str(e)}")
            raise