import asyncio
import os
import pandas as pd  # type: ignore
from typing import List, Dict, Any, Optional

# Apply nest_asyncio for Jupyter compatibility
import nest_asyncio  # type: ignore

# All imports must be before any code execution
from .config import HermesConfig, load_app_env_vars
from .data_processing.load_data import initialize_data_and_vector_store, load_emails_df
from .agents.workflow import hermes_langgraph_workflow, InputState, OutputState

# Apply nest_asyncio after imports
nest_asyncio.apply()

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
            # Create InputState from email_data
            input_state = InputState(
                email_id=str(email_data.get("email_id", f"unknown_email_{i}")),
                subject=email_data.get("subject"),
                message=email_data.get("message", ""),
            )

            # Execute the LangGraph workflow
            workflow_state: OutputState = await hermes_langgraph_workflow(
                input_state=input_state, hermes_config=config_obj
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
        # Try to import Google Colab dependencies
        try:
            # Use dynamic imports to avoid static type checking errors
            # pyright: ignore
            colab_auth = __import__("google.colab", fromlist=["auth"]).auth
            gspread = __import__("gspread")
            google_auth_default = __import__("google.auth", fromlist=["default"]).default
            set_with_dataframe = __import__("gspread_dataframe", fromlist=["set_with_dataframe"]).set_with_dataframe
        except ImportError:
            print("Google Colab dependencies not available. Output spreadsheet not created.")
            return "Google Colab dependencies not available"

        # Authenticate with Google
        colab_auth.authenticate_user()
        creds, _ = google_auth_default()
        gc = gspread.authorize(creds)  # type: ignore

        # Create output document
        output_document = gc.create(output_name)

        # Create and populate 'email-classification' sheet
        email_classification_sheet = output_document.add_worksheet(title="email-classification", rows=50, cols=2)
        email_classification_sheet.update([["email ID", "category"]], "A1:B1")
        set_with_dataframe(email_classification_sheet, email_classification_df)

        # Create and populate 'order-status' sheet
        order_status_sheet = output_document.add_worksheet(title="order-status", rows=50, cols=4)
        order_status_sheet.update([["email ID", "product ID", "quantity", "status"]], "A1:D1")
        set_with_dataframe(order_status_sheet, order_status_df)

        # Create and populate 'order-response' sheet
        order_response_sheet = output_document.add_worksheet(title="order-response", rows=50, cols=2)
        order_response_sheet.update([["email ID", "response"]], "A1:B1")
        set_with_dataframe(order_response_sheet, order_response_df)

        # Create and populate 'inquiry-response' sheet
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

    except Exception as e:
        print(f"Error creating output spreadsheet: {e}")
        return f"Error: {str(e)}"


async def main() -> Dict[str, Dict[str, Any]]:
    """
    Main function implementing the assignment requirements.

    Returns:
        Dictionary mapping email_id to processed results
    """
    # 1. Load app config and initialize data
    hermes_config = HermesConfig()
    print(f"Config loaded, using model: {hermes_config.llm_model_name}")

    # 2. Initialize the vector store and data
    # Pass the correct parameters to initialize_data_and_vector_store
    init_success = initialize_data_and_vector_store(
        spreadsheet_id=hermes_config.input_spreadsheet_id,
        collection_name=hermes_config.chroma_collection_name,
        openai_api_key=hermes_config.llm_api_key,
        openai_base_url=hermes_config.llm_base_url,
    )

    if not init_success:
        print("Failed to initialize data. Exiting.")
        return {}

    # 3. Load the emails dataset
    emails_df = load_emails_df(spreadsheet_id=hermes_config.input_spreadsheet_id)

    # Check if emails_df is None before using it
    if emails_df is None or emails_df.empty:
        print("No emails found to process. Exiting.")
        return {}

    print(f"Loaded {len(emails_df)} emails.")

    # Convert emails to dictionary format
    emails_batch = emails_df.to_dict(orient="records")  # type: ignore # Ignore type mismatch from to_dict

    # 4. Process emails with LangGraph workflow
    processing_limit_env = os.getenv("HERMES_PROCESSING_LIMIT")
    processing_limit: Optional[int] = None
    if processing_limit_env and processing_limit_env.isdigit():
        processing_limit = int(processing_limit_env)

    # Cast emails_batch to the correct type
    emails_for_processing: List[Dict[str, str]] = []
    for email in emails_batch:
        # Ensure all values are strings and keys are strings
        email_dict: Dict[str, str] = {}
        for k, v in email.items():
            if isinstance(k, str):  # Only include string keys
                email_dict[k] = str(v) if v is not None else ""
        emails_for_processing.append(email_dict)

    processing_results = await process_emails(
        emails_to_process=emails_for_processing,
        config_obj=hermes_config,
        limit_processing=processing_limit,
    )

    print(f"\nProcessed {len(processing_results)} emails successfully.")
    return processing_results


if __name__ == "__main__":
    asyncio.run(main())
