
# AI Information Extractor

A powerful AI agent that processes datasets and performs web searches to extract specific information based on user queries.

## Features

- File Upload and Processing
  - CSV file upload support
  - Google Sheets integration
  - Large file handling with chunking
  
- Dynamic Query Input
  - Custom prompt templates
  - Multiple field extraction
  - Batch processing support

- Automated Web Search
  - SerpAPI integration
  - Rate limiting and retry mechanisms
  - Content extraction and cleaning

- LLM-Based Information Extraction
  - Using Groq API
  - Structured data extraction
  - Confidence scoring
  
- Results Management
  - CSV export
  - Google Sheets export
  - Data validation

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/BreakoutAI_AI_Agent.git
cd BreakoutAI_AI_Agent
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys:
# - SERPAPI_KEY
# - GROQ_API_KEY
# - GOOGLE_CREDENTIALS_FILE
```

5. Run the application:
```bash
streamlit run app/main.py
```

## Usage Guide

1. Data Input:
   - Upload a CSV file or connect to Google Sheets
   - Select the column containing entities
   - Preview and validate data

2. Query Configuration:
   - Use pre-made templates or create custom queries
   - Configure extraction parameters
   - Set up batch processing

3. Processing:
   - Monitor progress in real-time
   - View extraction results
   - Export data in desired format

## API Keys Setup

1. SerpAPI:
   - Sign up at https://serpapi.com
   - Get API key from dashboard

2. Groq:
   - Register at https://www.groq.com
   - Generate API key

3. Google Sheets (Optional):
   - Create project in Google Cloud Console
   - Enable Sheets API
   - Download credentials

## Project Structure
```
BreakoutAI_AI_Agent/
├── app/
│   ├── services/        # External service integrations
│   ├── utils/          # Utility functions
│   └── main.py         # Main application
├── tests/              # Test suite
└── credentials/        # API credentials
```

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

## Demo Video

[Link to Loom Video Demonstration]

## Additional Features

- Advanced error handling
- Rate limiting and retry mechanisms
- Data validation and cleaning
- Batch processing support
- Progress monitoring
- Custom query templates

## License

This project is licensed under the MIT License.
