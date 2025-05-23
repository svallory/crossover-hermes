The `load_data.py` file is responsible for fetching data from Google Sheets and loading it into pandas DataFrames. It serves as the initial data loading layer for the Hermes system, providing the raw information needed by other components.

Key components:
- **Configuration Integration**: Uses `HermesConfig` to get the default input spreadsheet ID, avoiding hardcoded values
- **Global Variables**: Maintains module-level variables for caching:
  - `_products_df`: Cached products DataFrame to avoid redundant loading
  - `vector_store`: ChromaDB collection reference for vector operations
- **Core Functions**:
  - `read_data_from_gsheet()`: Generic function to read any sheet from a Google Spreadsheet using the CSV export API
  - `load_emails_df()`: Loads email data from the "emails" sheet
  - `load_products_df()`: Loads product data from the "products" sheet with memoization to prevent redundant API calls

The file implements a simple but effective caching strategy where the products DataFrame is loaded once and reused throughout the session. This optimization is particularly important since product data is frequently accessed by multiple agents but changes infrequently. The use of Google Sheets' CSV export API provides a straightforward way to access spreadsheet data without requiring complex authentication for read-only operations.

[Link to source file](../../../src/hermes/data_processing/load_data.py) 