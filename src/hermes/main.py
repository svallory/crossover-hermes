import asyncio
import os
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import json
from pydantic import BaseModel

# Apply nest_asyncio for Jupyter compatibility
import nest_asyncio

nest_asyncio.apply()

from .config import HermesConfig, load_app_env_vars
from .data_processing.load_data import initialize_data_and_vector_store, load_emails_df

# Import the LangGraph workflow
from .agents.workflow import hermes_langgraph_workflow, OverallState

# Legacy agent imports for type checking
from .agents.email_analyzer import EmailAnalysis
from .agents.order_processor import ProcessedOrder
from .agents.inquiry_responder import InquiryAnswers
from .agents.response_composer import ComposedResponse

# Load environment variables
load_app_env_vars()

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
            # Execute the LangGraph workflow
            workflow_state = await hermes_langgraph_workflow(
                email_data=email_data, hermes_config=config_obj
            )

            # Extract results for the assignment output format
            result = {
                "email_id": email_id,
                "workflow_state": workflow_state,
                "classification": None,
                "order_status": [],
                "response": None,
            }

            # Extract classification
            if workflow_state.get("email_analysis"):
                result["classification"] = workflow_state[
                    "email_analysis"
                ].primary_intent
                print(f"  → Classification: {result['classification']}")

            # Extract order status
            if workflow_state.get("order_result"):
                order_result = workflow_state["order_result"]
                for item in order_result.ordered_items:
                    order_status = {
                        "email_id": email_id,
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "status": item.status,
                    }
                    result["order_status"].append(order_status)
                print(f"  → Processed {len(result['order_status'])} order items")

            # Extract response
            if workflow_state.get("composed_response"):
                result["response"] = workflow_state["composed_response"].response_body
                print(f"  → Generated response: {len(result['response'])} characters")

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


async def create_output_spreadsheet(
    email_classification_df: pd.DataFrame,
    order_status_df: pd.DataFrame,
    order_response_df: pd.DataFrame,
    inquiry_response_df: pd.DataFrame,
    output_name: str = "Solving Business Problems with AI - Output",
) -> str:
    """
    Create the Google Spreadsheet with the assignment output.

    Args:
        email_classification_df: DataFrame with email classifications
        order_status_df: DataFrame with order status information
        order_response_df: DataFrame with order responses
        inquiry_response_df: DataFrame with inquiry responses
        output_name: Name for the output spreadsheet

    Returns:
        URL of the created spreadsheet
    """
    try:
        # Import Google-specific libraries here to avoid dependencies for local testing
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

        # Create and populate 'email-classification' sheet
        email_classification_sheet = output_document.add_worksheet(
            title="email-classification", rows=50, cols=2
        )
        email_classification_sheet.update([["email ID", "category"]], "A1:B1")
        set_with_dataframe(email_classification_sheet, email_classification_df)

        # Create and populate 'order-status' sheet
        order_status_sheet = output_document.add_worksheet(
            title="order-status", rows=50, cols=4
        )
        order_status_sheet.update(
            [["email ID", "product ID", "quantity", "status"]], "A1:D1"
        )
        set_with_dataframe(order_status_sheet, order_status_df)

        # Create and populate 'order-response' sheet
        order_response_sheet = output_document.add_worksheet(
            title="order-response", rows=50, cols=2
        )
        order_response_sheet.update([["email ID", "response"]], "A1:B1")
        set_with_dataframe(order_response_sheet, order_response_df)

        # Create and populate 'inquiry-response' sheet
        inquiry_response_sheet = output_document.add_worksheet(
            title="inquiry-response", rows=50, cols=2
        )
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

    except ImportError:
        print(
            "Google Colab dependencies not available. Output spreadsheet not created."
        )
        return "Google Colab dependencies not available"
    except Exception as e:
        print(f"Error creating output spreadsheet: {e}")
        return f"Error: {str(e)}"


async def main() -> Dict[str, Dict[str, Any]]:
    """
    Main function implementing the assignment requirements.

    Returns:
        Dictionary mapping email_id to processing results
    """
    print("Starting Hermes Email Processing Workflow for Fashion Store Assignment")

    # 1. Initialize Configuration
    hermes_config = HermesConfig()
    print(f"Configuration loaded. Using {hermes_config.llm_provider}")

    if not hermes_config.llm_api_key:
        print(f"ERROR: API key for {hermes_config.llm_provider} is missing.")
        return {}

    # 2. Initialize product data and vector store
    print("\nInitializing product catalog and vector store...")
    data_initialized = initialize_data_and_vector_store(
        spreadsheet_id=hermes_config.input_spreadsheet_id,
        collection_name=hermes_config.chroma_collection_name,
    )
    if not data_initialized:
        print("Failed to initialize product data. Exiting.")
        return {}
    print("Product catalog and vector store initialized.")

    # 3. Load emails from input spreadsheet
    print("\nLoading customer emails from Google Sheets...")
    emails_df = load_emails_df(spreadsheet_id=hermes_config.input_spreadsheet_id)

    if emails_df is None or emails_df.empty:
        print("No emails to process or failed to load emails. Exiting.")
        return {}
    print(f"Loaded {len(emails_df)} emails.")

    # Convert emails to dictionary format
    emails_batch = emails_df.to_dict(orient="records")

    # 4. Process emails with LangGraph workflow
    processing_limit = int(os.getenv("HERMES_PROCESSING_LIMIT", "0"))
    if processing_limit <= 0:
        processing_limit = None
        print(f"\nProcessing all {len(emails_batch)} emails...")
    else:
        print(f"\nProcessing up to {processing_limit} emails...")

    # Process emails and return results
    results = await process_emails(
        emails_to_process=emails_batch,
        config_obj=hermes_config,
        limit_processing=processing_limit,
    )

    print(f"\nProcessed {len(results)} emails successfully.")
    return results


if __name__ == "__main__":
    # When run directly, execute the workflow and display results
    results = asyncio.run(main())

    # Check if we got any results
    if not results:
        print("No results were generated. Exiting.")
        exit(1)

    # Create output directory for local results
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Save each result as JSON
    for email_id, result in results.items():
        try:
            # Prepare serializable result
            serializable_result = {}
            for k, v in result.items():
                if isinstance(v, BaseModel):
                    serializable_result[k] = v.model_dump()
                elif k == "workflow_state":
                    # Handle the workflow state specially
                    serializable_state = {}
                    for state_key, state_value in v.items():
                        if isinstance(state_value, BaseModel):
                            serializable_state[state_key] = state_value.model_dump()
                        elif state_value is not None:
                            serializable_state[state_key] = state_value
                    serializable_result[k] = serializable_state
                else:
                    serializable_result[k] = v

            # Save to file
            file_path = os.path.join(OUTPUT_DIR, f"{email_id}-result.json")
            with open(file_path, "w") as f:
                json.dump(serializable_result, f, indent=2)

        except Exception as e:
            print(f"Error saving result for {email_id}: {e}")

    print(f"Results saved to {OUTPUT_DIR}")
    print("Hermes Email Processing complete!")
