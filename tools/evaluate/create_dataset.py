#!/usr/bin/env python
"""Script to create sample datasets in LangSmith for evaluation."""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langsmith import Client


def create_sample_dataset(dataset_name: str) -> str:
    """Create a sample dataset in LangSmith with example emails.

    Args:
        dataset_name: Name for the new dataset

    Returns:
        Dataset ID
    """
    client = Client()

    # Sample email examples
    examples = [
        {
            "inputs": {
                "email_id": "order_001",
                "subject": "Order Request",
                "message": "Hi, I'd like to order 2 blue dresses in size M and 1 red dress in size L. Please let me know the total cost and delivery time.",
            },
            "outputs": {"expected_classification": "order request"},
        },
        {
            "inputs": {
                "email_id": "inquiry_001",
                "subject": "Product Question",
                "message": "Hello, I'm interested in your summer collection. Do you have any blue dresses available? What sizes do you carry?",
            },
            "outputs": {"expected_classification": "product inquiry"},
        },
        {
            "inputs": {
                "email_id": "order_002",
                "subject": "Change my order",
                "message": "I placed an order yesterday (order #12345) but I need to change the size from M to L. Is this possible?",
            },
            "outputs": {"expected_classification": "order request"},
        },
        {
            "inputs": {
                "email_id": "inquiry_002",
                "subject": "Fabric Information",
                "message": "Can you tell me what fabric your dresses are made from? I have sensitive skin and need to know the material composition.",
            },
            "outputs": {"expected_classification": "product inquiry"},
        },
        {
            "inputs": {
                "email_id": "order_003",
                "subject": "Bulk order inquiry",
                "message": "I'm interested in placing a bulk order for my boutique. I need 10 dresses in various sizes. What's your wholesale pricing?",
            },
            "outputs": {"expected_classification": "order request"},
        },
    ]

    # Create dataset
    print(f"Creating dataset: {dataset_name}")
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Sample email dataset for Hermes evaluation",
    )

    # Add examples
    print(f"Adding {len(examples)} examples...")
    client.create_examples(dataset_id=dataset.id, examples=examples)

    print(f"✅ Dataset created successfully!")
    print(f"   Dataset ID: {dataset.id}")
    print(f"   Dataset Name: {dataset_name}")
    print(f"   Examples: {len(examples)}")

    return str(dataset.id)


def main():
    """Main function for the dataset creation script."""
    parser = argparse.ArgumentParser(
        description="Create a sample dataset in LangSmith for Hermes evaluation"
    )

    parser.add_argument("dataset_name", help="Name for the new dataset")

    args = parser.parse_args()

    try:
        dataset_id = create_sample_dataset(args.dataset_name)

        print(f"\n🎉 Dataset ready for evaluation!")
        print(f"\nTo run evaluation:")
        print(f"  python -m tools.evaluate.cli {args.dataset_name}")
        print(f"\nOr with LLM evaluators:")
        print(
            f"  python -m tools.evaluate.cli {args.dataset_name} --use-llm-evaluators"
        )

    except Exception as e:
        print(f"❌ Error creating dataset: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
