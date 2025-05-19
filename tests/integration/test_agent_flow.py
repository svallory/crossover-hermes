"""
Integration test for the full Hermes agent workflow.

This test loads product and email data directly from local CSV files,
initializes the necessary data structures (like the vector store),
and then runs the main agent pipeline for a specified number of emails.

Usage:
  python -m tests.integration.test_agent_flow [--limit N]
"""

import asyncio
import os
import pandas as pd
import argparse
import yaml
from typing import Optional, Dict
import sys

from src.hermes.config import HermesConfig, load_app_env_vars
from src.hermes.data_processing import load_data
from src.hermes.data_processing.vector_store import create_vector_store
import src.hermes.main as hermes_main
from tests.integration.test_helpers import (
    OUTPUT_DIR_TEST,
    apply_patches,
    restore_patches,
    email_results,
    prepare_output_data,
    save_results_locally,
)

# Set base path assuming the script is run from the workspace root via `python -m`
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Modify sys.path if necessary to ensure src is importable
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if os.path.join(BASE_DIR, "src") not in sys.path:
    sys.path.insert(0, os.path.join(BASE_DIR, "src"))

# Ensure environment variables from .env are loaded for the test context
load_app_env_vars()


async def run_test_workflow(limit: Optional[int] = None):
    """
    Run the Hermes agent flow test workflow.

    Args:
        limit: Maximum number of emails to process
    """
    print("Starting Hermes Integration Test Workflow...")

    # Clear the email_results dict for each test run
    email_results.clear()

    # 0. Create a specific output directory for this test run
    if not os.path.exists(OUTPUT_DIR_TEST):
        os.makedirs(OUTPUT_DIR_TEST)
        print(f"Created test output directory: {OUTPUT_DIR_TEST}")

    # Patch the agent functions to save outputs
    original_funcs = apply_patches()

    try:
        # 1. Initialize Configuration
        print("Initializing HermesConfig for test...")
        # Use default config, can be overridden if test needs specific settings
        hermes_config = HermesConfig()
        # Disable LLM output verification for tests to speed up and reduce token usage
        hermes_config.llm_output_verification = False
        print(f"Test Config: LLM Verification Disabled: {not hermes_config.llm_output_verification}")

        # 2. Load data directly from CSV files for the test
        print("Loading data from local CSV files for test...")
        try:
            test_products_df = pd.read_csv(os.path.join(BASE_DIR, "data", "products.csv"))
            test_emails_df = pd.read_csv(os.path.join(BASE_DIR, "data", "emails.csv"))
        except FileNotFoundError as e:
            print(f"Error: Could not find data/products.csv or data/emails.csv. Ensure they exist. {e}")
            print(f"Attempted to load from: {os.path.join(BASE_DIR, 'data')}")
            # Fallback to try relative path from where script might be if not run with `python -m`
            alt_data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data")
            try:
                test_products_df = pd.read_csv(os.path.join(alt_data_path, "products.csv"))
                test_emails_df = pd.read_csv(os.path.join(alt_data_path, "emails.csv"))
                print(f"Successfully loaded data from alternative path: {alt_data_path}")
            except FileNotFoundError as e2:
                print(f"Error: Still could not find data files at alternative path. {e2}")
                return

        if test_products_df is None or test_emails_df is None:
            print("Failed to load test data. Exiting test.")
            return
        print(f"Loaded {len(test_products_df)} products and {len(test_emails_df)} emails for test.")

        # 3. Initialize data stores for tools
        print("Initializing data stores for tools (products_df and vector_store)...")
        try:
            # Directly set the pandas DataFrame in the load_data module
            load_data.products_df = test_products_df
            print(f"  Set load_data.products_df with {len(load_data.products_df)} products.")

            # Create and set the vector store in the load_data module
            # Use collection name from config or a test-specific one
            test_collection_name = hermes_config.chroma_collection_name + "_test"
            print(f"  Creating vector store with collection name: {test_collection_name}")
            vs = create_vector_store(products_df=test_products_df, collection_name=test_collection_name)
            if vs:
                load_data.vector_store = vs
                print("  Set load_data.vector_store successfully.")
            else:
                print("  Failed to create vector store for test. Exiting.")
                # Attempt to delete the potentially problematic collection if it was partially created
                try:
                    import chromadb

                    client = chromadb.Client()  # In-memory client
                    client.delete_collection(test_collection_name)
                    print(f"Attempted to clean up collection: {test_collection_name}")
                except Exception as cleanup_e:
                    print(f"Error during cleanup: {cleanup_e}")
                return

        except Exception as e_init:
            print(f"  Error initializing data stores for tools: {e_init}")
            return

        # 4. Convert emails to the expected format and apply limit
        emails_batch = test_emails_df.to_dict(orient="records")

        # Explicitly convert values to strings to match the expected type hint
        emails_for_processing: list[Dict[str, str]] = []
        for email in emails_batch:
            email_dict: Dict[str, str] = {}
            for k, v in email.items():
                if isinstance(k, str):
                    email_dict[k] = str(v) if v is not None else ""
            emails_for_processing.append(email_dict)

        # Set HERMES_PROCESSING_LIMIT for this run based on the 'limit' argument
        if limit is None:
            limit = int(os.environ.get("HERMES_PROCESSING_LIMIT", "0"))
        else:
            os.environ["HERMES_PROCESSING_LIMIT"] = str(limit)

        # 5. Run the main workflow
        print("\nStarting Hermes agent workflow using process_emails...")
        try:
            processed_outputs = await hermes_main.process_emails(
                emails_to_process=emails_for_processing,
                config_obj=hermes_config,
                limit_processing=limit,
            )
            print("\nIntegration test: process_emails completed.")

            # Basic check: Did we get any output?
            if limit is not None and limit > 0:
                assert len(processed_outputs) > 0, (
                    f"Expected some processed outputs when limit is {limit}, got {len(processed_outputs)}"
                )
                print(
                    f"  Processed {len(processed_outputs)} emails as expected by limit (or fewer if total emails is less than limit)."
                )
            elif limit is None or limit == 0:
                assert len(processed_outputs) == len(emails_batch), "Expected to process all emails if no limit."
                print(f"  Processed all {len(processed_outputs)} emails.")

            # 6. Save results locally
            print("\nSaving test results to JSON files...")
            save_results_locally(processed_outputs, OUTPUT_DIR_TEST)

            # 7. Prepare assignment output data
            print("\nPreparing assignment output data...")
            (
                email_classification_df,
                order_status_df,
                order_response_df,
                inquiry_response_df,
            ) = await prepare_output_data(processed_outputs)

            # 8. Save DataFrames as CSV files for inspection
            email_classification_df.to_csv(os.path.join(OUTPUT_DIR_TEST, "email-classification.csv"), index=False)
            order_status_df.to_csv(os.path.join(OUTPUT_DIR_TEST, "order-status.csv"), index=False)
            order_response_df.to_csv(os.path.join(OUTPUT_DIR_TEST, "order-response.csv"), index=False)
            inquiry_response_df.to_csv(os.path.join(OUTPUT_DIR_TEST, "inquiry-response.csv"), index=False)

            print(f"  Outputs and agent inputs saved to: {OUTPUT_DIR_TEST}")
            print(f"  Assignment output data saved as CSV files in: {OUTPUT_DIR_TEST}")

        except Exception as e_workflow:
            print(f"Error during agent workflow execution in test: {e_workflow}")
            assert False, f"Workflow execution failed: {e_workflow}"

    finally:
        # Restore original functions
        restore_patches(original_funcs)

        # Clean up environment variable
        if "HERMES_PROCESSING_LIMIT" in os.environ:
            del os.environ["HERMES_PROCESSING_LIMIT"]

        print("Test run finished and environment cleaned up.")


# Custom YAML loader class for handling custom tags
class SafeLoader(yaml.SafeLoader):
    pass


# Import YAML with custom tag handling


def custom_tag_constructor(loader, tag, node):
    # For any custom tag, just return the scalar value as a string
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


# Register constructor for all Python object tags
yaml.add_multi_constructor("tag:yaml.org,2002:python/object", custom_tag_constructor, Loader=SafeLoader)
yaml.add_multi_constructor("tag:yaml.org,2002:python/object/apply", custom_tag_constructor, Loader=SafeLoader)
yaml.add_multi_constructor("tag:yaml.org,2002:python/object/new", custom_tag_constructor, Loader=SafeLoader)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Hermes integration test.")
    parser.add_argument(
        "--limit",
        type=int,
        help="Number of emails to process. Processes all if not specified.",
        default=None,
    )
    args = parser.parse_args()

    asyncio.run(run_test_workflow(limit=args.limit))
