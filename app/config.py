import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = BASE_DIR / "credentials"
LOGS_DIR = BASE_DIR / "logs"

# Create necessary directories
CREDENTIALS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# API Keys and Credentials
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")

# Search Settings
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
BATCH_SEARCH_SIZE = int(os.getenv("BATCH_SEARCH_SIZE", "10"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))

# LLM Settings
LLM_MODEL = "mixtral-8x7b-32768"
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 1000

# Google Sheets Settings
SHEETS_SCOPE = ['https://www.googleapis.com/auth/spreadsheets']

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# Rate Limiting
RATE_LIMIT_CALLS = 100
RATE_LIMIT_PERIOD = 60  # seconds

def validate_config():
    """Validate that all required configuration is present."""
    required_vars = [
        ('SERPAPI_KEY', SERPAPI_KEY),
        ('GROQ_API_KEY', GROQ_API_KEY),
        ('GOOGLE_CREDENTIALS_FILE', GOOGLE_CREDENTIALS_FILE)
    ]
    
    missing_vars = [var[0] for var in required_vars if not var[1]]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Validate configuration on import
validate_config()