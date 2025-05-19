#!/usr/bin/env python
"""
Script to generate the assignment output spreadsheet.

This script runs the main Hermes workflow from main.py and then
generates the assignment submission in Google Sheets format,
as specified in the assignment instructions.

Usage:
  python -m src.hermes.create_assignment_output [--limit N]
"""

import os
import asyncio
import argparse

# Import the main function from main.py
from src.hermes.main import main, create_output_spreadsheet

# Import the output data preparation function from test_helpers
from tests.integration.test_helpers import prepare_output_data


async def generate_assignment_output(limit: int = None):
    """
    Generate the assignment output in Google Sheets format.

    Args:
        limit: Optional limit of emails to process
    """
    # Set environment variable for processing limit if specified
    if limit is not None:
        os.environ["HERMES_PROCESSING_LIMIT"] = str(limit)

    print("Starting Hermes workflow to generate assignment output...")

    # 1. Run the main workflow
    results = await main()

    if not results:
        print("No results were generated. Exiting.")
        return

    # 2. Prepare the output data
    print("\nPreparing output data for assignment submission...")
    (
        email_classification_df,
        order_status_df,
        order_response_df,
        inquiry_response_df,
    ) = await prepare_output_data(results)

    # 3. Create the output spreadsheet
    print("\nCreating Google Sheets output for assignment submission...")
    try:
        from src.hermes.config import HermesConfig

        hermes_config = HermesConfig()

        output_url = await create_output_spreadsheet(
            email_classification_df=email_classification_df,
            order_status_df=order_status_df,
            order_response_df=order_response_df,
            inquiry_response_df=inquiry_response_df,
            output_name=hermes_config.output_spreadsheet_name,
        )

        print("\nAssignment output successfully generated!")
        print(f"Spreadsheet URL: {output_url}")

    except ImportError:
        print("\nGoogle Colab dependencies not available. Unable to create spreadsheet.")
        print("This script needs to be run in a Google Colab environment.")
        print("Please run this in Colab, or adapt the code to use your preferred spreadsheet method.")

    except Exception as e:
        print(f"\nError creating output spreadsheet: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Hermes assignment output.")
    parser.add_argument(
        "--limit",
        type=int,
        help="Number of emails to process. Default is to process all emails.",
        default=None,
    )

    args = parser.parse_args()
    asyncio.run(generate_assignment_output(limit=args.limit))
