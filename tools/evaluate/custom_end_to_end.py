#!/usr/bin/env python
"""
Custom end-to-end evaluator for Hermes workflow.

This module provides a simplified version of the evaluation that only runs
the end-to-end evaluation with custom criteria focused on:
1. Email/segment classification accuracy
2. Response language correctness
3. Assignment criteria compliance

Usage:
  python -m tools.evaluate.custom_end_to_end --dataset-id UUID [--experiment-name NAME]
"""

import sys
import asyncio
import argparse
import uuid
import json
from typing import Dict, List, Any, Optional

# Add project root to system path if necessary
from .utils import PROJECT_ROOT, save_report

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import Hermes config
from src.hermes.config import load_app_env_vars

# Import test output dir
from tests.integration.test_agent_flow import OUTPUT_DIR_TEST

# LangSmith imports
from langsmith import Client
from langchain_openai import ChatOpenAI
from langchain.evaluation import load_evaluator

# Import workflow runner
from .workflow_runner import run_with_dataset

# Load environment variables
load_app_env_vars()

# Create a custom end-to-end evaluator prompt
CUSTOM_END_TO_END_PROMPT = """
You are evaluating the end-to-end performance of an email processing system for a high-end fashion retailer.

Given the original customer email, the analysis/classification, and the final response, evaluate:

1. Classification accuracy - Did the system correctly classify the email as either a product inquiry or order request?
2. Language correctness - Is the response in the correct language matching the customer's email?
3. Assignment criteria compliance - Does the system fulfill these specific requirements:
   - For orders: Verification of product availability and appropriate response
   - For inquiries: Relevant information from product catalog
   - Professional and production-ready tone
   - Complete addressing of all customer questions/requests

Original Email:
Subject: {email_subject}
Message: {email_message}

Email Analysis:
{email_analysis}

Final Response:
Subject: {response_subject}
Body: {response_body}

Provide your evaluation in the following format:
- Classification accuracy (0-10): [score]
- Language correctness (0-10): [score]
- Assignment criteria compliance (0-10): [score]
- Overall assessment (0-10): [score]
- Reasoning: [detailed explanation of your evaluation, highlighting any issues with classification, language, or missing criteria]
"""


async def run_custom_end_to_end_evaluation(
    results: List[Dict[str, Any]],
    experiment_name: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run only the end-to-end evaluation with custom criteria.

    Args:
        results: Results from running the workflow
        experiment_name: Custom name for the experiment
        output_dir: Directory to save the evaluation report

    Returns:
        Evaluation report
    """
    # Use default output directory if none specified
    if not output_dir:
        output_dir = OUTPUT_DIR_TEST

    # Generate a default experiment name if none provided
    if not experiment_name:
        experiment_name = f"hermes_custom_e2e_{uuid.uuid4().hex[:8]}"

    print(f"Running custom end-to-end evaluation on {len(results)} results in '{experiment_name}'...")

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

        # Create a custom evaluator with our criteria
        evaluator = load_evaluator(
            "labeled_criteria",
            criteria={
                "classification_accuracy": "Did the system correctly classify the email as either a product inquiry or order request?",
                "language_correctness": "Is the response in the correct language matching the customer's email?",
                "assignment_criteria_compliance": "Does the system fulfill all the required assignment criteria?",
            },
            evaluation_template=CUSTOM_END_TO_END_PROMPT,
            llm=model,
        )

        # Keep track of evaluation scores
        all_scores = []

        # Process each result
        for result in results:
            email_id = result.get("input", {}).get("email_id", "unknown")
            print(f"Evaluating end-to-end result for email {email_id}...")

            # Skip if there were workflow errors
            if result.get("errors") and any(result["errors"].values()):
                print(f"  Skipping evaluation due to workflow errors: {result['errors']}")
                continue

            # Extract input email
            email_input = result.get("input", {})
            email_subject = email_input.get("email_subject", "")
            email_message = email_input.get("email_message", "")

            # Extract outputs
            outputs = result.get("output", {})
            email_analyzer_output = outputs.get("email-analyzer", {})
            response_composer_output = outputs.get("response-composer", {})

            # Skip if missing required outputs
            if not email_analyzer_output or not response_composer_output:
                print("  Skipping evaluation due to missing outputs")
                continue

            if (
                not isinstance(response_composer_output, dict)
                or "response_body" not in response_composer_output
                or "subject" not in response_composer_output
            ):
                print("  Skipping evaluation due to invalid response format")
                continue

            final_subject = response_composer_output.get("subject", "")
            final_body = response_composer_output.get("response_body", "")

            # Run evaluation
            try:
                eval_result = evaluator.evaluate_strings(
                    prediction=f"Subject: {final_subject}\nBody: {final_body}",
                    input={
                        "email_subject": email_subject,
                        "email_message": email_message,
                        "email_analysis": json.dumps(email_analyzer_output, indent=2),
                        "response_subject": final_subject,
                        "response_body": final_body,
                    },
                    reference="",
                )

                # Log to LangSmith
                run = client.create_run(
                    project_name=experiment_name,
                    name=f"Custom End-to-End Evaluation - {email_id}",
                    inputs={
                        "email": f"Subject: {email_subject}\nMessage: {email_message}",
                        "email_analysis": json.dumps(email_analyzer_output, indent=2),
                    },
                    outputs={"final_response": f"Subject: {final_subject}\nBody: {final_body}"},
                    tags=["custom_end_to_end", email_id],
                    run_type="llm",
                )

                # Add evaluation feedback
                for criterion, score in eval_result.items():
                    if criterion.endswith("_reasoning"):
                        continue

                    client.create_feedback(
                        run.id,
                        criterion,
                        score=score == "Y" if isinstance(score, str) else score,
                        comment=eval_result.get(f"{criterion}_reasoning", ""),
                    )

                # Store the result
                eval_result["email_id"] = email_id
                all_scores.append(eval_result)

                print(
                    f"  Evaluated email {email_id} - Classification: {eval_result.get('classification_accuracy', 'N/A')}, Language: {eval_result.get('language_correctness', 'N/A')}, Criteria: {eval_result.get('assignment_criteria_compliance', 'N/A')}"
                )

            except Exception as e:
                print(f"  Error evaluating email {email_id}: {e}")

        # Generate summary report
        print("\nGenerating evaluation summary report...")
        report = {
            "experiment_name": experiment_name,
            "emails_processed": len(all_scores),
            "scores": all_scores,
            "langsmith_project": experiment_name,
            "langsmith_url": f"https://smith.langchain.com/projects/{experiment_name}",
        }

        # Save report
        report_path = save_report(report, output_dir, f"{experiment_name}_summary")

        print(f"Evaluation complete! Report saved to {report_path}")
        print(f"View the full results in LangSmith: https://smith.langchain.com/projects/{experiment_name}")

        return report

    except Exception as e:
        print(f"Error in evaluation: {e}")
        import traceback

        traceback.print_exc()

        # Save a minimal report
        report = {
            "experiment_name": experiment_name,
            "emails_processed": 0,
            "error": str(e),
        }

        report_path = save_report(report, output_dir, f"{experiment_name}_error")
        print(f"Error report saved to {report_path}")

        return report


async def main_async(dataset_id: str, experiment_name: Optional[str] = None, limit: Optional[int] = None):
    """
    Main async function to run the workflow and custom end-to-end evaluation.

    Args:
        dataset_id: ID of the LangSmith dataset
        experiment_name: Custom name for the experiment
        limit: Maximum number of examples to process
    """
    # Ensure dataset_id is a string without uuid wrapper if necessary
    if not dataset_id:
        print("Error: dataset_id is required")
        return

    # Remove any UUID wrapper if present
    dataset_id = str(dataset_id).replace("UUID('", "").replace("')", "")

    # Run the workflow on the dataset
    results = await run_with_dataset(dataset_id, experiment_name, limit=limit)

    if not results:
        print("No results to evaluate. Exiting.")
        return

    # Run the custom end-to-end evaluation
    await run_custom_end_to_end_evaluation(results, experiment_name, OUTPUT_DIR_TEST)


def main():
    """Command line entry point."""
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
