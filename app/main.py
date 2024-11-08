import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
from services.google_sheets import GoogleSheetsService
from services.search_service import SearchService
from services.llm_service import LLMService
from utils.file_handler import FileHandler
from utils.error_handler import ErrorHandler

load_dotenv()

class AIAgent:
    def __init__(self):
        self.file_handler = FileHandler()
        self.search_service = SearchService()
        self.llm_service = LLMService()
        self.sheets_service = GoogleSheetsService()
        self.error_handler = ErrorHandler()
        
    def setup_page(self):
        st.set_page_config(
            page_title="AI Information Extractor",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        st.title("AI Information Extractor")
        
        # Add sidebar configuration
        with st.sidebar:
            st.header("Settings")
            st.number_input("Max Results per Search", value=5, key="max_results")
            st.number_input("Batch Size", value=10, key="batch_size")
            
            # Add help section
            st.markdown("---")
            st.markdown("""
            ### How to use:
            1. Upload a CSV file or connect Google Sheet
            2. Select the column with entities
            3. Configure your search query
            4. Process and view results
            """)
        
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
                    st.success("File uploaded successfully!")
            else:
                sheet_id = st.text_input("Enter Google Sheet ID")
                if sheet_id:
                    df = self.sheets_service.get_sheet_data(sheet_id)
                    st.success("Google Sheet connected successfully!")
                    
        except Exception as e:
            error_detail = self.error_handler.handle_error(e)
            st.error(self.error_handler.format_user_message(error_detail))
            
        return df
    
    def column_selection(self, df):
        if df is not None:
            st.header("2. Column Selection")
            
            # Show DataFrame preview
            st.subheader("Data Preview")
            st.dataframe(df.head())
            
            # Column selection
            selected_column = st.selectbox(
                "Select the column containing entities:",
                df.columns.tolist()
            )
            
            if selected_column:
                st.write("Preview of selected column:")
                st.write(df[selected_column].head())
            
            return selected_column
        return None
    
    def query_input(self):
        st.header("3. Query Configuration")
        
        # Template selection
        template_type = st.radio(
            "Choose query type:",
            ["Use Template", "Custom Query"]
        )
        
        if template_type == "Use Template":
            template = st.selectbox(
                "Select a template:",
                [
                    "Find the email address and location of {entity}",
                    "Get company information for {entity}",
                    "Find social media profiles of {entity}",
                    "Get contact details for {entity}"
                ]
            )
            return template
        else:
            query_template = st.text_area(
                "Enter your search query template:",
                "Find the {field} of {entity}",
                help="Use {entity} as a placeholder for each item in your selected column"
            )
            return query_template
    
    async def process_data(self, df, selected_column, query_template):
        if st.button("Process Data"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create expander for detailed progress
            with st.expander("Processing Details", expanded=True):
                details_container = st.empty()
                
            total_rows = len(df)
            for idx, entity in enumerate(df[selected_column]):
                try:
                    status_text.text(f"Processing: {entity}")
                    details = f"Processing entity {idx+1}/{total_rows}: {entity}\n"
                    
                    # Search web for information
                    search_results = await self.search_service.search(
                        query_template.replace("{entity}", entity)
                    )
                    details += "✓ Search completed\n"
                    
                    # Extract information using LLM
                    extracted_info = await self.llm_service.extract_information(
                        search_results,
                        entity
                    )
                    details += "✓ Information extracted\n"
                    
                    # Verify extracted information
                    verified_info = await self.llm_service.verify_information(
                        extracted_info
                    )
                    details += "✓ Information verified\n"
                    
                    results.append({
                        "Entity": entity,
                        **verified_info.dict()
                    })
                    
                    details_container.text(details)
                    progress_bar.progress((idx + 1) / total_rows)
                    
                except Exception as e:
                    error_detail = self.error_handler.handle_error(e)
                    st.error(
                        f"Error processing {entity}: "
                        f"{self.error_handler.format_user_message(error_detail)}"
                    )
                    continue
            
            if results:
                results_df = pd.DataFrame(results)
                st.header("4. Results")
                st.dataframe(results_df)
                
                # Export options
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
                        sheet_id = await self.sheets_service.create_new_sheet(
                            "AI Agent Results"
                        )
                        await self.sheets_service.update_sheet(
                            sheet_id,
                            "A1",
                            [results_df.columns.tolist()] + results_df.values.tolist()
                        )
                        st.success(f"Results exported to new Google Sheet! ID: {sheet_id}")
                    except Exception as e:
                        error_detail = self.error_handler.handle_error(e)
                        st.error(self.error_handler.format_user_message(error_detail))
            
            return results_df

async def main():
    agent = AIAgent()
    agent.setup_page()
    
    df = agent.file_upload_section()
    if df is not None:
        selected_column = agent.column_selection(df)
        if selected_column:
            query_template = agent.query_input()
            results_df = await agent.process_data(df, selected_column, query_template)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())