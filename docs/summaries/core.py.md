# Summary of src/hermes/core.py

This file, `core.py`, serves as the main orchestrator for the Hermes email processing pipeline. It brings together configuration, data loading, the core workflow execution (via LangGraph), and output generation (CSV and potentially Google Sheets). It handles batch processing of emails and manages the overall flow from input to results.

Key components and responsibilities:
-   **Async Setup**: 
    -   Applies `nest_asyncio.apply()` for compatibility in environments like Jupyter notebooks where an event loop might already be running.
    -   Resets the asyncio event loop policy to `asyncio.DefaultEventLoopPolicy()`, noting that `uvloop` (if used elsewhere) might be incompatible with `nest_asyncio`.
-   **Global Constants**: Defines `OUTPUT_DIR` ("output") and `RESULTS_DIR` ("output/results") for storing output files. These can be dynamically updated by `run_email_processing`.

-   **`async process_emails(...) -> dict[str, dict[str, Any]]`**: 
    -   **Purpose**: Processes a list of emails, one by one, through the Hermes LangGraph workflow.
    -   **Inputs**:
        -   `emails_to_process` (list[dict[str, str]]): A list of dictionaries, each representing an email with keys like `email_id`, `subject`, `message`.
        -   `config_obj` (`HermesConfig`): The application configuration object.
        -   `results_dir` (str): Directory to save individual YAML files for each processed email's workflow state.
        -   `limit_processing` (Optional[int]): An optional limit on the number of emails to process from the list.
    -   **Mechanism**:
        1.  Iterates through each `email_data` in `emails_to_process` (respecting `limit_processing`).
        2.  For each email:
            -   Creates a `ClassifierInput` Pydantic model from the email data.
            -   Invokes `await run_workflow(input_state=input_state, hermes_config=config_obj)` to execute the full LangGraph pipeline for that email. This is the core processing step.
            -   Awaits `save_workflow_result_as_yaml(...)` to save the complete `OverallState` of the workflow to a YAML file in `results_dir` named `{email_id}.yml`.
            -   Extracts key information from the `workflow_state` (e.g., primary classification from `workflow_state.classifier`, order status items from `workflow_state.fulfiller`, and the composed response from `workflow_state.composer`) to build a structured result dictionary for that email.
            -   Handles exceptions during individual email processing, logging the error and storing a simplified error structure in the results.
    -   **Output**: Returns a dictionary where keys are `email_id`s and values are the structured result dictionaries (containing classification, order status, response, or error information).

-   **`async run_email_processing(...) -> str`**: 
    -   **Purpose**: The main entry point function to orchestrate the entire email processing task, from loading data to processing emails and saving all outputs.
    -   **Inputs**:
        -   `products_source` (str): Source for product data (GSheet ID#SheetName or file path).
        -   `emails_source` (str): Source for email data (GSheet ID#SheetName or file path).
        -   `output_spreadsheet_id` (Optional[str]): Google Spreadsheet ID for uploading results. If `None`, results are only saved as CSVs.
        -   `processing_limit` (Optional[int]): Limit on the number of emails to process.
        -   `target_email_ids` (Optional[list[str]]): List of specific email IDs to process, filtering the loaded emails.
        -   `output_dir` (str, default: "output"): Directory to save output CSV files and YAML results.
    -   **Mechanism**:
        1.  **Directory Setup**: Ensures `output_dir` and `RESULTS_DIR` exist. Updates global `OUTPUT_DIR` and `RESULTS_DIR` (noted as a potential 'hack').
        2.  **Config Loading**: Loads `HermesConfig()`.
        3.  **Data Loading**:
            -   Loads emails from `emails_source` using `load_emails_df()`. This can handle GSheet links or file paths (though the parsing logic for source strings is marked as a TODO).
            -   If `target_email_ids` are provided, filters the loaded `emails_df`.
            -   Loads product data from `products_source` using `load_products_df()` (which has built-in memoization).
        4.  **Email Batch Preparation**: Converts the `emails_df` into a list of dictionaries suitable for `process_emails`.
        5.  **Core Processing**: Calls `await process_emails(...)` to process the batch.
        6.  **Output Preparation & Saving**: 
            -   Aggregates results from `process_emails` into lists for different DataFrames (email classification, order status, order response, inquiry response).
            -   Converts these lists into pandas DataFrames, ensuring correct column order using constants from `hermes.constants`.
            -   Calls `await create_output_csv(...)` to save these DataFrames as CSV files in `output_dir`.
            -   If `gsheet_output_target` (derived from `output_spreadsheet_id`) is provided, calls `await create_output_spreadsheet(...)` to upload these DataFrames to the specified Google Sheet.
        7.  **Result Message**: Constructs and returns a message indicating where the results were saved (CSV paths and/or GSheet link).
    -   **Output**: A string message summarizing the output locations.

Architecturally, `core.py` acts as the application's engine for batch email processing. It demonstrates a clear separation of concerns: `HermesConfig` for configuration, `load_data.py` for data input, `run_workflow` (from `hermes.agents.workflow.run`) for the agent-based processing logic, and utility modules (`hermes.utils.output`, `hermes.utils.gsheets`) for saving results. The `process_emails` function encapsulates the per-email workflow execution and result extraction, while `run_email_processing` manages the overall batch operation, data aggregation, and final output generation. The use of `asyncio` throughout is critical for handling I/O-bound tasks (like API calls within the workflow, file saving, GSheet operations) efficiently.

[Link to source file](../../../src/hermes/core.py) 