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
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
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
        """Initialize the Google Sheets service with retry logic."""
        try:
            self.service = build(
                'sheets', 
                'v4', 
                credentials=self.credentials,
                cache_discovery=False
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_sheet_data(self, spreadsheet_id: str, range_name: str = 'A1:Z1000') -> pd.DataFrame:
        """Fetch data from Google Sheets with improved error handling."""
        try:
            # Validate spreadsheet ID
            if not spreadsheet_id or not isinstance(spreadsheet_id, str):
                raise ValueError("Invalid spreadsheet ID")

            # Fetch data with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.service.spreadsheets().values().get(
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
                
            # Create DataFrame with proper column handling
            df = pd.DataFrame(values[1:], columns=values[0])
            
            # Clean the DataFrame
            df = df.replace('', pd.NA)
            df = df.dropna(how='all')
            
            return df
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching sheet data: {spreadsheet_id}")
            raise TimeoutError("Request to Google Sheets timed out")
        except Exception as e:
            logger.error(f"Failed to fetch sheet data: {str(e)}")
            raise

    async def export_to_sheets(self, df: pd.DataFrame, sheet_title: Optional[str] = None) -> str:
        """Export DataFrame to a new Google Sheet with proper error handling and formatting."""
        try:
            if df is None or df.empty:
                raise ValueError("No data to export")

            # Generate sheet title with timestamp
            sheet_title = sheet_title or f"AI Agent Results {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # Create new spreadsheet with optimized settings
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

            # Create spreadsheet with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.service.spreadsheets().create(
                        body=spreadsheet
                    ).execute
                ),
                timeout=30
            )

            sheet_id = response.get('spreadsheetId')
            if not sheet_id:
                raise ValueError("Failed to get spreadsheet ID from response")

            # Prepare data for export
            headers = df.columns.tolist()
            data = df.values.tolist()
            values = [headers] + data

            # Clean and format values
            formatted_values = self._format_values_for_sheets(values)

            # Update sheet with data
            await self._update_sheet_data(sheet_id, formatted_values)

            # Apply formatting
            await self._apply_formatting(sheet_id)

            # Verify data was written correctly
            verification_df = await self.get_sheet_data(sheet_id)
            if len(verification_df) != len(df):
                logger.warning("Data verification showed mismatched row counts")

            return sheet_id

        except Exception as e:
            logger.error(f"Failed to export to sheets: {str(e)}")
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
                    # Clean strings of problematic characters
                    formatted_row.append(str(value).replace('\x00', ''))
            formatted_values.append(formatted_row)
        return formatted_values

    async def _update_sheet_data(self, sheet_id: str, values: List[List[Any]]) -> None:
        """Update sheet with data using batched updates for large datasets."""
        try:
            BATCH_SIZE = 1000  # Maximum rows per update
            for i in range(0, len(values), BATCH_SIZE):
                batch = values[i:i + BATCH_SIZE]
                range_name = f'A{i+1}'
                
                body = {
                    'values': batch,
                    'majorDimension': 'ROWS'
                }

                await asyncio.wait_for(
                    asyncio.to_thread(
                        self.service.spreadsheets().values().update(
                            spreadsheetId=sheet_id,
                            range=range_name,
                            valueInputOption='USER_ENTERED',
                            body=body
                        ).execute
                    ),
                    timeout=30
                )
                
                # Small delay between batches to prevent rate limiting
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to update sheet data: {str(e)}")
            raise

    async def _apply_formatting(self, sheet_id: str) -> None:
        """Apply formatting to the sheet with error handling."""
        try:
            requests = [
                # Header formatting
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
                # Auto-resize columns
                {
                    'autoResizeDimensions': {
                        'dimensions': {
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': 26
                        }
                    }
                },
                # Freeze header row
                {
                    'updateSheetProperties': {
                        'properties': {
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                },
                # Alternate row colors
                {
                    'addBanding': {
                        'bandedRange': {
                            'range': {
                                'startRowIndex': 1
                            },
                            'rowProperties': {
                                'headerColor': {
                                    'red': 0.95,
                                    'green': 0.95,
                                    'blue': 0.95
                                },
                                'firstBandColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 1.0
                                },
                                'secondBandColor': {
                                    'red': 0.95,
                                    'green': 0.95,
                                    'blue': 0.95,
                                    'alpha': 0.1
                                }
                            }
                        }
                    }
                }
            ]

            await asyncio.wait_for(
                asyncio.to_thread(
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body={'requests': requests}
                    ).execute
                ),
                timeout=30
            )

        except Exception as e:
            logger.error(f"Failed to apply formatting: {str(e)}")
            # Don't raise here as formatting is not critical
            logger.warning("Continuing without formatting")