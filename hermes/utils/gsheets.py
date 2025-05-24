import pandas as pd

def read_data_from_gsheet(document_id: str, sheet_name: str) -> pd.DataFrame:
    """Reads a sheet from a Google Spreadsheet into a pandas DataFrame."""
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    dataframe = pd.read_csv(export_link)
    print(f"Successfully read {len(dataframe)} rows from sheet: {sheet_name}")
    return dataframe


async def create_output_spreadsheet(
    spreadsheet_id: str,
    email_classification_df: pd.DataFrame,
    order_status_df: pd.DataFrame,
    order_response_df: pd.DataFrame,
    inquiry_response_df: pd.DataFrame,
    output_name: str = "Solving Business Problems with AI - Output",
) -> str:
    """Create the Google Spreadsheet with the assignment output."""
    try:
        # Import Google Colab dependencies
        import gspread
        from google.auth import default, credentials as google_credentials
        from google.colab import auth
        from gspread_dataframe import set_with_dataframe
    except ImportError:
        print("Google Colab and gspread dependencies not found. Skipping spreadsheet creation.")
        return "Spreadsheet creation skipped due to missing dependencies."


    # Authenticate with Google
    try:
        auth.authenticate_user()
        creds, _ = default()
    except Exception as e:
        print(f"Google Colab authentication failed: {e}. Attempting local authentication.")
        # Fallback to local authentication if Colab auth fails or is not available
        try:
            creds, _ = default(scopes=['https://www.googleapis.com/auth/spreadsheets'])
        except Exception as auth_e:
            print(f"Local Google authentication failed: {auth_e}")
            return "Spreadsheet creation skipped due to authentication failure."

    if not isinstance(creds, google_credentials.Credentials):
        print("Authentication failed: Credentials are not of the expected type.")
        return "Spreadsheet creation skipped due to authentication failure."

    gc = gspread.authorize(creds)


    # Create output document
    output_document = gc.create(output_name)

    # Create and populate sheets with correct column structure

    # Email classification sheet
    email_classification_sheet = output_document.add_worksheet(title="email-classification", rows=50, cols=2)
    email_classification_sheet.update([["email ID", "category"]], "A1:B1")
    # Ensure data is in the correct format and columns
    email_classification_df = email_classification_df[["email ID", "category"]]
    set_with_dataframe(email_classification_sheet, email_classification_df)

    # Order status sheet
    order_status_sheet = output_document.add_worksheet(title="order-status", rows=50, cols=4)
    order_status_sheet.update([["email ID", "product ID", "quantity", "status"]], "A1:D1")
    # Ensure data is in the correct format and columns
    order_status_df = order_status_df[["email ID", "product ID", "quantity", "status"]]
    set_with_dataframe(order_status_sheet, order_status_df)

    # Order response sheet
    order_response_sheet = output_document.add_worksheet(title="order-response", rows=50, cols=2)
    order_response_sheet.update([["email ID", "response"]], "A1:B1")
    # Ensure data is in the correct format and columns
    order_response_df = order_response_df[["email ID", "response"]]
    set_with_dataframe(order_response_sheet, order_response_df)

    # Inquiry response sheet
    inquiry_response_sheet = output_document.add_worksheet(title="inquiry-response", rows=50, cols=2)
    inquiry_response_sheet.update([["email ID", "response"]], "A1:B1")
    # Ensure data is in the correct format and columns
    inquiry_response_df = inquiry_response_df[["email ID", "response"]]
    set_with_dataframe(inquiry_response_sheet, inquiry_response_df)

    # Delete the default Sheet1
    worksheet = output_document.get_worksheet(0)
    output_document.del_worksheet(worksheet)

    # Share the spreadsheet publicly
    output_document.share("", perm_type="anyone", role="reader")

    # Return the shareable link
    shareable_link = f"https://docs.google.com/spreadsheets/d/{output_document.id}"
    print(f"Shareable link: {shareable_link}")
    return shareable_link