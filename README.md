# AI Information Extractor

An advanced AI agent that automates web-based information extraction for entities in datasets. This tool leverages cutting-edge LLM technology to process and structure data from web searches, making information gathering efficient and scalable.

## 🚀 Project Overview

AI Information Extractor is a powerful tool that:
- Processes datasets (CSV/Google Sheets) to identify target entities
- Performs intelligent web searches for each entity
- Uses LLM technology to extract and structure relevant information
- Presents data in an intuitive dashboard interface
- Supports both single-entity and batch processing modes

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
- Automated web searching with rate limiting
- LLM-powered information parsing
- Structured data extraction
- Confidence scoring for extracted information

### Results Management
- Interactive results dashboard
- CSV export functionality
- Google Sheets integration for results
- Detailed error reporting and handling

## 🛠 Technical Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Data Processing**: Pandas
- **Web Search**: SerpAPI
- **LLM Integration**: Groq API
- **Cloud Integration**: Google Sheets API

## 📋 Prerequisites

- Python 3.9+
- Google Cloud Platform account (for Sheets API)
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
1. Enable Google Sheets API in GCP
2. Download credentials JSON
3. Set up environment variables
4. Use sheet ID for data import/export

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
- Failed searches
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
