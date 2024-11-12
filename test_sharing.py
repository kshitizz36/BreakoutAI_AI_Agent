import os
import sys
from pathlib import Path
import asyncio
import pandas as pd
from dotenv import load_dotenv

# Add the project root to Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Load environment variables
load_dotenv()

# Import after environment variables are loaded
from app.services.google_sheets import GoogleSheetsService

async def test_sheet_sharing():
    try:
        print("\nChecking environment setup...")
        # Verify credentials path
        creds_path = os.getenv('GOOGLE_CREDENTIALS_FILE')
        if not creds_path:
            print("❌ GOOGLE_CREDENTIALS_FILE not found in environment variables")
            return
            
        abs_creds_path = current_dir / creds_path
        print(f"Looking for credentials at: {abs_creds_path}")
        
        if not abs_creds_path.exists():
            print(f"❌ Credentials file not found at: {abs_creds_path}")
            return

        # Create test data
        print("\nCreating test data...")
        test_data = {
            'Column1': ['Test1', 'Test2', 'Test3'],
            'Column2': [100, 200, 300],
            'Column3': ['A', 'B', 'C']
        }
        df = pd.DataFrame(test_data)
        
        # Initialize service
        print("\nInitializing Google Sheets service...")
        service = GoogleSheetsService()
        
        # Create and share spreadsheet
        print("\nCreating and sharing spreadsheet...")
        sheet_id = await service.export_to_sheets(
            df=df,
            sheet_title="Public Test Sheet",
            make_public=True,
            share_with_email="kshitizyadav69@gmail.com"
        )
        
        print(f"\n✅ Success!")
        print(f"Sheet ID: {sheet_id}")
        print(f"Public URL: https://docs.google.com/spreadsheets/d/{sheet_id}/view")
        print(f"Sheet has been shared with kshitizyadav69@gmail.com")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print("\nFull error trace:")
        print(traceback.format_exc())

if __name__ == "__main__":
    print("Starting Google Sheets sharing test...")
    print(f"Current directory: {current_dir}")
    
    # Verify .env file exists
    env_path = current_dir / ".env"
    if not env_path.exists():
        print(f"❌ .env file not found at: {env_path}")
        sys.exit(1)
    
    # Run the test
    asyncio.run(test_sheet_sharing())