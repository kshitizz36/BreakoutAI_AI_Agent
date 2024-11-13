# AI Information Extractor

An AI agent that automates web-based information extraction for entities in datasets. This tool leverages LLM technology to process and structure data from web searches, making information gathering efficient .

## 🚀 Project Overview

This tool enables users to:
- Upload CSV files or connect Google Sheets for data input
- Select target columns for entity identification
- Configure custom search queries
- Extract structured information using AI
- Export results to CSV or Google Sheets
- Process both single entities and batch data

## ✨ Key Features

### Data Input & Processing
- CSV file upload with drag-and-drop support
- Google Sheets integration for direct data access
- Real-time data preview and validation
- Column selection for entity identification

### Query Configuration
- Pre-built query templates for common use cases
- Custom query builder with dynamic placeholders
- Multi-field extraction support
- Batch processing capabilities

### Information Extraction
- Automated web searching via SerpAPI
- AI-powered information parsing using Groq
- Structured data extraction
- Error handling and retry mechanisms

### Results Management
- Interactive results display
- CSV export functionality
- Google Sheets integration with:
  - Public/private access control
  - Real-time updates
  - Formatted output

## 🛠 Technical Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.9+
- **Data Processing**: Pandas
- **Web Search**: SerpAPI
- **LLM Integration**: Groq API
- **Cloud Integration**: Google Sheets & Drive APIs

## 📋 Prerequisites

- Python 3.9+
- Google Cloud Platform account (for APIs)
- SerpAPI account
- Groq API account

## 🔧 Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/BreakoutAI_AI_Agent.git
cd BreakoutAI_AI_Agent
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

Required Environment Variables:
- `SERPAPI_KEY`: Your SerpAPI key
- `GROQ_API_KEY`: Your Groq API key
- `GOOGLE_CREDENTIALS_FILE`: Path to Google credentials JSON

## 🚦 Usage Guide

### Starting the Application
```bash
streamlit run app/main.py
```

### Single Entity Search
1. Select "Single Company" mode
2. Enter the company name
3. Choose or customize search query
4. View and export results

### Batch Processing
1. Upload CSV file or connect Google Sheet
2. Select entity column
3. Configure search parameters
4. Monitor processing progress
5. Export results

### Google Sheets Integration
1. Enable APIs in Google Cloud Console
2. Download service account credentials
3. Place in credentials folder
4. Configure environment variables

## 🎯 Features Overview

### Core Features
- [x] CSV and Google Sheets support
- [x] Dynamic query templates
- [x] Web search integration
- [x] LLM-powered extraction
- [x] Results export options

### Advanced Features
- [x] Single entity processing
- [x] Multi-field extraction
- [x] Rate limiting & error handling
- [x] Progress monitoring
- [x] Data validation

## 🔒 Security Notes

- API keys and credentials are stored in environment variables
- Google credentials are secured in a dedicated directory
- Rate limiting implemented for API calls
- Error handling for failed requests

## 📊 Error Handling

The application includes robust error handling for:
- API rate limits
- Failed search retry mechanisms
- LLM processing errors
- File upload issues
- Data validation failures

## 🎥 Demo

[Watch the demo video](your-loom-video-link-here)

## 🌟 Acknowledgments

- [Breakout Consultancy Private Limited](https://www.breakoutinvesting.in)
- [SerpAPI](https://serpapi.com)
- [Groq](https://www.groq.com)
- [Streamlit](https://streamlit.io)
