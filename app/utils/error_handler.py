from typing import Optional, Dict, Any, Callable
from loguru import logger
import traceback
from datetime import datetime
from pydantic import BaseModel
import functools
import asyncio

class ErrorDetail(BaseModel):
    timestamp: datetime
    error_type: str
    message: str
    stack_trace: Optional[str]
    additional_info: Dict[str, Any] = {}

class ErrorHandler:
    def __init__(self):
        logger.add(
            "logs/error.log",
            format="{time} {level} {message}",
            level="ERROR",
            rotation="500 MB"
        )

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorDetail:
        """Handle and log errors with context."""
        try:
            error_detail = ErrorDetail(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                message=str(error),
                stack_trace=traceback.format_exc(),
                additional_info=context or {}
            )
            
            logger.error(
                f"Error: {error_detail.error_type}\n"
                f"Message: {error_detail.message}\n"
                f"Context: {error_detail.additional_info}\n"
                f"Stack Trace: {error_detail.stack_trace}"
            )
            
            return error_detail
            
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")
            return ErrorDetail(
                timestamp=datetime.now(),
                error_type="ErrorHandlerFailure",
                message=str(e)
            )
    
    def format_user_message(self, error_detail: ErrorDetail) -> str:
        """Format error message for user display."""
        if error_detail.error_type in ["ValueError", "KeyError"]:
            return f"Invalid input: {error_detail.message}"
        elif error_detail.error_type in ["HttpError", "ConnectionError"]:
            return "Connection failed. Please check your internet connection and try again."
        elif error_detail.error_type == "AuthenticationError":
            return "Authentication failed. Please check your credentials."
        else:
            return "An unexpected error occurred. Please try again later."

    def streamlit_error_handler(self, func: Callable):
        """Decorator to handle errors in Streamlit functions."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except Exception as e:
                error_detail = self.handle_error(e)
                return self.format_user_message(error_detail)
        return wrapper