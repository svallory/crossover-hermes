#!/usr/bin/env python
"""
Wrapper script for custom Hermes workflow evaluation.

This script is a simple wrapper around tools.evaluate.custom_end_to_end
to provide a convenient entry point for custom evaluation focusing on
classification accuracy, language correctness, and assignment criteria.

Usage:
  python -m tools.evaluate_custom --dataset-id UUID [--experiment-name NAME] [--limit N]
"""

import sys
import argparse
from tools.evaluate.custom_end_to_end import main_async
import asyncio


def main():
    """Command line entry point with support for limit parameter."""
    parser = argparse.ArgumentParser(description="Run custom end-to-end evaluation of Hermes workflow.")

    parser.add_argument("--dataset-id", type=str, help="ID of a LangSmith dataset to use", required=True)

    parser.add_argument(
        "--experiment-name",
        type=str,
        help="Custom name for the LangSmith experiment",
        default=None,
    )

    parser.add_argument("--limit", type=int, help="Maximum number of emails to process", default=None)

    args = parser.parse_args()

    # Run the main async function
    asyncio.run(
        main_async(
            dataset_id=args.dataset_id,
            experiment_name=args.experiment_name,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
