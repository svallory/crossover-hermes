""" {cell}
## Output Integration - Google Sheets

This module handles the integration with Google Sheets for outputting the results
of the email processing pipeline. It fulfills the assignment requirement to write
processed data into specific worksheets within a Google Sheet.

Key functionalities include:
- Authenticating with Google Sheets API, specifically handling Colab environments.
- Creating the required Google Sheet and worksheets if they don't exist.
- Formatting and writing DataFrames containing processing results to the appropriate sheets.

NOTE: This module relies heavily on the Google Colab environment for authentication.
Running this code outside Colab would require a different authentication setup 
(e.g., service account credentials).
"""
import gspread
import gspread_dataframe as gd
import pandas as pd
from typing import Dict, List, Any, Optional

def authenticate_google_sheets() -> gspread.Client:
    """
    Authenticate with Google Sheets API. Handles Colab environment specifically.
    
    Returns:
        An authenticated gspread Client object.
        
    Raises:
        Exception: If authentication fails or not in a known environment.
    """
    try:
        # Check if running in Google Colab
        import google.colab
        from google.colab import auth
        
        print("Running in Google Colab. Authenticating...")
        auth.authenticate_user()
        import google.auth
        creds, _ = google.auth.default()
        gc = gspread.authorize(creds)
        print("Google Sheets authentication successful.")
        return gc
        
    except ImportError:
        # Not in Colab - authentication needs to be handled differently
        # For a local environment, you might use a service account JSON file
        print("Not running in Google Colab. Standard authentication methods required.")
        # Example using service account (replace with your file path):
        # try:
        #     gc = gspread.service_account(filename='path/to/your/service_account.json')
        #     return gc
        # except Exception as e:
        #     raise Exception(f"Failed to authenticate using service account: {e}")
        raise Exception("Authentication outside Colab not implemented in this reference solution.")
    except Exception as e:
        raise Exception(f"An error occurred during Google Sheets authentication: {e}")

def get_or_create_spreadsheet(gc: gspread.Client, spreadsheet_name: str) -> gspread.Spreadsheet:
    """
    Get an existing Google Spreadsheet by name or create it if it doesn't exist.
    
    Args:
        gc: Authenticated gspread client.
        spreadsheet_name: The name of the spreadsheet.
        
    Returns:
        The gspread Spreadsheet object.
    """
    try:
        spreadsheet = gc.open(spreadsheet_name)
        print(f"Opened existing spreadsheet: '{spreadsheet_name}'")
        return spreadsheet
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Spreadsheet '{spreadsheet_name}' not found. Creating...")
        spreadsheet = gc.create(spreadsheet_name)
        print(f"Created new spreadsheet: '{spreadsheet_name}'")
        
        # Share with the user (optional, useful for visibility)
        try:
            user_email = spreadsheet.client.auth.credentials.service_account_email 
            if user_email:
                spreadsheet.share(user_email, perm_type='user', role='writer')
        except Exception as share_error:
            print(f"Warning: Could not automatically share spreadsheet: {share_error}")
            
        return spreadsheet

def get_or_create_worksheet(spreadsheet: gspread.Spreadsheet, worksheet_name: str, headers: List[str]) -> gspread.Worksheet:
    """
    Get an existing worksheet within a spreadsheet or create it with specified headers.
    
    Args:
        spreadsheet: The gspread Spreadsheet object.
        worksheet_name: The name of the worksheet.
        headers: A list of strings for the header row if the worksheet is created.
        
    Returns:
        The gspread Worksheet object.
    """
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        print(f"Opened existing worksheet: '{worksheet_name}'")
        return worksheet
    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet '{worksheet_name}' not found. Creating...")
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1, cols=len(headers))
        
        # Add headers
        worksheet.append_row(headers)
        print(f"Created new worksheet '{worksheet_name}' with headers.")
        return worksheet

def write_results_to_sheet(spreadsheet: gspread.Spreadsheet, worksheet_name: str, 
                           results_df: pd.DataFrame, required_headers: List[str]):
    """
    Write the processing results DataFrame to the specified worksheet.
    Ensures the worksheet exists and has the correct headers.
    
    Args:
        spreadsheet: The target gspread Spreadsheet object.
        worksheet_name: The name of the target worksheet.
        results_df: DataFrame containing the results to write.
        required_headers: List of headers expected in the worksheet.
    """
    # Ensure the worksheet exists with the correct headers
    worksheet = get_or_create_worksheet(spreadsheet, worksheet_name, required_headers)
    
    # Check if DataFrame is empty
    if results_df.empty:
        print(f"DataFrame for worksheet '{worksheet_name}' is empty. Nothing to write.")
        return
    
    # Ensure DataFrame columns match required headers
    # Reorder columns and add missing ones with default values (e.g., None or empty string)
    formatted_df = pd.DataFrame(columns=required_headers)
    for header in required_headers:
        if header in results_df.columns:
            formatted_df[header] = results_df[header]
        else:
            formatted_df[header] = None # Or pd.NA or appropriate default
    
    # Convert DataFrame for gspread
    # Using gspread-dataframe library for easier writing
    try:
        # Clear existing data (optional, depends on desired behavior - append or overwrite)
        # worksheet.clear()
        # worksheet.append_row(required_headers) # Re-add headers after clearing
        
        # Write DataFrame content (starting from the next available row)
        # This appends the data
        existing_rows = len(worksheet.get_all_values()) # Get current number of rows
        
        # Use gd.set_with_dataframe, start writing from the next row after existing data
        gd.set_with_dataframe(
            worksheet=worksheet, 
            dataframe=formatted_df, 
            row=existing_rows + 1, # Start writing after the last row
            col=1, 
            include_index=False, 
            include_column_header=False, # Don't write headers again
            resize=True, # Resize sheet if necessary
            allow_formulas=False
        )
        print(f"Successfully wrote {len(formatted_df)} rows to worksheet '{worksheet_name}'.")
        
    except Exception as e:
        print(f"Error writing DataFrame to worksheet '{worksheet_name}': {e}")
        # Fallback to appending rows one by one if set_with_dataframe fails
        # try:
        #     print("Attempting row-by-row append as fallback...")
        #     list_of_lists = formatted_df.fillna('').values.tolist()
        #     worksheet.append_rows(list_of_lists, value_input_option='USER_ENTERED')
        #     print(f"Fallback append successful for {len(list_of_lists)} rows.")
        # except Exception as append_error:
        #     print(f"Fallback row-by-row append failed: {append_error}")

def format_and_write_final_outputs(processed_states: List[Dict[str, Any]], 
                                  spreadsheet_name: str = "Hermes - AI Processed Emails"):
    """
    Formats the final processing results from multiple emails and writes them 
    to the specified Google Sheet with separate worksheets as required by the assignment.
    
    Args:
        processed_states: A list of final state dictionaries for each processed email.
        spreadsheet_name: The name of the Google Spreadsheet to write to.
    """
    # Authenticate first
    try:
        gc = authenticate_google_sheets()
    except Exception as auth_error:
        print(f"Authentication failed: {auth_error}. Cannot write to Google Sheets.")
        return
    
    # Get or create the spreadsheet
    spreadsheet = get_or_create_spreadsheet(gc, spreadsheet_name)
    
    # --- Prepare DataFrames for each required worksheet --- 
    
    # 1. Processed Emails Worksheet
    processed_emails_data = []
    email_responses_data = []
    order_processing_data = []
    inquiry_processing_data = []
    
    for state in processed_states:
        email_id = state.get("email_id", "")
        email_analysis = state.get("email_analysis", {})
        order_result = state.get("order_result", {})
        inquiry_result = state.get("inquiry_result", {})
        final_response = state.get("final_response", "")
        
        # Data for "Processed Emails" sheet
        processed_emails_data.append({
            "Email ID": email_id,
            "Subject": state.get("email_subject", ""),
            "Body": state.get("email_body", ""),
            "Classification": email_analysis.get("classification", "unknown"),
            "Language": email_analysis.get("language", "unknown"),
            "Analysis Reasoning": email_analysis.get("reasoning", ""),
            "Final Status": order_result.get("overall_status", "") if order_result 
                            else ("inquiry_answered" if inquiry_result else "unknown")
        })
        
        # Data for "Email Responses" sheet
        email_responses_data.append({
            "Email ID": email_id,
            "Generated Response": final_response
        })
        
        # Data for "Order Processing" sheet (if applicable)
        if order_result and order_result.get("order_items"):
            for item in order_result["order_items"]:
                order_processing_data.append({
                    "Email ID": email_id,
                    "Product ID": item.get("product_id", ""),
                    "Product Name": item.get("product_name", ""),
                    "Quantity Requested": item.get("quantity_requested", 0),
                    "Quantity Fulfilled": item.get("quantity_fulfilled", 0),
                    "Status": item.get("status", ""),
                    "Unit Price": item.get("unit_price"),
                    "Promotion Details": item.get("promotion_details", "")
                })
            # Add alternatives if any
            for alt in order_result.get("suggested_alternatives", []):
                 order_processing_data.append({
                    "Email ID": email_id,
                    "Product ID": alt.get("original_product_id", ""),
                    "Product Name": f"Alternative for {alt.get('original_product_name', '')}",
                    "Quantity Requested": 0,
                    "Quantity Fulfilled": 0,
                    "Status": f"Suggested Alternative: {alt.get('suggested_product_name', '')} (ID: {alt.get('suggested_product_id', '')})",
                    "Unit Price": alt.get("price"),
                    "Promotion Details": alt.get("reason", "")
                })
        
        # Data for "Inquiry Processing" sheet (if applicable)
        if inquiry_result and inquiry_result.get("answered_questions"):
            for qa in inquiry_result["answered_questions"]:
                inquiry_processing_data.append({
                    "Email ID": email_id,
                    "Question": qa.get("question", ""),
                    "Answer": qa.get("answer", ""),
                    "Confidence": qa.get("confidence", 0.0),
                    "Relevant Product IDs": ", ".join(qa.get("relevant_product_ids", []))
                })
            # Add unanswered questions
            for question in inquiry_result.get("unanswered_questions", []):
                 inquiry_processing_data.append({
                    "Email ID": email_id,
                    "Question": question,
                    "Answer": "Could not answer with available information",
                    "Confidence": 0.0,
                    "Relevant Product IDs": ""
                })

    # Create DataFrames
    processed_emails_df = pd.DataFrame(processed_emails_data)
    email_responses_df = pd.DataFrame(email_responses_data)
    order_processing_df = pd.DataFrame(order_processing_data)
    inquiry_processing_df = pd.DataFrame(inquiry_processing_data)
    
    # --- Define Headers and Write to Sheets --- 
    
    processed_emails_headers = ["Email ID", "Subject", "Body", "Classification", "Language", "Analysis Reasoning", "Final Status"]
    write_results_to_sheet(spreadsheet, "Processed Emails", processed_emails_df, processed_emails_headers)
    
    email_responses_headers = ["Email ID", "Generated Response"]
    write_results_to_sheet(spreadsheet, "Email Responses", email_responses_df, email_responses_headers)
    
    order_processing_headers = ["Email ID", "Product ID", "Product Name", "Quantity Requested", "Quantity Fulfilled", "Status", "Unit Price", "Promotion Details"]
    write_results_to_sheet(spreadsheet, "Order Processing", order_processing_df, order_processing_headers)
    
    inquiry_processing_headers = ["Email ID", "Question", "Answer", "Confidence", "Relevant Product IDs"]
    write_results_to_sheet(spreadsheet, "Inquiry Processing", inquiry_processing_df, inquiry_processing_headers)
    
    print(f"Finished writing all results to Google Sheet: '{spreadsheet_name}'")

""" {cell}
### Output Integration Implementation Notes

This module provides the necessary functions to write the Hermes pipeline results to Google Sheets as required by the assignment specification.

Key aspects:

1. **Colab Authentication**: The `authenticate_google_sheets` function specifically handles authentication within a Google Colab environment using `google.colab.auth`. Note that running this code locally would require setting up different credentials (e.g., a service account).

2. **Spreadsheet/Worksheet Management**:
   - `get_or_create_spreadsheet` finds an existing spreadsheet by name or creates a new one.
   - `get_or_create_worksheet` finds an existing worksheet or creates it with the required headers.
   - This ensures the output structure is correctly set up before writing data.

3. **Data Formatting**: The `format_and_write_final_outputs` function:
   - Takes a list of final state dictionaries from the pipeline.
   - Parses and transforms the data from agent outputs (`email_analysis`, `order_result`, `inquiry_result`, `final_response`).
   - Creates separate Pandas DataFrames for each required worksheet ("Processed Emails", "Email Responses", "Order Processing", "Inquiry Processing").

4. **Writing to Sheets**:
   - The `write_results_to_sheet` function handles writing a DataFrame to a specific worksheet.
   - It uses the `gspread-dataframe` library for efficient writing.
   - It ensures the DataFrame columns match the required worksheet headers before writing.
   - Data is appended to existing content in the sheet.

5. **Error Handling**: Basic error handling is included for authentication and sheet/worksheet operations.

This module bridges the gap between the internal pipeline state and the required external output format, ensuring compliance with the assignment's deliverable requirements.
""" 