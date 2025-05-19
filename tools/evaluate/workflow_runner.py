#!/usr/bin/env python
"""
Module for running the Hermes workflow against examples.
"""

import sys
import uuid
from typing import Dict, List, Any, Optional

# Add project root to system path if necessary
from .utils import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# LangSmith imports
from langsmith import Client

# Import Hermes workflow
from src.hermes.agents.workflow import hermes_langgraph_workflow
from src.hermes.config import HermesConfig


async def run_with_dataset(
    dataset_id: str,
    experiment_name: Optional[str] = None,
    hermes_config=None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Run the hermes_workflow directly on examples from a LangSmith dataset.

    Args:
        dataset_id: ID of the LangSmith dataset containing emails
        experiment_name: Custom name for the LangSmith experiment
        hermes_config: Optional HermesConfig object
        limit: Maximum number of examples to process

    Returns:
        List of workflow result dictionaries
    """
    print(f"Running Hermes workflow with dataset {dataset_id}...")

    # Clean dataset_id in case it's wrapped in UUID()
    dataset_id = str(dataset_id).replace("UUID('", "").replace("')", "")

    # Load the dataset from LangSmith
    client = Client()
    try:
        dataset = client.read_dataset(dataset_id=dataset_id)
        print(f"Found dataset: {dataset.name}")
    except Exception as e:
        print(f"Error reading dataset {dataset_id}: {e}")
        return []

    # Generate a default experiment name if none provided
    if not experiment_name:
        experiment_name = f"hermes_evaluation_{uuid.uuid4().hex[:8]}"

    # Create a new experiment
    try:
        client.create_project(experiment_name)
        print(f"Created new LangSmith project: {experiment_name}")
    except Exception as e:
        print(f"Note: {e}")

    # Initialize an empty list to store results
    results = []

    # Get the examples from the dataset
    examples = list(client.list_examples(dataset_id=dataset_id))
    print(f"Found {len(examples)} examples in dataset")

    # Apply limit if specified
    if limit and limit > 0 and limit < len(examples):
        print(f"Limiting to {limit} examples")
        examples = examples[:limit]

    # Load Hermes config if not provided
    if not hermes_config:
        hermes_config = HermesConfig()

    # Process each example through hermes_workflow
    for example in examples:
        try:
            # Extract input data from the example
            inputs = example.inputs
            email_id = str(example.id)
            email_subject = inputs.get("email_subject", "")
            email_message = inputs.get("email_message", "")

            print(f"Processing email {email_id}: {email_subject[:50]}...")

            # Format the email data for the workflow
            email_data = {
                "email_id": email_id,
                "email_subject": email_subject,
                "email_message": email_message,
            }

            # Run the workflow directly
            workflow_result = await hermes_langgraph_workflow(email_data=email_data, hermes_config=hermes_config)

            # Store the workflow state in our results format
            results.append(
                {
                    "input": email_data,
                    "output": {
                        "email-analyzer": workflow_result.get("email_analysis"),
                        "order-processor": workflow_result.get("order_result"),
                        "inquiry-responder": workflow_result.get("inquiry_response"),
                        "response-composer": workflow_result.get("composed_response"),
                    },
                    "errors": workflow_result.get("errors", {}),
                }
            )

            # Create a run to track this example processing
            try:
                run = client.create_run(
                    project_name=experiment_name,
                    name=f"Hermes Workflow - {email_id}",
                    inputs=email_data,
                    outputs={
                        "email_analysis": workflow_result.get("email_analysis"),
                        "order_result": workflow_result.get("order_result"),
                        "inquiry_response": workflow_result.get("inquiry_response"),
                        "composed_response": workflow_result.get("composed_response"),
                    },
                    tags=["hermes_workflow", email_id],
                    run_type="chain",
                )

                print(f"  Completed workflow for email {email_id} - Run ID: {run.id}")
            except Exception as e:
                print(f"  Error logging run to LangSmith: {e}")

        except Exception as e:
            print(f"Error processing example {example.id}: {e}")
            # Add error to results for tracking
            results.append(
                {
                    "input": {
                        "email_id": str(example.id),
                        "email_subject": inputs.get("email_subject", ""),
                        "email_message": inputs.get("email_message", ""),
                    },
                    "output": {},
                    "errors": {"workflow_execution": str(e)},
                }
            )

    print(f"Completed processing {len(results)} emails")
    return results
