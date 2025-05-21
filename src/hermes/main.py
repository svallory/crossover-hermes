import asyncio
import csv  # Add csv import
import os
from typing import Any

# Apply nest_asyncio for Jupyter compatibility
import nest_asyncio
import pandas as pd  # type: ignore
import yaml  # Add YAML import

# Set the event loop policy back to the default asyncio policy
# This is needed because uvloop is incompatible with nest_asyncio
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

from src.hermes.agents.classifier.models import ClassifierInput
from src.hermes.agents.workflow.states import OverallState
from src.hermes.agents.workflow.workflow import run_workflow
from src.hermes.config import HermesConfig
from src.hermes.data_processing.load_data import load_emails_df

# Apply nest_asyncio after imports
nest_asyncio.apply()

# Default output directory
OUTPUT_DIR = "output"
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")


async def makedirs_async(directory: str, exist_ok: bool = False) -> None:
    """Async wrapper for os.makedirs."""
    await asyncio.to_thread(os.makedirs, directory, exist_ok=exist_ok)


async def dataframe_to_csv_async(df: pd.DataFrame, path: str, index: bool = True) -> None:
    """Async wrapper for pandas DataFrame.to_csv.
    Uses QUOTE_ALL to ensure all values are quoted in the CSV.
    """
    await asyncio.to_thread(df.to_csv, path, index=index, quoting=csv.QUOTE_ALL)


async def save_workflow_result_as_yaml(email_id: str, workflow_state: OverallState) -> None:
    """Save the workflow result for a given email as a YAML file.

    Args:
        email_id: The ID of the email
        workflow_state: The final state of the workflow

    """
    # Create results directory if it doesn't exist
    await makedirs_async(RESULTS_DIR, exist_ok=True)

    # Define the file path
    file_path = os.path.join(RESULTS_DIR, f"{email_id}.yml")

    # Convert workflow state to a serializable dict
    if hasattr(workflow_state, "model_dump"):
        state_dict = workflow_state.model_dump()
    else:
        state_dict = workflow_state

    # Write the YAML file
    try:
        # Use a simpler approach without async context manager
        yaml_str = yaml.dump(state_dict, default_flow_style=False)
        await asyncio.to_thread(lambda: write_yaml_to_file(file_path, yaml_str))
        print(f"  → Saved workflow result to {file_path}")
    except Exception as e:
        print(f"  → Error saving workflow result: {e}")


def write_yaml_to_file(file_path: str, yaml_content: str) -> None:
    """Helper function to write YAML content to a file."""
    with open(file_path, "w") as f:
        f.write(yaml_content)


async def process_emails(
    emails_to_process: list[dict[str, str]],
    config_obj: HermesConfig,
    limit_processing: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Process a batch of emails using the Hermes workflow.

    Args:
        emails_to_process: List of email dictionaries with email_id, subject, and message
        config_obj: HermesConfig object with system configuration
        limit_processing: Optional limit on number of emails to process

    Returns:
        Dictionary mapping email_id to processed results

    """
    results = {}
    processed_count = 0
    limit_processing = 0 if limit_processing is None else limit_processing

    for i, email_data in enumerate(emails_to_process):
        if limit_processing > 0 and processed_count >= limit_processing:
            print(f"Reached processing limit of {limit_processing} emails.")
            break

        email_id = str(email_data.get("email_id", f"unknown_email_{i}"))
        print(f"\nProcessing email {i + 1}/{len(emails_to_process)}: ID {email_id}")

        try:
            # Create ClassifierInput from email_data
            input_state = ClassifierInput(
                email_id=email_data.get("email_id", f"unknown_email_{i}"),
                subject=email_data.get("subject", ""),
                message=email_data.get("message", ""),
            )

            # Execute the LangGraph workflow
            workflow_state: OverallState = await run_workflow(input_state=input_state, hermes_config=config_obj)

            # Save the workflow result as YAML file
            await save_workflow_result_as_yaml(email_id, workflow_state)

            # Extract results for the assignment output format
            result: dict[str, Any] = {
                "email_id": email_id,
                "workflow_state": workflow_state,
                "classification": None,
                "order_status": [],
                "response": None,
            }

            # Extract classification from classifier output
            if workflow_state.classifier and workflow_state.classifier.email_analysis:
                result["classification"] = workflow_state.classifier.email_analysis.primary_intent
                print(f"  → Classification: {result['classification']}")

            # Extract order status from fulfiller output
            if workflow_state.fulfiller and workflow_state.fulfiller.order_result:
                order_result = workflow_state.fulfiller.order_result
                for item in order_result.ordered_items:
                    order_status = {
                        "email ID": email_id,
                        "product ID": item.product_id,
                        "quantity": item.quantity,
                        "status": item.status.value,  # Use .value to get the string representation
                    }
                    result["order_status"].append(order_status)
                print(f"  → Processed {len(result['order_status'])} order items")

            # Extract response from composer output
            if workflow_state.composer:
                result["response"] = workflow_state.composer.composed_response.response_body
                print(f"  → Generated response: {len(str(result['response']))} characters")

            # Store in results dictionary
            results[email_id] = result
            processed_count += 1

        except Exception as e:
            print(f"  Error processing email {email_id}: {e}")
            results[email_id] = {
                "email_id": email_id,
                "error": str(e),
                "classification": None,
                "order_status": [],
                "response": None,
            }
            processed_count += 1

    return results


async def create_output_csv(
    email_classification_df: pd.DataFrame,
    order_status_df: pd.DataFrame,
    order_response_df: pd.DataFrame,
    inquiry_response_df: pd.DataFrame,
    output_dir: str = OUTPUT_DIR,
) -> dict[str, str]:
    """Create CSV files with the assignment output."""
    # Create output directory if it doesn't exist
    await makedirs_async(output_dir, exist_ok=True)

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
    await dataframe_to_csv_async(email_classification_df, email_classification_path, index=False)
    await dataframe_to_csv_async(order_status_df, order_status_path, index=False)
    await dataframe_to_csv_async(order_response_df, order_response_path, index=False)
    await dataframe_to_csv_async(inquiry_response_df, inquiry_response_path, index=False)

    print(f"CSV files saved to {output_dir}")

    # Return file paths
    return {
        "email-classification": email_classification_path,
        "order-status": order_status_path,
        "order-response": order_response_path,
        "inquiry-response": inquiry_response_path,
    }


async def create_output_spreadsheet(
    email_classification_df: pd.DataFrame,
    order_status_df: pd.DataFrame,
    order_response_df: pd.DataFrame,
    inquiry_response_df: pd.DataFrame,
    output_name: str = "Solving Business Problems with AI - Output",
) -> str:
    """Create the Google Spreadsheet with the assignment output."""
    # Import Google Colab dependencies
    import gspread
    from google.auth import default
    from google.colab import auth
    from gspread_dataframe import set_with_dataframe

    # Authenticate with Google
    auth.authenticate_user()
    creds, _ = default()
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


async def main(spreadsheet_id: str, use_csv_output: bool = False, processing_limit: int | None = None) -> str:
    """Main function implementing the assignment requirements.

    Args:
        spreadsheet_id: ID of the Google Spreadsheet with input data
        use_csv_output: Whether to use CSV output instead of Google Sheets
        processing_limit: Optional limit on the number of emails to process

    Returns:
        Shareable link to the output spreadsheet or path to CSV files

    """
    # 1. Load app config
    hermes_config = HermesConfig()
    hermes_config.input_spreadsheet_id = spreadsheet_id
    print(f"Config loaded, using model: {hermes_config.llm_model_name}")

    # 2. Load the emails dataset - no need for validation checks in a notebook environment
    emails_df = load_emails_df(spreadsheet_id=spreadsheet_id)  # Remove await since this is not an async function
    print(f"Loaded {len(emails_df)} emails.")

    # 3. Convert emails to dictionary format
    emails_batch = emails_df.to_dict(orient="records")

    # 4. Process emails with LangGraph workflow
    emails_for_processing = []
    for email in emails_batch:
        email_dict = {}
        for k, v in email.items():
            if isinstance(k, str):
                email_dict[k] = str(v) if v is not None else ""
        emails_for_processing.append(email_dict)

    processing_results = await process_emails(
        emails_to_process=emails_for_processing,
        config_obj=hermes_config,
        limit_processing=processing_limit,
    )

    print(f"\nProcessed {len(processing_results)} emails successfully.")

    # 5. Prepare DataFrames for the output
    email_classification_data = []
    order_status_data = []
    order_response_data = []
    inquiry_response_data = []

    for email_id, result in processing_results.items():
        # Email classification data - ensure we have the proper category labels
        classification = result["classification"]
        if classification and classification in ["order request", "product inquiry"]:
            email_classification_data.append({"email ID": email_id, "category": classification})

        # Order status data - ensure we're capturing all required fields
        if classification == "order request" and result["order_status"]:
            for order_status in result["order_status"]:
                order_status_data.append(
                    {
                        "email ID": email_id,
                        "product ID": order_status["product ID"],
                        "quantity": order_status["quantity"],
                        "status": order_status["status"],
                    }
                )

        # Determine which response sheet to populate based on classification
        if result["response"]:
            if classification == "order request":
                order_response_data.append({"email ID": email_id, "response": result["response"]})
            elif classification == "product inquiry":
                inquiry_response_data.append({"email ID": email_id, "response": result["response"]})

    # Create DataFrames with the required column names
    email_classification_df = pd.DataFrame(email_classification_data, columns=["email ID", "category"])
    order_status_df = pd.DataFrame(order_status_data, columns=["email ID", "product ID", "quantity", "status"])
    order_response_df = pd.DataFrame(order_response_data, columns=["email ID", "response"])
    inquiry_response_df = pd.DataFrame(inquiry_response_data, columns=["email ID", "response"])

    # 6. Create and populate the output
    if use_csv_output:
        await create_output_csv(
            email_classification_df=email_classification_df,
            order_status_df=order_status_df,
            order_response_df=order_response_df,
            inquiry_response_df=inquiry_response_df,
        )
        return f"CSV files saved to: {OUTPUT_DIR}"
    else:
        shareable_link = await create_output_spreadsheet(
            email_classification_df=email_classification_df,
            order_status_df=order_status_df,
            order_response_df=order_response_df,
            inquiry_response_df=inquiry_response_df,
        )
        return shareable_link


if __name__ == "__main__":
    # For command-line execution, but this code will primarily be used in a notebook
    import sys

    # Default values
    input_spreadsheet_id = "14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U"  # From assignment
    use_csv = "--csv" in sys.argv or os.getenv("OUTPUT_CSV") is not None

    # Get limit from command-line argument or environment variable
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            try:
                limit = int(arg.split("=")[1])
            except ValueError:
                pass

    # Try to get limit from environment variable if not set by command-line
    if limit is None:
        limit = int(os.getenv("HERMES_PROCESSING_LIMIT", 0))

    result = asyncio.run(main(spreadsheet_id=input_spreadsheet_id, use_csv_output=use_csv, processing_limit=limit))
    print(f"Final result: {result}")
