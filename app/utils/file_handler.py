import pandas as pd
from typing import Optional, List, Dict, Union
import csv
import io
from loguru import logger
from pathlib import Path
from pydantic import BaseModel
import chardet

try:
    import aiofiles
    ASYNC_SUPPORTED = True
except ImportError:
    ASYNC_SUPPORTED = False
    logger.warning("aiofiles not available, falling back to synchronous operations")

class FileData(BaseModel):
    filename: str
    content_type: str
    size: int
    data: bytes

class FileHandler:
    def __init__(self):
        logger.add("logs/file_handler.log", rotation="500 MB")
        self.supported_extensions = ['.csv', '.xlsx', '.xls']
        self.chunk_size = 1024 * 1024  # 1MB chunks
        
    async def read_file(self, file_path: Union[str, Path]) -> Optional[pd.DataFrame]:
        """Read data from various file formats."""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() not in self.supported_extensions:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            if ASYNC_SUPPORTED:
                async with aiofiles.open(file_path, mode='rb') as file:
                    content = await file.read()
            else:
                with open(file_path, 'rb') as file:
                    content = file.read()
                
            if file_path.suffix.lower() == '.csv':
                # Detect encoding
                encoding = chardet.detect(content)['encoding']
                return pd.read_csv(io.BytesIO(content), encoding=encoding)
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                return pd.read_excel(io.BytesIO(content))
                
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            raise

    async def save_results(self, results: List[Dict], output_path: Union[str, Path], 
                         format: str = 'csv') -> None:
        """Save extraction results to file."""
        try:
            df = pd.DataFrame(results)
            output_path = Path(output_path)
            
            if format.lower() == 'csv':
                csv_data = df.to_csv(index=False, quoting=csv.QUOTE_ALL)
                if ASYNC_SUPPORTED:
                    async with aiofiles.open(output_path, mode='w', newline='') as file:
                        await file.write(csv_data)
                else:
                    with open(output_path, 'w', newline='') as file:
                        file.write(csv_data)
            elif format.lower() == 'xlsx':
                df.to_excel(output_path, index=False)
            else:
                raise ValueError(f"Unsupported output format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to save results to {output_path}: {str(e)}")
            raise

    async def validate_file(self, file_content: bytes, filename: str) -> bool:
        """Validate file content and structure."""
        try:
            suffix = Path(filename).suffix.lower()
            
            if suffix not in self.supported_extensions:
                return False
                
            if suffix == '.csv':
                # Try reading the CSV content
                encoding = chardet.detect(file_content)['encoding']
                pd.read_csv(io.BytesIO(file_content), encoding=encoding)
            elif suffix in ['.xlsx', '.xls']:
                # Try reading the Excel content
                pd.read_excel(io.BytesIO(file_content))
                
            return True
            
        except Exception as e:
            logger.error(f"File validation failed: {str(e)}")
            return False

    async def process_large_file(self, file_path: Union[str, Path], 
                               chunk_size: int = 1000) -> pd.DataFrame:
        """Process large files in chunks."""
        try:
            chunks = []
            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                processed_chunk = await self._process_chunk(chunk)
                chunks.append(processed_chunk)
            
            return pd.concat(chunks, ignore_index=True)
        
        except Exception as e:
            logger.error(f"Failed to process file in chunks: {str(e)}")
            raise
            
    async def _process_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Process a single chunk of data."""
        try:
            # Clean data
            chunk = chunk.replace({'\n': ' ', '\r': ' '})
            
            # Remove duplicates
            chunk = chunk.drop_duplicates()
            
            # Handle missing values
            chunk = chunk.fillna('')
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error processing chunk: {str(e)}")
            raise

    async def validate_data_quality(self, df: pd.DataFrame) -> Dict:
        """Validate data quality and return metrics."""
        try:
            metrics = {
                'total_rows': len(df),
                'missing_values': df.isnull().sum().to_dict(),
                'duplicates': df.duplicated().sum(),
                'column_types': df.dtypes.astype(str).to_dict()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Data quality validation failed: {str(e)}")
            raise