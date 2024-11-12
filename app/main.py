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

# Cached utility functions
@st.cache_data
def get_search_mode_options():
    """Cached function for search mode options."""
    return ["Single Company", "Batch Processing"]

@st.cache_data
def get_query_templates():
    """Cached function for query templates."""
    return [
        "Find detailed information about {entity} including contacts, location, and description",
        "Get company information and social media profiles for {entity}",
        "Find all contact details and business information for {entity}",
        "Get complete profile including headquarters, contacts, and key details for {entity}"
    ]

@st.cache_data
def get_column_keywords():
    """Cached function for column keywords."""
    return ['company', 'entity', 'name', 'organization', 'business']

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
    defaults = {
        'processing': False,
        'results': None,
        'loaded_data': None,
        'search_mode': None,
        'selected_column': None,
        'query_template': None,
        'export_status': None,
        'export_sheet_id': None,
        'max_results': 5,
        'batch_size': 10,
        'settings_initialized': False,
        'last_uploaded_file': None,
        'last_sheet_id': None
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

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
        """Set up the Streamlit page with settings in sidebar."""
        st.set_page_config(page_title="AI Information Extractor", layout="wide")
        st.title("AI Information Extractor")
        
        # Sidebar settings using forms to prevent auto-refresh
        with st.sidebar:
            st.header("Settings")
            with st.form(key="settings_form"):
                max_results = st.number_input(
                    "Results per search",
                    min_value=1,
                    max_value=20,
                    value=st.session_state.max_results
                )
                batch_size = st.number_input(
                    "Batch size",
                    min_value=1,
                    max_value=100,
                    value=st.session_state.batch_size
                )
                submit_button = st.form_submit_button("Apply Settings")
                
                if submit_button:
                    st.session_state.max_results = max_results
                    st.session_state.batch_size = batch_size
                    st.session_state.settings_initialized = True
            
            st.markdown("---")
            st.markdown("""
            ### Instructions:
            1. Choose search mode
            2. Enter company or upload file
            3. Configure search query
            4. Process and view results
            """)

    def search_mode_selection(self):
        """Select search mode with improved state management."""
        if 'search_mode' not in st.session_state:
            st.session_state.search_mode = None

        # Use cached options
        mode_options = get_search_mode_options()
        
        # If mode is already selected, use it as the default index
        default_index = 0
        if st.session_state.search_mode is not None:
            default_index = mode_options.index(st.session_state.search_mode)

        mode = st.radio(
            "Choose search mode:",
            mode_options,
            key="search_mode_radio",
            index=default_index
        )

        if mode != st.session_state.search_mode:
            # Clear related state when mode changes
            st.session_state.search_mode = mode
            st.session_state.loaded_data = None
            st.session_state.selected_column = None
            st.session_state.results = None
            st.session_state.query_template = None

        return mode

    def single_company_input(self):
        """Handle single company input with form."""
        st.header("1. Company Input")
        with st.form(key="company_form"):
            company_name = st.text_input("Enter company name:", placeholder="e.g., Google")
            submit = st.form_submit_button("Submit")
            
            if submit and company_name:
                return pd.DataFrame({'entity_name': [company_name]})
        return None
    
    async def file_upload_section(self):
        """Handle file upload with improved state management."""
        st.header("1. Data Input")
        
        data_source = st.radio(
            "Choose data source:",
            ["Upload CSV", "Google Sheets"],
            key="data_source"
        )
        
        try:
            if data_source == "Upload CSV":
                uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
                if uploaded_file and (
                    'last_uploaded_file' not in st.session_state or 
                    st.session_state.last_uploaded_file != uploaded_file.name
                ):
                    df = pd.read_csv(uploaded_file)
                    st.session_state.loaded_data = df
                    st.session_state.last_uploaded_file = uploaded_file.name
                    st.success("✅ File uploaded successfully!")
            else:
                with st.form(key="sheets_form"):
                    sheet_id = st.text_input("Enter Google Sheet ID")
                    submit = st.form_submit_button("Connect")
                    
                    if submit and sheet_id and sheet_id != st.session_state.get('last_sheet_id'):
                        with st.spinner("Connecting to Google Sheets..."):
                            sheet_data = await self.sheets_service.get_sheet_data(sheet_id)
                            df = pd.DataFrame(sheet_data)
                            st.session_state.loaded_data = df
                            st.session_state.last_sheet_id = sheet_id
                            st.success("✅ Google Sheet connected!")
                
            if st.session_state.get('loaded_data') is not None:
                st.write("Preview:")
                st.dataframe(st.session_state.loaded_data.head())
                return st.session_state.loaded_data
                    
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return None
            
        return None

    def column_selection(self, df: Optional[pd.DataFrame]) -> Optional[str]:
        """Select column with cached keywords."""
        if df is not None and not df.empty:
            st.header("2. Column Selection")
            
            if len(df.columns) == 1:
                st.session_state.selected_column = df.columns[0]
                return df.columns[0]
            
            if st.session_state.selected_column is None:
                with st.form(key="column_form"):
                    # Use cached keywords
                    keywords = get_column_keywords()
                    likely_columns = [
                        col for col in df.columns if any(
                            keyword in col.lower() 
                            for keyword in keywords
                        )
                    ]
                    
                    column_options = likely_columns + [
                        col for col in df.columns 
                        if col not in likely_columns
                    ]
                    
                    selected_column = st.selectbox(
                        "Select the column containing entities:",
                        column_options,
                        index=0 if likely_columns else 0
                    )
                    
                    submit = st.form_submit_button("Confirm Column")
                    if submit:
                        st.session_state.selected_column = selected_column
            
            if st.session_state.selected_column:
                st.write("Sample entities:")
                st.write(df[st.session_state.selected_column].head().tolist())
            
            return st.session_state.selected_column
        return None

    def query_configuration(self):
        """Configure query with cached templates."""
        st.header("3. Query Configuration")
        
        if st.session_state.query_template is None:
            with st.form(key="query_form"):
                query_type = st.radio(
                    "Choose query type:",
                    ["Use Template", "Custom Query"]
                )
                
                if query_type == "Use Template":
                    # Use cached templates
                    templates = get_query_templates()
                    template = st.selectbox(
                        "Select template:",
                        templates
                    )
                else:
                    template = st.text_area(
                        "Enter custom query:",
                        "Find the {field} of {entity}",
                        help="Use {entity} as placeholder"
                    )
                
                submit = st.form_submit_button("Confirm Query")
                if submit:
                    st.session_state.query_template = template
                    
        return st.session_state.query_template

    async def process_single_company(self, company_name: str, query: str):
        """Process a single company with progress tracking."""
        try:
            status_container = st.empty()
            status_container.info(f"Processing: {company_name}")
            
            # Search
            search_results = await self.search_service.search(
                query.replace("{entity}", company_name),
                max_results=st.session_state.max_results
            )
            
            # Extract information
            info = await self.llm_service.extract_information(
                search_results,
                company_name
            )
            
            # Verify information
            verified_info = await self.llm_service.verify_information(info)
            
            status_container.success(f"✅ Processed: {company_name}")
            
            return pd.DataFrame([{
                "Entity": company_name,
                **verified_info.model_dump()
            }])
            
        except Exception as e:
            status_container.error(f"Error processing {company_name}: {str(e)}")
            return pd.DataFrame([{
                "Entity": company_name,
                "error": str(e)
            }])

    async def process_data(self, df: pd.DataFrame, column: str, query: str):
        """Process data with improved progress tracking and error handling."""
        if st.button("Process Data", disabled=st.session_state.processing):
            try:
                st.session_state.processing = True
                
                # Check if it's a single company
                if len(df) == 1:
                    results_df = await self.process_single_company(
                        df[column].iloc[0],
                        query
                    )
                else:
                    # Batch processing
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_container = st.container()
                    
                    results = []
                    total = len(df)
                    batch_size = st.session_state.batch_size
                    
                    for i in range(0, total, batch_size):
                        batch = df[i:i + batch_size]
                        status_text.text(f"Processing batch {i//batch_size + 1}/{(total-1)//batch_size + 1}")
                        
                        tasks = [
                            self.process_single_company(
                                str(entity),
                                query.replace("{entity}", str(entity))
                            )
                            for entity in batch[column]
                        ]
                        
                        batch_results = await asyncio.gather(*tasks)
                        results.extend([df for df in batch_results if df is not None])
                        
                        progress_bar.progress(min((i + batch_size) / total, 1.0))
                        
                        # Show intermediate results
                        if results:
                            with results_container:
                                st.write("Latest results:")
                                st.dataframe(pd.concat(results, ignore_index=True).tail())
                    
                    results_df = pd.concat(results, ignore_index=True)
                
                st.session_state.results = results_df
                st.session_state.processing = False
                
                # Show export options
                await self.show_export_options(results_df)
                
            except Exception as e:
                st.error(f"Error during processing: {str(e)}")
                st.session_state.processing = False
                
    async def show_export_options(self, results_df: pd.DataFrame):
        """Show and handle export options."""
        st.header("4. Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Download as CSV
            csv = results_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="extracted_data.csv",
                mime="text/csv"
            )
        
        with col2:
            # Export to Google Sheets
            await self.export_to_sheets(results_df)

    async def export_to_sheets(self, df: pd.DataFrame):
        """Handle Google Sheets export with proper state management."""
        if st.session_state.export_status != "processing":
            try:
                # Create container for export status
                export_container = st.empty()
                
                # Initialize export
                st.session_state.export_status = "processing"
                export_container.info("🔄 Exporting to Google Sheets...")
                
                # Export data
                sheet_id = await self.sheets_service.export_to_sheets(df)
                
                # Update status and show success message
                export_container.success("✅ Data exported successfully!")
                
                # Show link to sheet
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                st.markdown(f"📊 [Open Google Sheet]({sheet_url})")
                
                # Reset status
                st.session_state.export_status = None
                st.session_state.export_sheet_id = sheet_id
                
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
                st.session_state.export_status = None

async def main():
    """Main application flow."""
    try:
        # Check environment variables first
        check_environment()
        
        # Initialize application state
        init_session_state()
        
        # Create application instance
        app = AIAgentUI()
        
        # Setup page
        app.setup_page()
        
        # Main workflow
        search_mode = app.search_mode_selection()
        
        if search_mode == "Single Company":
            df = app.single_company_input()
        else:
            df = await app.file_upload_section()
        
        if df is not None:
            selected_column = app.column_selection(df)
            if selected_column:
                query = app.query_configuration()
                if query:
                    await app.process_data(df, selected_column, query)
    
    except Exception as e:
        st.error("An unexpected error occurred!")
        st.error(f"Error details: {str(e)}")
        if st.checkbox("Show detailed error trace"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())