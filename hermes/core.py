import asyncio
import os
from typing import Any

# Apply nest_asyncio for Jupyter compatibility
from hermes.utils.output import create_output_csv
from hermes.utils.output import save_workflow_result_as_yaml
from hermes.utils.gsheets import create_output_spreadsheet
import nest_asyncio  # type: ignore
import pandas as pd  # type: ignore

from hermes.agents.classifier.models import ClassifierInput
from hermes.workflow.states import OverallState
from hermes.workflow.run import run_workflow
from hermes.config import HermesConfig
from hermes.data import load_emails_df, load_products_df
from hermes.model.email import CustomerEmail

# Set the event loop policy back to the default asyncio policy
# This is needed because uvloop is incompatible with nest_asyncio
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# Apply nest_asyncio after imports
nest_asyncio.apply()

# Default output directory
OUTPUT_DIR = "output"
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")


async def process_emails(
    emails_to_process: list[dict[str, str]],
    config_obj: HermesConfig,
    results_dir: str,
    limit_processing: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Process a batch of emails using the Hermes workflow.

    Args:
        emails_to_process: List of email dictionaries with email_id, subject, and message
        config_obj: HermesConfig object with system configuration
        results_dir: Directory to save individual YAML results.
        limit_processing: Optional limit on number of emails to process

    Returns:
        Dictionary mapping email_id to processed results

    """
    results = {}
    processed_count = 0
    # limit_processing = 0 if limit_processing is None else limit_processing # Original logic

    for i, email_data in enumerate(emails_to_process):
        # Corrected logic: if limit_processing is not None and we've reached it, break.
        if limit_processing is not None and processed_count >= limit_processing:
            print(f"Reached processing limit of {limit_processing} emails.")
            break

        email_id = str(email_data.get("email_id", f"unknown_email_{i}"))
        print(f"\nProcessing email {i + 1}/{len(emails_to_process)}: ID {email_id}")

        try:
            # Create ClassifierInput from email_data
            input_state = ClassifierInput(
                email=CustomerEmail(
                    email_id=email_data.get("email_id", f"unknown_email_{i}"),
                    subject=email_data.get("subject", ""),
                    message=email_data.get("message", ""),
                )
            )

            # Execute the LangGraph workflow
            workflow_state: OverallState = await run_workflow(
                input_state=input_state, hermes_config=config_obj
            )

            # Save the workflow result as YAML file
            await save_workflow_result_as_yaml(email_id, workflow_state, results_dir)

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
                result["classification"] = (
                    workflow_state.classifier.email_analysis.primary_intent
                )
                print(f"  → Classification: {result['classification']}")

            # Extract order status from fulfiller output
            if workflow_state.fulfiller and workflow_state.fulfiller.order_result:
                order_result = workflow_state.fulfiller.order_result
                for item in order_result.lines:
                    order_status = {
                        "email ID": email_id,
                        "product ID": item.product_id,
                        "quantity": item.quantity,
                        "status": item.status.value if item.status else "unknown",
                    }
                    result["order_status"].append(order_status)
                print(f"  → Processed {len(result['order_status'])} order items")

            # Extract response from composer output
            if workflow_state.composer:
                result["response"] = workflow_state.composer.response_body
                print(
                    f"  → Generated response: {len(str(result['response']))} characters"
                )

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


async def run_email_processing(
    products_source: str,
    emails_source: str,
    output_spreadsheet_id: str | None = None,
    processing_limit: int | None = None,
    target_email_ids: list[str] | None = None,
    output_dir: str = "output",
) -> str:
    """Core function implementing the email processing workflow.

    Args:
        products_source: Source for product data (GSheet ID#SheetName or file path).
        emails_source: Source for email data (GSheet ID#SheetName or file path).
        output_spreadsheet_id: ID of the Google Spreadsheet for output data.
                               If None, results are only saved as CSVs.
        processing_limit: Optional limit on the number of emails to process.
        target_email_ids: Optional list of specific email IDs to process.
        output_dir: Directory to save output CSV files.

    Returns:
        Message indicating where the results were saved (CSV path and/or GSheet link).
    """
    # 0. Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    # Update the global OUTPUT_DIR for other functions like save_workflow_result_as_yaml
    # This is a bit of a hack; ideally, output_dir would be passed around more explicitly
    # or set via config.
    global OUTPUT_DIR, RESULTS_DIR
    OUTPUT_DIR = output_dir
    RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # 1. Load app config
    hermes_config = HermesConfig()

    # Determine the output spreadsheet ID to use for GSheet upload
    # If output_spreadsheet_id is provided, that's where we upload.
    # If not, we only save CSVs.
    gsheet_output_target = output_spreadsheet_id

    print(f"Config loaded, using model: {hermes_config.llm_model_name}")
    print(f"Products source: {products_source}")
    print(f"Emails source: {emails_source}")
    print(f"Output directory for CSVs: {output_dir}")
    if gsheet_output_target:
        print(f"Output Google Sheet for upload: {gsheet_output_target}")

    # 2. Load the emails dataset
    try:
        print(f"Attempting to load emails from source: {emails_source}")
        emails_df = load_emails_df(source=emails_source)
        print(f"Successfully loaded {len(emails_df)} emails.")

        # Filter emails if target_email_ids are provided
        if target_email_ids:
            print(f"Filtering for specific email IDs: {target_email_ids}")
            # Ensure 'email_id' column exists. Adjust column name if different in your actual data.
            if "email_id" not in emails_df.columns:
                raise ValueError(
                    "DataFrame does not contain an 'email_id' column for filtering."
                )

            # Convert all email IDs in DataFrame to string for consistent comparison
            emails_df["email_id"] = emails_df["email_id"].astype(str)

            initial_count = len(emails_df)
            emails_df = emails_df[emails_df["email_id"].isin(target_email_ids)]
            filtered_count = len(emails_df)
            print(f"Filtered emails: {initial_count} -> {filtered_count}")
            if filtered_count == 0:
                print(
                    "Warning: No emails matched the provided target email IDs. No emails will be processed."
                )
                # Early exit or specific handling might be desired here
                # For now, it will proceed with an empty batch, resulting in no processing.

    except Exception as e:
        raise ValueError(f"Error loading emails from source '{emails_source}': {e}")

    # Load products dataset (memoized)
    try:
        print(f"Attempting to load products from source: {products_source}")
        # The actual loading will only happen if _products_df is None or source changes
        # and is handled within load_products_df
        load_products_df(source=products_source)
        # No need to assign to a variable here if it's only used by other modules via the global _products_df
        # However, if HermesConfig needs it, it should be set there.
        print(f"Products loaded/ensured available.")
    except Exception as e:
        raise ValueError(f"Error loading products from source '{products_source}': {e}")

    # 3. Convert emails to dictionary format
    emails_batch = emails_df.to_dict(orient="records")
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
        results_dir=RESULTS_DIR,
        limit_processing=processing_limit,
    )

    print(f"\nProcessed {len(processing_results)} emails successfully.")

    # 4. Prepare DataFrames for the output
    email_classification_data = []
    order_status_data = []
    order_response_data = []
    inquiry_response_data = []

    for email_id, result in processing_results.items():
        # Email classification data
        classification = result["classification"]
        if classification and classification in ["order request", "product inquiry"]:
            email_classification_data.append(
                {"email ID": email_id, "category": classification}
            )

        # Order status data
        if classification == "order request" and result["order_status"]:
            order_status_data.extend(
                [
                    {
                        "email ID": email_id,
                        "product ID": order_status["product ID"],
                        "quantity": order_status["quantity"],
                        "status": order_status["status"],
                    }
                    for order_status in result["order_status"]
                ]
            )

        # Determine which response sheet to populate based on classification
        if result["response"]:
            if classification == "order request":
                order_response_data.append(
                    {"email ID": email_id, "response": result["response"]}
                )
            elif classification == "product inquiry":
                inquiry_response_data.append(
                    {"email ID": email_id, "response": result["response"]}
                )

    # Create DataFrames with the required column names
    email_classification_df = pd.DataFrame(
        email_classification_data, columns=["email ID", "category"]
    )
    order_status_df = pd.DataFrame(
        order_status_data, columns=["email ID", "product ID", "quantity", "status"]
    )
    order_response_df = pd.DataFrame(
        order_response_data, columns=["email ID", "response"]
    )
    inquiry_response_df = pd.DataFrame(
        inquiry_response_data, columns=["email ID", "response"]
    )

    # 6. Create and populate the output
    # Always save to CSV
    await create_output_csv(
        output_dir=output_dir,
        email_classification_df=email_classification_df,
        order_status_df=order_status_df,
        order_response_df=order_response_df,
        inquiry_response_df=inquiry_response_df,
    )
    csv_message = f"CSV files saved to: {output_dir}"

    # Upload to Google Sheets if output_spreadsheet_id is provided
    if gsheet_output_target:
        shareable_link = await create_output_spreadsheet(
            spreadsheet_id=gsheet_output_target,
            email_classification_df=email_classification_df,
            order_status_df=order_status_df,
            order_response_df=order_response_df,
            inquiry_response_df=inquiry_response_df,
        )
        return f"{csv_message}\\nGoogle Sheet updated: {shareable_link}"
    else:
        return csv_message
