#!/usr/bin/env python
"""Upload existing Hermes experiment results to LangSmith.

This script takes experiment results from the output directory and uploads them
to LangSmith using the /datasets/upload-experiment endpoint.

Usage:
  python -m tools.upload_experiments --dataset-name NAME [--experiment-name NAME]
"""

import argparse
import datetime
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import requests
import yaml

from hermes.config import load_app_env_vars
from tests.integration.test_agent_flow import OUTPUT_DIR_TEST

# Load environment variables
load_app_env_vars()


def upload_experiment_to_langsmith(
    results: list[dict[str, Any]],
    dataset_name: str,
    experiment_name: str | None = None,
    dataset_id: str | None = None,
) -> dict[str, Any]:
    """Upload experiment results to LangSmith.

    Args:
        results: List of processed email results
        dataset_name: Name for the dataset in LangSmith
        experiment_name: Name for the experiment in LangSmith
        dataset_id: Optional existing dataset ID

    Returns:
        Response JSON from LangSmith API

    """
    if not experiment_name:
        experiment_name = f"hermes_experiment_{uuid.uuid4().hex[:8]}"

    # Get API key from environment
    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        raise ValueError("LANGSMITH_API_KEY environment variable not set")

    # Construct experiment data
    now = datetime.datetime.now()
    experiment_start_time = (now - datetime.timedelta(minutes=10)).isoformat()
    experiment_end_time = now.isoformat()

    # Create evaluation results for each email
    eval_results = []

    for result in results:
        email_id = result.get("input", {}).get("email_id", str(uuid.uuid4()))
        inputs = result.get("input", {})
        outputs = result.get("output", {})

        classifier_output = outputs.get("email-analyzer", {})
        fulfiller_output = outputs.get("order-processor", {})
        advisor_output = outputs.get("inquiry-responder", {})
        composer_output = outputs.get("response-composer", {})

        # Create a result entry for each email
        eval_result = {
            "row_id": email_id,
            "inputs": inputs,
            "expected_outputs": {},  # We don't have expected outputs in this case
            "actual_outputs": {
                "classifier": classifier_output,
                "fulfiller": fulfiller_output,
                "advisor": advisor_output,
                "composer": composer_output,
            },
            "start_time": experiment_start_time,
            "end_time": experiment_end_time,
            "run_name": f"Hermes Flow - {email_id}",
            "run_metadata": {"email_id": email_id},
        }

        eval_results.append(eval_result)

    # Construct the request body
    body = {
        "experiment_name": experiment_name,
        "experiment_description": "Hermes Agent Flow Evaluation",
        "experiment_start_time": experiment_start_time,
        "experiment_end_time": experiment_end_time,
        "experiment_metadata": {"system": "Hermes", "version": "1.0"},
        "summary_experiment_scores": [],
        "results": eval_results,
    }

    # Add dataset info depending on whether we have an ID or name
    if dataset_id:
        body["dataset_id"] = dataset_id
    else:
        body["dataset_name"] = dataset_name
        body["dataset_description"] = "Email processing evaluation dataset"

    # API endpoint
    langsmith_api_url = os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    endpoint = f"{langsmith_api_url}/api/v1/datasets/upload-experiment"

    # Send request
    print(f"Uploading experiment '{experiment_name}' to LangSmith...")
    response = requests.post(endpoint, json=body, headers={"x-api-key": api_key})

    if response.status_code != 200:
        print(f"Error uploading experiment: {response.text}")
        return {"error": response.text}

    return response.json()


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


# Add a safe loader that handles custom tags
class SafeLoader(yaml.SafeLoader):
    pass


# Register constructor for all Python object tags
yaml.add_multi_constructor("tag:yaml.org,2002:python/object", custom_tag_constructor, Loader=SafeLoader)
yaml.add_multi_constructor("tag:yaml.org,2002:python/object/apply", custom_tag_constructor, Loader=SafeLoader)
yaml.add_multi_constructor("tag:yaml.org,2002:python/object/new", custom_tag_constructor, Loader=SafeLoader)


def load_results_from_directory(directory: str) -> list[dict[str, Any]]:
    """Load results from the output directory.

    Args:
        directory: Directory containing the YAML files

    Returns:
        List of result dictionaries

    """
    results = []
    output_dir = Path(directory)

    for yaml_file in output_dir.glob("*.yaml"):
        if yaml_file.name.endswith("_report.json"):
            continue

        with open(yaml_file) as f:
            try:
                data = yaml.load(f, Loader=SafeLoader)
                results.append(data)
            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload Hermes experiment results to LangSmith.")
    parser.add_argument(
        "--dataset-name",
        type=str,
        help="Name for the dataset in LangSmith",
        required=True,
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        help="Name for the experiment in LangSmith",
        default=None,
    )
    parser.add_argument("--dataset-id", type=str, help="Optional existing dataset ID", default=None)
    parser.add_argument(
        "--results-dir",
        type=str,
        help="Directory containing result YAML files",
        default=OUTPUT_DIR_TEST,
    )
    args = parser.parse_args()

    # Load results
    print(f"Loading results from {args.results_dir}...")
    results = load_results_from_directory(args.results_dir)

    if not results:
        print("No results found. Exiting.")
        sys.exit(1)

    print(f"Found {len(results)} results.")

    # Upload to LangSmith
    response = upload_experiment_to_langsmith(
        results=results,
        dataset_name=args.dataset_name,
        experiment_name=args.experiment_name,
        dataset_id=args.dataset_id,
    )

    # Print result
    print("\nExperiment uploaded successfully!")
    print(f"Dataset ID: {response.get('dataset', {}).get('id')}")
    print(f"Experiment ID: {response.get('experiment', {}).get('id')}")

    experiment_id = response.get("experiment", {}).get("id")
    if experiment_id:
        print(f"View the experiment at: https://smith.langchain.com/projects/{experiment_id}")
