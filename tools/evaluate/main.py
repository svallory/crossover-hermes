#!/usr/bin/env python
"""
Main entry point for Hermes evaluation tools.

This module provides the main functionality for running the Hermes agent flow
and evaluating its performance using LangSmith. It can automatically upload
experiment results to LangSmith using the datasets API.

Usage:
  python -m tools.evaluate.main --dataset-id UUID [--experiment-name NAME] [--dataset-name NAME]
  python -m tools.evaluate.main --result-dir DIR [--experiment-name NAME] [--dataset-name NAME]

Options:
  --auto-upload      Automatically upload results to LangSmith (default: enabled)
  --no-upload        Disable automatic upload of results to LangSmith
  --dataset-name     Custom name for the dataset when auto-uploading to LangSmith
"""

import os
import sys
import asyncio
import argparse
import uuid
import datetime
import requests
from typing import Dict, List, Any, Optional

# Add project root to system path if necessary
from .utils import (
    PROJECT_ROOT,
    load_results_from_directory,
    save_report,
    format_evaluation_scores,
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import Hermes config
from src.hermes.config import load_app_env_vars

# Import test output dir
from tests.integration.test_agent_flow import OUTPUT_DIR_TEST

# LangSmith imports
from langsmith import Client
from langchain_openai import ChatOpenAI

# Import our modules
from .workflow_runner import run_with_dataset
from .evaluators import evaluate_master, convert_to_serializable

# Load environment variables
load_app_env_vars()


def upload_experiment_to_langsmith(
    results: List[Dict[str, Any]],
    dataset_name: str,
    experiment_name: Optional[str] = None,
    dataset_id: Optional[str] = None,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Upload experiment results to LangSmith.

    Args:
        results: List of processed email results
        dataset_name: Name for the dataset in LangSmith
        experiment_name: Name for the experiment in LangSmith
        dataset_id: Optional existing dataset ID
        report: Optional evaluation report containing scores

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
        # Make a serializable copy of the result
        serializable_result = convert_to_serializable(result)

        email_id = serializable_result.get("input", {}).get("email_id", str(uuid.uuid4()))
        inputs = serializable_result.get("input", {})
        outputs = serializable_result.get("output", {})

        email_analyzer_output = outputs.get("email-analyzer", {})
        order_processor_output = outputs.get("order-processor", {})
        inquiry_responder_output = outputs.get("inquiry-responder", {})
        response_composer_output = outputs.get("response-composer", {})

        # Create a result entry for each email
        eval_result = {
            # Generate a new UUID for each result
            "row_id": str(uuid.uuid4()),
            "inputs": inputs,
            "expected_outputs": {},  # We don't have expected outputs in this case
            "actual_outputs": {
                "email_analyzer": email_analyzer_output,
                "order_processor": order_processor_output,
                "inquiry_responder": inquiry_responder_output,
                "response_composer": response_composer_output,
            },
            "start_time": experiment_start_time,
            "end_time": experiment_end_time,
            "run_name": f"Hermes Flow - {email_id}",
            "run_metadata": {"email_id": email_id},
        }

        eval_results.append(eval_result)

    # Format summary scores from the report if available
    summary_experiment_scores = []
    if report:
        summary_experiment_scores = format_evaluation_scores(report)

    # Construct the request body
    body = {
        "experiment_name": experiment_name,
        "experiment_description": "Hermes Agent Flow Evaluation",
        "experiment_start_time": experiment_start_time,
        "experiment_end_time": experiment_end_time,
        "experiment_metadata": {"system": "Hermes", "version": "1.0"},
        "summary_experiment_scores": summary_experiment_scores,
        "results": eval_results,
    }

    # Always create a new dataset instead of trying to reuse an existing one
    # This avoids conflicts with example IDs
    if not dataset_name.endswith(f"_{uuid.uuid4().hex[:8]}"):
        dataset_name = f"{dataset_name}_{uuid.uuid4().hex[:8]}"

    body["dataset_name"] = dataset_name
    body["dataset_description"] = "Email processing evaluation dataset"

    # API endpoint
    langsmith_api_url = os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    endpoint = f"{langsmith_api_url}/api/v1/datasets/upload-experiment"

    # Send request
    print(f"Uploading experiment '{experiment_name}' to LangSmith with dataset '{dataset_name}'...")
    response = requests.post(endpoint, json=body, headers={"x-api-key": api_key})

    if response.status_code != 200:
        print(f"Error uploading experiment: {response.text}")
        return {"error": response.text}

    return response.json()


async def run_evaluation(
    results: List[Dict[str, Any]],
    experiment_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    auto_upload: bool = True,
    dataset_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate the results of running the Hermes agent flow using the master evaluator.

    Args:
        results: Results from running the workflow
        experiment_name: Custom name for the experiment
        output_dir: Directory to save the evaluation report
        auto_upload: Whether to automatically upload results to LangSmith
        dataset_name: Name for the dataset in LangSmith when auto-uploading

    Returns:
        Evaluation report
    """
    # Use default output directory if none specified
    if not output_dir:
        output_dir = OUTPUT_DIR_TEST

    # Generate a default experiment name if none provided
    if not experiment_name:
        experiment_name = f"hermes_evaluation_{uuid.uuid4().hex[:8]}"

    print(f"Evaluating {len(results)} workflow results in experiment '{experiment_name}'...")
    print("Using master evaluator for comprehensive evaluation")

    # Create LLM model for evaluation
    model = ChatOpenAI(model="gpt-4")

    # Initialize LangSmith client
    client = Client()

    try:
        # Create project if it doesn't exist
        try:
            client.create_project(experiment_name)
            print(f"Created new LangSmith project: {experiment_name}")
        except Exception as e:
            print(f"Note: {e}")

        # Keep track of scores for the final report
        all_scores = {
            "email_analyzer": [],
            "order_processor": [],
            "inquiry_responder": [],
            "response_composer": [],
            "end_to_end": [],
        }

        # Process each result
        for result in results:
            # Make a serializable copy of the result
            serializable_result = convert_to_serializable(result)

            email_id = serializable_result.get("input", {}).get("email_id", "unknown")
            print(f"Evaluating result for email {email_id}...")

            # Skip if there were workflow errors
            if serializable_result.get("errors") and any(serializable_result["errors"].values()):
                print(f"  Skipping evaluation due to workflow errors: {serializable_result['errors']}")
                continue

            # Extract input email
            email_input = serializable_result.get("input", {})
            email_subject = email_input.get("email_subject", "")
            email_message = email_input.get("email_message", "")

            # Extract agent outputs
            outputs = serializable_result.get("output", {})
            email_analyzer_output = outputs.get("email-analyzer", {})
            order_processor_output = outputs.get("order-processor", {})
            inquiry_responder_output = outputs.get("inquiry-responder", {})
            response_composer_output = outputs.get("response-composer", {})

            # Create workflow state for master evaluator
            workflow_state = {
                "email_id": email_id,
                "email_subject": email_subject,
                "email_message": email_message,
                "email_analysis": email_analyzer_output,
                "order_result": order_processor_output,
                "inquiry_response": inquiry_responder_output,
                "final_response": response_composer_output,
            }

            # Use the master evaluator for all components at once
            eval_results = await evaluate_master(client, experiment_name, email_id, workflow_state, model)

            # Store results in the appropriate structure
            if "email_analyzer" in eval_results and eval_results["email_analyzer"]:
                all_scores["email_analyzer"].append(eval_results["email_analyzer"])

            if "order_processor" in eval_results and eval_results["order_processor"]:
                all_scores["order_processor"].append(eval_results["order_processor"])

            if "inquiry_responder" in eval_results and eval_results["inquiry_responder"]:
                all_scores["inquiry_responder"].append(eval_results["inquiry_responder"])

            if "response_composer" in eval_results and eval_results["response_composer"]:
                all_scores["response_composer"].append(eval_results["response_composer"])

            if "end_to_end" in eval_results and eval_results["end_to_end"]:
                all_scores["end_to_end"].append(eval_results["end_to_end"])

        # Generate summary report
        print("\nGenerating evaluation summary report...")
        report = {
            "experiment_name": experiment_name,
            "emails_processed": len(results),
            "scores": all_scores,
            "langsmith_project": experiment_name,
            "langsmith_url": f"https://smith.langchain.com/projects/{experiment_name}",
            "evaluation_method": "master_evaluator",
        }

        # Save report
        report_path = save_report(report, output_dir, experiment_name)

        print(f"Evaluation complete! Report saved to {report_path}")
        print(f"View the full results in LangSmith: https://smith.langchain.com/projects/{experiment_name}")

        # Auto-upload results to LangSmith if enabled
        if auto_upload:
            if not dataset_name:
                dataset_name = f"hermes_dataset_{uuid.uuid4().hex[:8]}"

            print("\nUploading results to LangSmith using the datasets API...")

            # Convert results to serializable format for uploading
            serializable_results = [convert_to_serializable(r) for r in results]

            upload_response = upload_experiment_to_langsmith(
                results=serializable_results,
                dataset_name=dataset_name,
                experiment_name=experiment_name,
                report=convert_to_serializable(report),
            )

            dataset_id = upload_response.get("dataset", {}).get("id")
            external_experiment_id = upload_response.get("experiment", {}).get("id")

            if dataset_id and external_experiment_id:
                report["external_upload"] = {
                    "dataset_id": dataset_id,
                    "experiment_id": external_experiment_id,
                    "external_url": f"https://smith.langchain.com/projects/{external_experiment_id}",
                }

                # Update the saved report with external upload info
                report_path = save_report(report, output_dir, experiment_name)

                print("\nExperiment data uploaded successfully!")
                print(f"Dataset ID: {dataset_id}")
                print(f"Experiment ID: {external_experiment_id}")
                print(f"View the external experiment at: https://smith.langchain.com/projects/{external_experiment_id}")
            else:
                print(f"Warning: Failed to upload experiment data: {upload_response.get('error', 'Unknown error')}")

        return report

    except Exception as e:
        print(f"Error in evaluation: {e}")
        import traceback

        traceback.print_exc()

        # Save a minimal report
        report = {
            "experiment_name": experiment_name,
            "emails_processed": len(results),
            "error": str(e),
        }

        report_path = save_report(report, output_dir, experiment_name)
        print(f"Error report saved to {report_path}")

        return report


async def main_async(
    dataset_id: Optional[str] = None,
    experiment_name: Optional[str] = None,
    result_dir: Optional[str] = None,
    auto_upload: bool = True,
    dataset_name: Optional[str] = None,
    limit: Optional[int] = None,
):
    """
    Main async function to run the workflow and evaluation.

    Args:
        dataset_id: ID of the LangSmith dataset
        experiment_name: Custom name for the experiment
        result_dir: Directory containing result files
        auto_upload: Whether to automatically upload results to LangSmith
        dataset_name: Name for the dataset in LangSmith when auto-uploading
        limit: Maximum number of examples to process
    """
    # Determine whether to use existing dataset or load results
    results = []

    if dataset_id:
        # Run the workflow on the dataset
        results = await run_with_dataset(dataset_id, experiment_name, limit=limit)
    elif result_dir:
        # Load results from the directory
        print(f"Loading results from {result_dir}...")
        results = load_results_from_directory(result_dir)

        # Apply limit if specified
        if limit and limit > 0 and limit < len(results):
            print(f"Limiting to {limit} results")
            results = results[:limit]
    else:
        print("Error: Either dataset_id or result_dir must be specified.")
        return

    if not results:
        print("No results to evaluate. Exiting.")
        return

    # Run evaluation
    await run_evaluation(
        results=results,
        experiment_name=experiment_name,
        output_dir=OUTPUT_DIR_TEST,
        auto_upload=auto_upload,
        dataset_name=dataset_name,
    )


def main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Evaluate Hermes agent flow using LangSmith.")

    # Input source group
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--dataset-id", type=str, help="ID of a LangSmith dataset to use")
    input_group.add_argument("--result-dir", type=str, help="Directory containing result files to evaluate")

    # Other arguments
    parser.add_argument(
        "--experiment-name",
        type=str,
        help="Custom name for the LangSmith experiment",
        default=None,
    )
    parser.add_argument(
        "--auto-upload",
        action="store_true",
        help="Automatically upload results to LangSmith using the datasets API",
        default=True,
    )
    parser.add_argument(
        "--no-upload",
        action="store_false",
        dest="auto_upload",
        help="Disable automatic upload of results to LangSmith",
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        help="Custom name for the dataset when auto-uploading to LangSmith",
        default=None,
    )
    parser.add_argument("--limit", type=int, help="Maximum number of emails to process", default=None)

    args = parser.parse_args()

    # Run the main async function
    asyncio.run(
        main_async(
            dataset_id=args.dataset_id,
            experiment_name=args.experiment_name,
            result_dir=args.result_dir,
            auto_upload=args.auto_upload,
            dataset_name=args.dataset_name,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
