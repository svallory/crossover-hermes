import asyncio
import os
import pandas as pd  # type: ignore
from typing import List, Dict, Any, Optional

# Apply nest_asyncio for Jupyter compatibility
import nest_asyncio

from src.hermes.agents.email_analyzer.models import EmailAnalyzerInput
from src.hermes.agents.workflow.states import OverallState
from src.hermes.agents.workflow.workflow import run_workflow
from src.hermes.config import HermesConfig
from src.hermes.data_processing.load_data import load_emails_df

# Apply nest_asyncio after imports
nest_asyncio.apply()

# Default output directory
OUTPUT_DIR = "output"


async def process_emails(
    emails_to_process: List[Dict[str, str]],
    config_obj: HermesConfig,
    limit_processing: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Process a batch of emails using the Hermes workflow.

    Args:
        emails_to_process: List of email dictionaries with email_id, subject, and message
        config_obj: HermesConfig object with system configuration
        limit_processing: Optional limit on number of emails to process

    Returns:
        Dictionary mapping email_id to processed results
    """
    results = {}
    processed_count = 0

    for i, email_data in enumerate(emails_to_process):
        if limit_processing is not None and processed_count >= limit_processing:
            print(f"Reached processing limit of {limit_processing} emails.")
            break

        email_id = str(email_data.get("email_id", f"unknown_email_{i}"))
        print(f"\nProcessing email {i + 1}/{len(emails_to_process)}: ID {email_id}")

        try:
            # Create EmailAnalyzerInput from email_data
            input_state = EmailAnalyzerInput(
                email_id=email_data.get("email_id", f"unknown_email_{i}"),
                subject=email_data.get("subject", ""),
                message=email_data.get("message", ""),
            )

            # Execute the LangGraph workflow
            workflow_state: OverallState = await run_workflow(
                input_state=input_state, 
                hermes_config=config_obj
            )

            # Extract results for the assignment output format
            result: Dict[str, Any] = {
                "email_id": email_id,
                "workflow_state": workflow_state,
                "classification": None,
                "order_status": [],
                "response": None,
            }

            # Extract classification from email_analyzer output
            if workflow_state.email_analyzer and workflow_state.email_analyzer.email_analysis:
                result["classification"] = workflow_state.email_analyzer.email_analysis.primary_intent
                print(f"  → Classification: {result['classification']}")

            # Extract order status from order_processor output
            if workflow_state.order_processor and workflow_state.order_processor.order_result:
                order_result = workflow_state.order_processor.order_result
                for item in order_result.ordered_items:
                    order_status = {
                        "email_id": email_id,
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "status": item.status,
                    }
                    result["order_status"].append(order_status)
                print(f"  → Processed {len(result['order_status'])} order items")

            # Extract response from response_composer output
            if workflow_state.response_composer:
                result["response"] = workflow_state.response_composer.composed_response.response_body
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


def create_output_csv(
    email_classification_df: pd.DataFrame,
    order_status_df: pd.DataFrame,
    order_response_df: pd.DataFrame,
    inquiry_response_df: pd.DataFrame,
    output_dir: str = OUTPUT_DIR,
) -> Dict[str, str]:
    """Create CSV files with the assignment output."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Define file paths
    email_classification_path = os.path.join(output_dir, "email-classification.csv")
    order_status_path = os.path.join(output_dir, "order-status.csv")
    order_response_path = os.path.join(output_dir, "order-response.csv")
    inquiry_response_path = os.path.join(output_dir, "inquiry-response.csv")
    
    # Save DataFrames to CSV files
    email_classification_df.to_csv(email_classification_path, index=False)
    order_status_df.to_csv(order_status_path, index=False)
    order_response_df.to_csv(order_response_path, index=False)
    inquiry_response_df.to_csv(inquiry_response_path, index=False)
    
    print(f"CSV files saved to {output_dir}")
    
    # Return file paths
    return {
        "email-classification": email_classification_path,
        "order-status": order_status_path,
        "order-response": order_response_path,
        "inquiry-response": inquiry_response_path
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
    from google.colab import auth
    import gspread
    from google.auth import default
    from gspread_dataframe import set_with_dataframe

    # Authenticate with Google
    auth.authenticate_user()
    creds, _ = default()
    gc = gspread.authorize(creds)

    # Create output document
    output_document = gc.create(output_name)

    # Create and populate sheets
    email_classification_sheet = output_document.add_worksheet(title="email-classification", rows=50, cols=2)
    email_classification_sheet.update([["email ID", "category"]], "A1:B1")
    set_with_dataframe(email_classification_sheet, email_classification_df)

    order_status_sheet = output_document.add_worksheet(title="order-status", rows=50, cols=4)
    order_status_sheet.update([["email ID", "product ID", "quantity", "status"]], "A1:D1")
    set_with_dataframe(order_status_sheet, order_status_df)

    order_response_sheet = output_document.add_worksheet(title="order-response", rows=50, cols=2)
    order_response_sheet.update([["email ID", "response"]], "A1:B1")
    set_with_dataframe(order_response_sheet, order_response_df)

    inquiry_response_sheet = output_document.add_worksheet(title="inquiry-response", rows=50, cols=2)
    inquiry_response_sheet.update([["email ID", "response"]], "A1:B1")
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


async def main(
    spreadsheet_id: str,
    use_csv_output: bool = False,
    processing_limit: Optional[int] = None
) -> str:
    """
    Main function implementing the assignment requirements.

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
    emails_df = await load_emails_df(spreadsheet_id=spreadsheet_id)
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
        # Email classification data
        email_classification_data.append({
            "email ID": email_id,
            "category": result["classification"]
        })
        
        # Order status data
        for order_status in result["order_status"]:
            order_status_data.append({
                "email ID": email_id,
                "product ID": order_status["product_id"],
                "quantity": order_status["quantity"],
                "status": order_status["status"]
            })
        
        # Response data
        if result["classification"] == "order request" and result["response"]:
            order_response_data.append({
                "email ID": email_id,
                "response": result["response"]
            })
        elif result["classification"] == "product inquiry" and result["response"]:
            inquiry_response_data.append({
                "email ID": email_id,
                "response": result["response"]
            })
    
    # Create DataFrames
    email_classification_df = pd.DataFrame(email_classification_data)
    order_status_df = pd.DataFrame(order_status_data)
    order_response_df = pd.DataFrame(order_response_data)
    inquiry_response_df = pd.DataFrame(inquiry_response_data)
    
    # 6. Create and populate the output
    if use_csv_output:
        output_paths = create_output_csv(
            email_classification_df=email_classification_df,
            order_status_df=order_status_df,
            order_response_df=order_response_df,
            inquiry_response_df=inquiry_response_df
        )
        return f"CSV files saved to: {OUTPUT_DIR}"
    else:
        shareable_link = await create_output_spreadsheet(
            email_classification_df=email_classification_df,
            order_status_df=order_status_df,
            order_response_df=order_response_df,
            inquiry_response_df=inquiry_response_df
        )
        return shareable_link


if __name__ == "__main__":
    # For command-line execution, but this code will primarily be used in a notebook
    import sys
    
    # Default values
    input_spreadsheet_id = "14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U"  # From assignment
    use_csv = "--csv" in sys.argv
    
    # Get limit if specified
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            try:
                limit = int(arg.split("=")[1])
            except:
                pass
    
    result = asyncio.run(main(
        spreadsheet_id=input_spreadsheet_id,
        use_csv_output=use_csv,
        processing_limit=limit
    ))
    print(f"Final result: {result}")
