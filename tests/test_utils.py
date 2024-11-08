import pytest
import pandas as pd
from pathlib import Path
import io
import json
from datetime import datetime
from app.utils.file_handler import FileHandler, FileData
from app.utils.error_handler import ErrorHandler, ErrorDetail

@pytest.mark.asyncio
class TestFileHandler:
    @pytest.fixture
    def file_handler(self):
        return FileHandler()

    @pytest.fixture
    def sample_csv_content(self):
        return b"column1,column2\nvalue1,value2\nvalue3,value4"

    async def test_read_file(self, file_handler, tmp_path):
        # Create a temporary CSV file
        file_path = tmp_path / "test.csv"
        file_path.write_bytes(b"column1,column2\nvalue1,value2")

        df = await file_handler.read_file(file_path)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == ['column1', 'column2']

    async def test_validate_file(self, file_handler, sample_csv_content):
        is_valid = await file_handler.validate_file(sample_csv_content, "test.csv")
        assert is_valid

    async def test_invalid_file_format(self, file_handler):
        with pytest.raises(ValueError):
            await file_handler.read_file("invalid.txt")

    async def test_save_results(self, file_handler, tmp_path):
        test_data = [
            {"column1": "value1", "column2": "value2"},
            {"column1": "value3", "column2": "value4"}
        ]
        output_path = tmp_path / "output.csv"
        
        await file_handler.save_results(test_data, output_path)
        
        assert output_path.exists()
        df = pd.read_csv(output_path)
        assert len(df) == 2

    async def test_process_large_file(self, file_handler, tmp_path):
        # Create a large temporary CSV file
        file_path = tmp_path / "large.csv"
        large_content = "column1,column2\n" + "\n".join(f"value{i},value{i}" for i in range(1000))
        file_path.write_text(large_content)

        df = await file_handler.process_large_file(file_path, chunk_size=100)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1000

    async def test_validate_data_quality(self, file_handler):
        test_df = pd.DataFrame({
            'column1': ['value1', 'value2', None],
            'column2': ['value1', 'value1', 'value2']
        })
        
        metrics = await file_handler.validate_data_quality(test_df)
        
        assert 'total_rows' in metrics
        assert 'missing_values' in metrics
        assert 'duplicates' in metrics
        assert metrics['total_rows'] == 3

class TestErrorHandler:
    @pytest.fixture
    def error_handler(self):
        return ErrorHandler()

    def test_handle_error(self, error_handler):
        test_error = ValueError("Test error")
        context = {"test_key": "test_value"}
        
        error_detail = error_handler.handle_error(test_error, context)
        
        assert isinstance(error_detail, ErrorDetail)
        assert error_detail.error_type == "ValueError"
        assert error_detail.message == "Test error"
        assert error_detail.additional_info == context

    def test_format_user_message(self, error_handler):
        test_cases = [
            (
                ErrorDetail(
                    timestamp=datetime.now(),
                    error_type="ValueError",
                    message="Test error",
                    stack_trace=None
                ),
                "Invalid input"
            ),
            (
                ErrorDetail(
                    timestamp=datetime.now(),
                    error_type="HttpError",
                    message="Connection failed",
                    stack_trace=None
                ),
                "Connection failed"
            ),
            (
                ErrorDetail(
                    timestamp=datetime.now(),
                    error_type="AuthenticationError",
                    message="Auth failed",
                    stack_trace=None
                ),
                "Authentication failed"
            )
        ]
        
        for error_detail, expected_message in test_cases:
            message = error_handler.format_user_message(error_detail)
            assert expected_message in message

    def test_error_handler_decorator(self, error_handler):
        @error_handler.streamlit_error_handler
        async def test_function():
            raise ValueError("Test error")
            
        with pytest.raises(Exception):
            asyncio.run(test_function())