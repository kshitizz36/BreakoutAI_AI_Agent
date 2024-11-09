import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
import asyncio
import nest_asyncio
from typing import Optional, Dict, Any
import traceback
from services.google_sheets import GoogleSheetsService
from services.search_service import SearchService
from services.llm_service import LLMService
from utils.file_handler import FileHandler
from utils.error_handler import ErrorHandler

# Enable nested async support for Streamlit
nest_asyncio.apply()

# Load environment variables
load_dotenv()

def check_environment():
    """Check required environment variables."""
    missing_vars = []
    required_vars = [
        'SERPAPI_KEY',
        'GROQ_API_KEY',
        'GOOGLE_CREDENTIALS_FILE'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.info("Please set up your .env file with the required API keys.")
        st.stop()

def init_session_state():
    """Initialize session state variables."""
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'results' not in st.session_state:
        st.session_state.results = None

class AIAgentUI:
    def __init__(self):
        try:
            self.file_handler = FileHandler()
            self.search_service = SearchService()
            self.llm_service = LLMService()
            self.sheets_service = GoogleSheetsService()
            self.error_handler = ErrorHandler()
        except Exception as e:
            st.error(f"Error initializing services: {str(e)}")
            st.stop()

    def setup_page(self):
        st.set_page_config(page_title="AI Information Extractor", layout="wide")
        st.title("AI Information Extractor")
        
        # Sidebar configuration
        with st.sidebar:
            st.header("Settings")
            st.number_input("Results per search", value=5, key="max_results")
            st.number_input("Batch size", value=10, key="batch_size")
            
            st.markdown("---")
            st.markdown("""
            ### Instructions:
            1. Choose search mode (Single/Batch)
            2. Enter company or upload file
            3. Configure search query
            4. Process and view results
            """)

    def search_mode_selection(self):
        """Select between single company or batch processing."""
        return st.radio(
            "Choose search mode:",
            ["Single Company", "Batch Processing"]
        )

    def single_company_input(self):
        """Input section for single company search."""
        st.header("1. Company Input")
        company_name = st.text_input("Enter company name:", placeholder="e.g., Google")
        
        if company_name:
            return pd.DataFrame({'company_name': [company_name]})
        return None

    def file_upload_section(self):
        st.header("1. Data Input")
        
        data_source = st.radio(
            "Choose data source:",
            ["Upload CSV", "Google Sheets"]
        )
        
        df = None
        try:
            if data_source == "Upload CSV":
                uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
                if uploaded_file:
                    df = pd.read_csv(uploaded_file)
                    st.success("✅ File uploaded successfully!")
            else:
                sheet_id = st.text_input("Enter Google Sheet ID")
                if sheet_id:
                    df = self.sheets_service.get_sheet_data(sheet_id)
                    st.success("✅ Google Sheet connected!")
                    
            if df is not None:
                st.write("Preview:")
                st.dataframe(df.head())
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            
        return df
    
    def column_selection(self, df):
        if df is not None:
            st.header("2. Column Selection")
            
            # If it's a single company, we already know the column
            if len(df.columns) == 1 and 'company_name' in df.columns:
                return 'company_name'
            
            selected_column = st.selectbox(
                "Select the column containing entities:",
                df.columns.tolist()
            )
            
            if selected_column:
                st.write("Sample entities:")
                st.write(df[selected_column].head())
            
            return selected_column
        return None
    
    def query_configuration(self):
        st.header("3. Query Configuration")
        
        query_type = st.radio(
            "Choose query type:",
            ["Use Template", "Custom Query"]
        )
        
        if query_type == "Use Template":
            template = st.selectbox(
                "Select template:",
                [
                    "Find detailed information about {entity} including contacts, location, and description",
                    "Get company information and social media profiles for {entity}",
                    "Find all contact details and business information for {entity}",
                    "Get complete profile including headquarters, contacts, and key details for {entity}"
                ]
            )
            return template
        else:
            query = st.text_area(
                "Enter custom query:",
                "Find the {field} of {entity}",
                help="Use {entity} as placeholder"
            )
            return query

    async def process_single_company(self, company_name: str, query: str):
        """Process a single company."""
        try:
            status_text = st.empty()
            status_text.text(f"Processing: {company_name}")
            
            # Search
            search_results = await self.search_service.search(
                query.replace("{entity}", company_name)
            )
            
            # Extract information
            info = await self.llm_service.extract_information(
                search_results,
                company_name
            )
            
            # Verify information
            verified_info = await self.llm_service.verify_information(info)
            
            # Convert to DataFrame
            result_df = pd.DataFrame([{
                "Entity": company_name,
                **verified_info.model_dump()
            }])
            
            return result_df
            
        except Exception as e:
            st.error(f"Error processing {company_name}: {str(e)}")
            return pd.DataFrame([{
                "Entity": company_name,
                "error": str(e)
            }])

    async def process_data(self, df, column, query):
        if st.button("Process Data", disabled=st.session_state.processing):
            st.session_state.processing = True
            
            try:
                # Check if it's a single company
                if len(df) == 1 and column == 'company_name':
                    results_df = await self.process_single_company(
                        df[column].iloc[0],
                        query
                    )
                else:
                    # Batch processing
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    error_container = st.empty()
                    
                    results = []
                    total = len(df)
                    
                    for idx, entity in enumerate(df[column]):
                        try:
                            status_text.text(f"Processing: {entity} ({idx + 1}/{total})")
                            
                            # Search
                            search_results = await self.search_service.search(
                                query.replace("{entity}", entity)
                            )
                            
                            await asyncio.sleep(2)
                            
                            # Extract information
                            info = await self.llm_service.extract_information(
                                search_results,
                                entity
                            )
                            
                            await asyncio.sleep(2)
                            
                            # Verify information
                            verified_info = await self.llm_service.verify_information(info)
                            
                            results.append({
                                "Entity": entity,
                                **verified_info.model_dump()
                            })
                            
                        except Exception as e:
                            error_msg = str(e)
                            error_container.error(f"Error processing {entity}: {error_msg}")
                            results.append({
                                "Entity": entity,
                                "error": error_msg
                            })
                            await asyncio.sleep(5)
                        
                        progress_bar.progress((idx + 1) / total)
                        await asyncio.sleep(2)
                    
                    results_df = pd.DataFrame(results)
                
                if not results_df.empty:
                    st.session_state.results = results_df
                    self.show_results(results_df)
                
            except Exception as e:
                st.error(f"Error during processing: {str(e)}")
            
            finally:
                st.session_state.processing = False

    def show_results(self, results_df):
        st.header("4. Results")
        
        # Display each field in an organized way
        for index, row in results_df.iterrows():
            with st.expander(f"Details for {row['Entity']}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Basic Information**")
                    st.write(f"Company: {row['Entity']}")
                    st.write(f"Website: {row.get('website', 'N/A')}")
                    st.write(f"Location: {row.get('location', 'N/A')}")
                    st.write(f"Phone: {row.get('phone', 'N/A')}")
                    st.write(f"Email: {row.get('email', 'N/A')}")
                
                with col2:
                    st.write("**Additional Information**")
                    if row.get('description'):
                        st.write("Description:", row['description'])
                    if row.get('social_media'):
                        st.write("Social Media:")
                        for platform, link in row['social_media'].items():
                            st.write(f"- {platform}: {link}")
                    if row.get('additional_info'):
                        st.write("Other Details:")
                        for key, value in row['additional_info'].items():
                            st.write(f"- {key}: {value}")
        
        st.header("5. Export Options")
        
        # Download as CSV
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="extracted_data.csv",
            mime="text/csv"
        )
        
        # Export to Google Sheets
        if st.button("Export to Google Sheets"):
            try:
                sheet_id = self.sheets_service.create_new_sheet("AI Agent Results")
                self.sheets_service.update_sheet(
                    sheet_id,
                    "A1",
                    [results_df.columns.tolist()] + results_df.values.tolist()
                )
                st.success(f"Exported to new sheet! ID: {sheet_id}")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")

async def main():
    # Check environment variables first
    check_environment()
    
    # Initialize application
    init_session_state()
    app = AIAgentUI()
    app.setup_page()
    
    # Select search mode
    search_mode = app.search_mode_selection()
    
    if search_mode == "Single Company":
        df = app.single_company_input()
    else:
        df = app.file_upload_section()
    
    if df is not None:
        selected_column = app.column_selection(df)
        if selected_column:
            query = app.query_configuration()
            await app.process_data(df, selected_column, query)

if __name__ == "__main__":
    asyncio.run(main())