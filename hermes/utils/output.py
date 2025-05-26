import asyncio
import os
import pandas as pd
import yaml
from typing import Any

from hermes.workflow.states import OverallState


async def create_output_csv(
    email_classification_df: pd.DataFrame,
    order_status_df: pd.DataFrame,
    order_response_df: pd.DataFrame,
    inquiry_response_df: pd.DataFrame,
    output_dir: str = "./output",  # Changed default, though core.py will pass this value
) -> dict[str, str]:
    """Create CSV files with the assignment output."""
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

    # Save DataFrames to CSV files with all values quoted
    await asyncio.to_thread(
        email_classification_df.to_csv, email_classification_path, index=False
    )
    await asyncio.to_thread(order_status_df.to_csv, order_status_path, index=False)
    await asyncio.to_thread(order_response_df.to_csv, order_response_path, index=False)
    await asyncio.to_thread(
        inquiry_response_df.to_csv, inquiry_response_path, index=False
    )

    print(f"CSV files saved to {output_dir}")

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
    email_id: str, workflow_state: OverallState, results_dir: str
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
