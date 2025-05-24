# Summary of src/hermes/utils/output.py

This module, `output.py`, found in the `hermes.utils` package, provides asynchronous utility functions for saving processed data from the Hermes system to files. It supports exporting data to CSV format and saving workflow state information to YAML files. This is crucial for persisting results, debugging, and allowing external review of the system's operations.

Key components and responsibilities:
-   **`async create_output_csv(...) -> dict[str, str]`**:
    -   **Purpose**: Asynchronously creates multiple CSV files, each containing a specific type of processed data derived from the Hermes workflow (e.g., email classifications, order statuses). The function takes several pandas DataFrames as input.
    -   **Inputs**: 
        -   `email_classification_df` (pd.DataFrame): DataFrame with email classification results.
        -   `order_status_df` (pd.DataFrame): DataFrame with order status information.
        -   `order_response_df` (pd.DataFrame): DataFrame with generated order responses.
        -   `inquiry_response_df` (pd.DataFrame): DataFrame with generated inquiry responses.
        -   `output_dir` (str, default: "./output"): The directory where CSV files will be saved. This default can be overridden.
    -   **Mechanism**: 
        1.  Ensures the `output_dir` exists, creating it if necessary using `os.makedirs` run in a separate thread via `asyncio.to_thread` to avoid blocking the event loop.
        2.  Defines file paths for each CSV using base names from `hermes.constants` (e.g., `constants.EMAIL_CLASSIFICATION_SHEET_NAME`).
        3.  Reorders columns in the input DataFrames to match predefined column lists from `hermes.constants` (e.g., `constants.EMAIL_CLASSIFICATION_COLUMNS`), ensuring consistent CSV structure.
        4.  Saves each DataFrame to its respective CSV file using `df.to_csv(index=False)`, also run asynchronously via `asyncio.to_thread`.
    -   **Output**: Returns a dictionary mapping the sheet/constant names to their corresponding saved CSV file paths. Prints a confirmation message.

-   **`write_yaml_to_file(file_path: str, yaml_content: str) -> None`**:
    -   **Purpose**: A synchronous helper function to write a given string of YAML content to a specified file path.
    -   **Mechanism**: Opens the file in write mode and writes the content.

-   **`async save_workflow_result_as_yaml(email_id: str, workflow_state: OverallState, results_dir: str) -> None`**:
    -   **Purpose**: Asynchronously saves the final state of a LangGraph workflow (`OverallState`) for a specific email to a YAML file.
    -   **Inputs**:
        -   `email_id` (str): The identifier of the email whose workflow state is being saved.
        -   `workflow_state` (`OverallState`): The workflow state object (presumably a Pydantic model or a class with a `model_dump()` method).
        -   `results_dir` (str): The directory where the YAML file will be saved.
    -   **Mechanism**:
        1.  Ensures the `results_dir` exists, creating it if necessary (using `asyncio.to_thread`).
        2.  Defines the output file path as `{results_dir}/{email_id}.yml`.
        3.  Converts the `workflow_state` object to a serializable dictionary (using `model_dump()` if available, otherwise uses the object itself).
        4.  Serializes the dictionary to a YAML string using `yaml.dump(default_flow_style=False)`.
        5.  Writes the YAML string to the file using the `write_yaml_to_file` helper, run asynchronously via `asyncio.to_thread`.
        6.  Prints a confirmation or error message.

Architecturally, `output.py` provides essential capabilities for data persistence and observability in the Hermes system. `create_output_csv` allows for the batch export of structured results into a widely accessible format, useful for reporting, analysis, or integration with other systems. `save_workflow_result_as_yaml` is particularly important for debugging and auditing, as it captures the complete state of a workflow execution, allowing developers to inspect the data at each step and understand the system's behavior for specific inputs. The asynchronous nature of these functions ensures that file I/O operations do not block the main processing loop, which is important for performance in an async application.

[Link to source file](../../../src/hermes/utils/output.py) 