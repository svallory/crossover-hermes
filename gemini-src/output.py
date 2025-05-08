""" {cell}
## Google Sheets Output Integration

This module handles the final output step of the Hermes project: writing the
processed results to a new Google Spreadsheet.

It assumes execution within a **Google Colab environment**, utilizing Colab's
authentication mechanisms (`google.colab.auth`) to gain access to Google Sheets API.

Key functionalities:
-   **Authentication**: Handles authentication for Google Colab users.
-   **Spreadsheet Creation**: Creates a new Google Spreadsheet with a specified name.
-   **Worksheet Setup**: Adds the required worksheets (`email-classification`, `order-status`,
    `order-response`, `inquiry-response`) and sets their headers.
-   **Data Writing**: Populates the worksheets with data from pandas DataFrames using
    the `gspread_dataframe` library.
-   **Sharing**: Shares the created spreadsheet publicly so the results can be easily accessed.

**Dependencies**:
Requires the following libraries to be installed in the Colab environment:
-   `gspread`: For interacting with the Google Sheets API.
-   `gspread-dataframe`: For easy writing of pandas DataFrames to sheets.
-   `google-auth`: For handling authentication.
-   `pandas`: For data manipulation.

The `assignment-instructions.md` provides the basic structure, which is adapted here into
reusable functions.
"""

import pandas as pd
from typing import Dict, Optional

# Google Colab specific imports
# These lines will only work in a Google Colab environment
# In a local environment, different authentication (e.g., OAuth 2.0 flow with credentials file) would be needed.
try:
    from google.colab import auth
    import gspread
    from google.auth import default
    from gspread_dataframe import set_with_dataframe
    is_colab = True
except ImportError:
    print("Warning: Not in a Google Colab environment. Google Sheets output functionality will be limited.")
    # Define dummy classes/functions if needed for basic script execution without Colab
    class GspreadClientMock: pass
    class SpreadsheetMock: 
        def add_worksheet(self, *args, **kwargs): return WorksheetMock()
        def share(self, *args, **kwargs): pass
        @property
        def id(self): return "mock_sheet_id"
    class WorksheetMock: 
        def update(self, *args, **kwargs): pass
        def clear(self, *args, **kwargs): pass
    gspread = None
    set_with_dataframe = None
    auth = None
    default = None
    is_colab = False

def authenticate_colab_user() -> Optional[Any]: # Returns gspread.client.Client on success
    """
    Performs Google Colab authentication and returns an authorized gspread client.
    Returns None if not in Colab or authentication fails.
    """
    if not is_colab:
        print("Authentication skipped: Not in Google Colab environment.")
        return None
        
    try:
        print("Authenticating Google Colab user for Google Sheets access...")
        auth.authenticate_user()
        print("User authenticated.")
        creds, _ = default()
        gc = gspread.authorize(creds)
        print("gspread client authorized.")
        return gc
    except Exception as e:
        print(f"Error during Colab authentication or gspread authorization: {e}")
        return None

def create_output_spreadsheet(gc: Any, spreadsheet_name: str) -> Optional[Any]: # Returns gspread.Spreadsheet
    """
    Creates a new Google Spreadsheet, sets up the required sheets and headers,
    and shares it publicly.
    """
    if not gc:
        print("Cannot create spreadsheet: gspread client not available.")
        return None
        
    try:
        print(f"Creating spreadsheet: '{spreadsheet_name}'...")
        output_document = gc.create(spreadsheet_name)
        print(f"Spreadsheet created with ID: {output_document.id}")

        # --- Create Required Sheets and Headers --- 
        required_sheets = {
            "email-classification": ['email ID', 'category'],
            "order-status": ['email ID', 'product ID', 'quantity', 'status'],
            "order-response": ['email ID', 'response'],
            "inquiry-response": ['email ID', 'response']
        }

        # Delete the default initial sheet ("Sheet1")
        if len(output_document.worksheets()) > 0 and output_document.worksheets()[0].title == 'Sheet1':
            try:
                output_document.del_worksheet(output_document.worksheets()[0])
                print("Deleted default 'Sheet1'.")
            except Exception as del_e:
                print(f"Could not delete default 'Sheet1': {del_e}")

        for title, headers in required_sheets.items():
            print(f"Creating sheet: '{title}'...")
            # Set rows/cols large enough initially, gspread_dataframe will resize if needed
            sheet = output_document.add_worksheet(title=title, rows=100, cols=len(headers))
            # Set headers
            sheet.update([headers], 'A1') 
            print(f"Sheet '{title}' created with headers: {headers}")
            
        # --- Share the spreadsheet publicly ---
        print("Sharing spreadsheet publicly (read-only)...")
        output_document.share('', perm_type='anyone', role='reader')
        print("Spreadsheet shared.")
        
        print(f"Shareable link: https://docs.google.com/spreadsheets/d/{output_document.id}")
        return output_document
        
    except Exception as e:
        print(f"Error creating or setting up spreadsheet '{spreadsheet_name}': {e}")
        return None

def write_dataframe_to_sheet(spreadsheet: Any, sheet_name: str, df: pd.DataFrame):
    """
    Writes a pandas DataFrame to a specific worksheet in the given spreadsheet.
    Assumes the worksheet already exists.
    """
    if not spreadsheet or not is_colab or set_with_dataframe is None:
        print(f"Skipping write to sheet '{sheet_name}': Google Sheets integration not available.")
        return
        
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        print(f"Writing {len(df)} rows to sheet '{sheet_name}'...")
        # Clear existing data below header (optional, depends on desired behavior)
        # worksheet.clear_basic_filter()
        # worksheet.clear(start='A2') # Clear data starting from row 2
        
        # Write DataFrame (includes header by default, set include_index=False)
        # Adjust start cell if headers are already present and you don't want to overwrite
        set_with_dataframe(worksheet, df, row=1, col=1, include_sheet_header=True, include_index=False, resize=True)
        print(f"Successfully wrote data to sheet '{sheet_name}'.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"Error: Worksheet '{sheet_name}' not found in the spreadsheet.")
    except Exception as e:
        print(f"Error writing DataFrame to sheet '{sheet_name}': {e}")

def save_results_to_google_sheets(results_dfs: Dict[str, pd.DataFrame], spreadsheet_name: str):
    """
    Main function to orchestrate saving the results DataFrames to a new Google Sheet.
    Handles authentication, sheet creation, and data writing.
    
    Args:
        results_dfs: A dictionary mapping sheet names (e.g., "email-classification")
                     to pandas DataFrames containing the results.
        spreadsheet_name: The desired name for the new Google Spreadsheet.
    """
    print("--- Starting Google Sheets Output Process --- ")
    if not is_colab:
        print("Operation requires Google Colab environment. Aborting Google Sheets output.")
        return

    # 1. Authenticate
    gc = authenticate_colab_user()
    if not gc:
        print("Authentication failed. Cannot proceed with Google Sheets output.")
        return
        
    # 2. Create Spreadsheet and Sheets
    spreadsheet = create_output_spreadsheet(gc, spreadsheet_name)
    if not spreadsheet:
        print("Failed to create spreadsheet. Cannot proceed with writing data.")
        return
        
    # 3. Write DataFrames to respective sheets
    for sheet_name, df in results_dfs.items():
        write_dataframe_to_sheet(spreadsheet, sheet_name, df)
        
    print(f"--- Google Sheets Output Process Complete --- ")
    print(f"Results saved to: https://docs.google.com/spreadsheets/d/{spreadsheet.id}")

""" {cell}
### Usage Notes:

- **Colab Dependency**: This module is heavily dependent on the Google Colab environment
  for authentication (`google.colab.auth`) and the associated libraries (`gspread`, `google-auth`).
  Running this outside Colab would require implementing an alternative OAuth 2.0 flow.
- **Error Handling**: Basic error handling is included, but more robust handling
  (e.g., retries for API errors) might be needed in a production setting.
- **Permissions**: The `authenticate_user()` call will prompt the Colab user to grant
  permission for the notebook to access their Google Drive / Sheets.
- **Input DataFrames**: The `save_results_to_google_sheets` function expects a dictionary
  where keys are the exact sheet names required by the assignment and values are the
  corresponding pandas DataFrames generated by `src/process_emails.py`.
- **`gspread_dataframe`**: This library simplifies writing DataFrames. `set_with_dataframe`
  handles resizing the sheet and formatting appropriately.
- **Sharing**: The spreadsheet is shared publicly with read-only access by default.
  Permissions can be adjusted if needed.
""" 