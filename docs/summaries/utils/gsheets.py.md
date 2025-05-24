# Summary of src/hermes/utils/gsheets.py

This module, `gsheets.py`, located in the `hermes.utils` package, provides utility functions for interacting with Google Sheets. It handles both reading data from existing sheets and creating new spreadsheets populated with data, primarily pandas DataFrames. This module is essential for data input (e.g., loading initial datasets) and output (e.g., exporting results of processing).

Key components and responsibilities:
-   **`read_data_from_gsheet(document_id: str, sheet_name: str) -> pd.DataFrame`**: 
    -   **Purpose**: Reads a specific sheet from a publicly accessible Google Spreadsheet into a pandas DataFrame.
    -   **Mechanism**: It constructs a CSV export link for the specified `document_id` and `sheet_name` (e.g., `https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}`).
    -   **Output**: Returns a pandas DataFrame containing the data from the sheet. It also prints a confirmation message with the number of rows read.
    -   **Usage**: This function is likely used by data loading components (e.g., `hermes.data_processing.load_data`) to fetch initial datasets like product catalogs or email lists if they are stored in Google Sheets.

-   **`async create_output_spreadsheet(...) -> str`**:
    -   **Purpose**: Asynchronously creates a new Google Spreadsheet, populates it with several DataFrames representing different aspects of Hermes processing results (email classification, order status, order responses, inquiry responses), and returns a shareable link.
    -   **Dependencies**: This function has a more complex setup, attempting to import Google Colab specific libraries (`gspread`, `google.auth`, `google.colab`, `gspread_dataframe`). It includes error handling to skip spreadsheet creation if these dependencies are not found, suggesting it's designed to run in environments like Google Colab but can degrade gracefully.
    -   **Authentication**: It handles authentication with Google services, first attempting Google Colab's `auth.authenticate_user()` and falling back to local default credentials if Colab authentication fails or is unavailable. It requires appropriate scopes (`https://www.googleapis.com/auth/spreadsheets`).
    -   **Spreadsheet Creation & Population**: 
        -   Creates a new spreadsheet with a given `output_name` (defaults to "Solving Business Problems with AI - Output").
        -   Adds multiple worksheets with predefined names (from `hermes.constants`) and column headers (also from `hermes.constants`) for: 
            - Email Classification (`constants.EMAIL_CLASSIFICATION_SHEET_NAME`)
            - Order Status (`constants.ORDER_STATUS_SHEET_NAME`)
            - Order Response (`constants.ORDER_RESPONSE_SHEET_NAME`)
            - Inquiry Response (`constants.INQUIRY_RESPONSE_SHEET_NAME`)
        -   Populates these sheets using `set_with_dataframe` from the `gspread_dataframe` library, ensuring the input DataFrames (`email_classification_df`, `order_status_df`, etc.) conform to the expected column structure defined in `hermes.constants`.
        -   Deletes the default "Sheet1" created by Google Sheets.
    -   **Sharing**: Shares the newly created spreadsheet publicly (read-only for anyone with the link).
    -   **Output**: Returns the shareable link to the created Google Spreadsheet or a message indicating failure/skip.

Architecturally, `gsheets.py` serves as an important interface between the Hermes system and Google Sheets, a common tool for data storage and collaboration. `read_data_from_gsheet` provides a simple and direct way to ingest data without requiring OAuth for read-only public sheets. The `create_output_spreadsheet` function is more sophisticated, designed for environments where Hermes might be run as part of a demonstration or assignment (given the Colab dependencies and output naming). It showcases how processed data from various stages of the Hermes workflow can be exported into a structured, human-readable format for review or further analysis. The use of constants for sheet names and columns promotes consistency and maintainability.

[Link to source file](../../../src/hermes/utils/gsheets.py) 