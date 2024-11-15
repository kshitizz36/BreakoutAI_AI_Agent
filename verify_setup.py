import os
import sys
from pathlib import Path

# Adding the project root to Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from dotenv import load_dotenv
import json
import asyncio
import pandas as pd
from app.services.google_sheets import GoogleSheetsService  # Updated import path

async def verify_setup():
    # Loading environment variables
    load_dotenv()
    
    # 1. Check credentials file
    creds_path = os.getenv('GOOGLE_CREDENTIALS_FILE')
    print(f"\n1. Checking credentials file...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Credentials path from env: {creds_path}")
    
    # Adjust credentials path to be relative to project root
    abs_creds_path = current_dir / creds_path
    print(f"Absolute credentials path: {abs_creds_path}")
    
    if not abs_creds_path.exists():
        print("❌ Credentials file not found!")
        print("Expected location:", abs_creds_path)
        return False
        
    # 2. Verify credentials content
    print("\n2. Verifying credentials content...")
    try:
        with open(abs_creds_path) as f:
            creds = json.load(f)
            print(f"✓ Service account email: {creds.get('client_email')}")
            print(f"✓ Project ID: {creds.get('project_id')}")
    except Exception as e:
        print(f"❌ Error reading credentials: {str(e)}")
        return False
    
    # 3. Test Google Sheets connection
    print("\n3. Testing Google Sheets connection...")
    try:
        # Initialize service
        sheets_service = GoogleSheetsService()
        
        # Create test data
        test_df = pd.DataFrame({
            'Test': ['Data1', 'Data2'],
            'Value': [100, 200]
        })
        
        # Create sheet
        print("Creating test spreadsheet...")
        sheet_id = await sheets_service.export_to_sheets(
            df=test_df,
            sheet_title=f"Verification Test {pd.Timestamp.now()}"
        )
        
        print(f"\n✅ Success! Spreadsheet created.")
        print(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing connection: {str(e)}")
        print("Full error:")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Starting verification...")
    print(f"Project root: {current_dir}")
    
    # Print Python path for debugging
    print("\nPython path:")
    for p in sys.path:
        print(f"- {p}")
    
    success = asyncio.run(verify_setup())
    
    if success:
        print("\n✅ All checks passed! Your setup is working correctly.")
    else:
        print("\n❌ Some checks failed. Please review the errors above.")
