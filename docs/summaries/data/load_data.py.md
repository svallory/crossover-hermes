# Summary of src/hermes/data_processing/load_data.py

The `load_data.py` file is responsible for fetching data from Google Sheets and loading it into pandas DataFrames. It serves as the initial data loading layer for the Hermes system, providing the raw information needed by other components.

Key components and responsibilities:
- **Configuration Integration**: Uses `HermesConfig` to get the default input spreadsheet ID, avoiding hardcoded values.
- **Global Variables for Caching**:
  - `_products_df`: Caches the loaded products DataFrame to avoid redundant API calls and improve performance, as this data is frequently accessed.
  - `vector_store`: Maintains a reference related to vector operations, potentially for data consumed by or passed to a vector store.
- **Core Data Loading Functions**:
  - `read_data_from_gsheet()`: A generic function to read data from any sheet from a Google Spreadsheet using its CSV export API. This provides a simple way to access sheet data.
  - `load_emails_df()`: Specifically loads email data from the "emails" sheet.
  - `load_products_df()`: Specifically loads product data from the "products" sheet, implementing memoization (caching) for efficiency.

Architecturally, `load_data.py` provides a foundational data ingress service for the Hermes system. It abstracts the details of fetching data from Google Sheets and implements a simple but effective caching strategy for frequently accessed product data. This optimization is crucial for system performance. The use of Google Sheets' CSV export API offers a straightforward method for data retrieval, particularly for read-only operations.

[Link to source file](../../../src/hermes/data_processing/load_data.py) 