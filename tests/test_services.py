import pytest
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import os
from dotenv import load_dotenv
from pathlib import Path
from app.services.google_sheets import GoogleSheetsService, SheetData
from app.services.search_service import SearchService, SearchResult
from app.services.llm_service import LLMService, ExtractedInformation
import google.oauth2.service_account
from googleapiclient import discovery
from groq import Groq

# Load test environment variables
test_env_path = Path(__file__).parent / '.env.test'
load_dotenv(test_env_path)

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    with patch.dict(os.environ, {
        'SERPAPI_KEY': 'test_key',
        'GROQ_API_KEY': 'test_key',
        'GOOGLE_CREDENTIALS_FILE': 'test_credentials.json'
    }):
        yield

@pytest.mark.asyncio
class TestGoogleSheetsService:
    @pytest.fixture
    def mock_sheets_service(self):
        with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds, \
             patch('googleapiclient.discovery.build', autospec=True) as mock_build:
            
            # Create base mocks
            mock_service = MagicMock()
            mock_spreadsheets = MagicMock()
            mock_values = MagicMock()
            
            # Create mocks for updates
            mock_update_request = MagicMock()
            def update_side_effect(**kwargs):
                mock_update_request.execute.return_value = {}
                return mock_update_request
            mock_values.update.side_effect = update_side_effect
            
            # Create mocks for create
            mock_create_request = MagicMock()
            def create_side_effect(**kwargs):
                mock_create_request.execute.return_value = {'spreadsheetId': 'new_sheet_id'}
                return mock_create_request
            mock_spreadsheets.create.side_effect = create_side_effect
            
            # Setup the method chain
            mock_service.spreadsheets.return_value = mock_spreadsheets
            mock_spreadsheets.values.return_value = mock_values
            mock_build.return_value = mock_service
            
            # Create service instance
            service = GoogleSheetsService()
            service.service = mock_service
            
            return (
                service,
                mock_values.update,
                mock_spreadsheets.create,
                mock_update_request,
                mock_create_request
            )

    async def test_get_sheet_data(self, mock_sheets_service):
        """Test fetching data from Google Sheets."""
        service, _, _, _, _ = mock_sheets_service
        
        # Setup mock response for get
        service.service.spreadsheets().values().get().execute.return_value = {
            'values': [['header1', 'header2'], ['value1', 'value2']]
        }
        
        df = await service.get_sheet_data('dummy_id')
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == ['header1', 'header2']

    async def test_update_sheet(self, mock_sheets_service):
        """Test updating Google Sheets."""
        service, mock_update, _, mock_update_request, _ = mock_sheets_service
        test_values = [['header1', 'header2'], ['value1', 'value2']]
        
        await service.update_sheet('dummy_id', 'A1', test_values)
        
        # Verify update was called with correct parameters
        mock_update.assert_called_once_with(
            spreadsheetId='dummy_id',
            range='A1',
            valueInputOption='RAW',
            body={'values': test_values}
        )
        # Verify execute was called
        mock_update_request.execute.assert_called_once()

    async def test_create_new_sheet(self, mock_sheets_service):
        """Test creating a new Google Sheet."""
        service, _, mock_create, _, mock_create_request = mock_sheets_service
        
        sheet_id = await service.create_new_sheet('Test Sheet')
        
        # Verify create was called with correct parameters
        mock_create.assert_called_once_with(
            body={'properties': {'title': 'Test Sheet'}},
            fields='spreadsheetId'
        )
        # Verify execute was called
        mock_create_request.execute.assert_called_once()
        assert sheet_id == 'new_sheet_id'

@pytest.mark.asyncio
class TestSearchService:
    @pytest.fixture
    def search_service(self, setup_test_env):
        return SearchService()

    async def test_search(self, search_service):
        with patch('serpapi.google_search.GoogleSearch.get_dict') as mock_search:
            mock_search.return_value = {
                'organic_results': [
                    {
                        'title': 'Test Title',
                        'link': 'http://test.com',
                        'snippet': 'Test Snippet',
                        'displayed_link': 'test.com'
                    }
                ]
            }

            results = await search_service.search('test query')
            assert len(results) == 1
            assert results[0].title == 'Test Title'

@pytest.mark.asyncio
class TestLLMService:
    @pytest.fixture
    def llm_service(self, setup_test_env):
        with patch('groq.Groq') as mock_groq:
            service = LLMService()
            mock_completion = Mock()
            mock_completion.choices = [
                Mock(
                    message=Mock(
                        content='{"email": "test@example.com", "location": "Test City"}'
                    )
                )
            ]
            service.client.chat.completions.create = AsyncMock(
                return_value=mock_completion
            )
            return service

    async def test_extract_information(self, llm_service):
        result = await llm_service.extract_information(
            [{'title': 'Test', 'link': 'http://test.com', 'snippet': 'Test'}],
            'test entity'
        )
        
        assert isinstance(result, ExtractedInformation)
        assert result.email == "test@example.com"

    async def test_verify_information(self, llm_service):
        test_info = ExtractedInformation(
            email="test@example.com",
            location="Test City"
        )
        
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(
                message=Mock(
                    content='{"email": "test@example.com", "location": "Test City", "confidence_scores": {"email": 0.9, "location": 0.8}}'
                )
            )
        ]
        llm_service.client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        result = await llm_service.verify_information(test_info)
        assert isinstance(result, ExtractedInformation)
        assert result.email == "test@example.com"
        assert "email" in result.model_dump()['confidence_scores']