import asyncio
import os
import pandas as pd
import yaml
from typing import Any

from hermes.workflow.states import WorkflowOutput


async def create_output_csv(
    email_classification_df: pd.DataFrame,
    order_status_df: pd.DataFrame,
    order_response_df: pd.DataFrame,
    inquiry_response_df: pd.DataFrame,
    output_dir: str = "./output",  # Changed default, though core.py will pass this value
) -> dict[str, str]:
    """Create CSV files with the assignment output, merging with existing data."""
    # Create output directory if it doesn't exist
    await asyncio.to_thread(os.makedirs, output_dir, exist_ok=True)

    # Define file paths
    email_classification_path = os.path.join(output_dir, "email-classification.csv")
    order_status_path = os.path.join(output_dir, "order-status.csv")
    order_response_path = os.path.join(output_dir, "order-response.csv")
    inquiry_response_path = os.path.join(output_dir, "inquiry-response.csv")

    # Ensure dataframes have the correct column order
    email_classification_df = email_classification_df[["email ID", "category"]]
    order_status_df = order_status_df[["email ID", "product ID", "quantity", "status"]]
    order_response_df = order_response_df[["email ID", "response"]]
    inquiry_response_df = inquiry_response_df[["email ID", "response"]]

    # Helper function to merge new data with existing CSV
    async def merge_and_save_csv(
        new_df: pd.DataFrame, file_path: str, id_column: str = "email ID"
    ) -> None:
        """Merge new data with existing CSV file, updating/adding rows for processed emails."""
        try:
            # Try to read existing CSV file
            if os.path.exists(file_path):
                existing_df = await asyncio.to_thread(pd.read_csv, file_path)

                # Get email IDs that are being updated in this run
                processed_email_ids = new_df[id_column].tolist()

                # Remove rows for emails being processed in this run from existing data
                filtered_existing_df = existing_df[
                    ~existing_df[id_column].isin(processed_email_ids)
                ]

                # Combine filtered existing data with new data
                merged_df = pd.concat([filtered_existing_df, new_df], ignore_index=True)

                # Sort by email ID for consistent output
                merged_df = merged_df.sort_values(by=id_column).reset_index(drop=True)
            else:
                # If file doesn't exist, just use the new data
                merged_df = new_df

            # Save the merged data
            await asyncio.to_thread(merged_df.to_csv, file_path, index=False)

        except Exception as e:
            print(f"Warning: Error merging data for {file_path}: {e}")
            # Fallback to overwriting if merge fails
            await asyncio.to_thread(new_df.to_csv, file_path, index=False)

    # Save each DataFrame, merging with existing data
    await merge_and_save_csv(email_classification_df, email_classification_path)
    await merge_and_save_csv(order_status_df, order_status_path)
    await merge_and_save_csv(order_response_df, order_response_path)
    await merge_and_save_csv(inquiry_response_df, inquiry_response_path)

    print(f"CSV files saved to {output_dir} (merged with existing data)")

    # Return file paths
    return {
        "email-classification": email_classification_path,
        "order-status": order_status_path,
        "order-response": order_response_path,
        "inquiry-response": inquiry_response_path,
    }


def write_yaml_to_file(file_path: str, yaml_content: str) -> None:
    """Helper function to write YAML content to a file."""
    with open(file_path, "w") as f:
        f.write(yaml_content)


async def save_workflow_result_as_yaml(
    email_id: str, workflow_state: WorkflowOutput, results_dir: str
) -> None:
    """Save the workflow result for a given email as a YAML file.

    Args:
        email_id: The ID of the email
        workflow_state: The final state of the workflow
        results_dir: The directory to save the YAML files.

    """
    # Create results directory if it doesn't exist
    await asyncio.to_thread(os.makedirs, results_dir, exist_ok=True)

    # Define the file path
    file_path = os.path.join(results_dir, f"{email_id}.yml")

    # Convert workflow state to a serializable dict
    if hasattr(workflow_state, "model_dump"):
        state_dict: dict[str, Any] = workflow_state.model_dump()
    else:
        state_dict: dict[str, Any] = workflow_state  # type: ignore

    # Write the YAML file
    try:
        # Use a simpler approach without async context manager
        yaml_str = yaml.dump(state_dict, default_flow_style=False)
        await asyncio.to_thread(write_yaml_to_file, file_path, yaml_str)
        print(f"  → Saved workflow result to {file_path}")
    except Exception as e:
        print(f"  → Error saving workflow result: {e}")
