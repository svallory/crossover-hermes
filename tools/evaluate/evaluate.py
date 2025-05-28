#!/usr/bin/env python
"""Hermes Workflow Evaluation with LangSmith Integration.

This module provides a clean, simple way to evaluate the Hermes workflow
using LangSmith datasets and experiments.
"""

import asyncio
import uuid
from typing import Any

from langsmith import evaluate

from hermes.config import HermesConfig
from hermes.model.email import CustomerEmail
from hermes.workflow.run import run_workflow
from hermes.workflow.states import WorkflowInput


def create_target_function():
    """Create the target function that LangSmith will evaluate.

    Returns:
        A function that takes LangSmith example inputs and returns Hermes workflow outputs
    """

    async def target(inputs: dict) -> dict:
        """Target function for LangSmith evaluation.

        Args:
            inputs: Dictionary with email data from LangSmith dataset

        Returns:
            Dictionary with workflow outputs
        """
        # Extract email data from LangSmith inputs
        email_id = inputs.get("email_id", str(uuid.uuid4()))
        subject = inputs.get("subject", inputs.get("email_subject", ""))
        message = inputs.get("message", inputs.get("email_message", ""))

        # Create workflow input
        workflow_input = WorkflowInput(
            email=CustomerEmail(email_id=email_id, subject=subject, message=message)
        )

        # Load config and run workflow
        config = HermesConfig()
        result = await run_workflow(workflow_input, config)

        # Convert result to dictionary for LangSmith
        return {
            "email_analysis": result.classifier.model_dump()
            if result.classifier
            else None,
            "product_resolution": result.stockkeeper.model_dump()
            if result.stockkeeper
            else None,
            "order_processing": result.fulfiller.model_dump()
            if result.fulfiller
            else None,
            "inquiry_response": result.advisor.model_dump() if result.advisor else None,
            "final_response": result.composer.model_dump() if result.composer else None,
            "errors": result.errors if result.errors else {},
        }

    return target


def create_evaluators():
    """Create evaluators for different aspects of the workflow.

    Returns:
        List of LangSmith evaluators
    """
    evaluators = []

    # Email Classification Evaluator
    def evaluate_classification(run, example) -> dict:
        """Evaluate email classification accuracy."""
        try:
            outputs = run.outputs or {}
            email_analysis = outputs.get("email_analysis", {})

            if not email_analysis:
                return {
                    "key": "classification_accuracy",
                    "score": 0,
                    "comment": "No classification output",
                }

            # Get the primary intent
            primary_intent = email_analysis.get("email_analysis", {}).get(
                "primary_intent", ""
            )

            # Simple scoring based on whether we got a classification
            score = (
                1.0 if primary_intent in ["order request", "product inquiry"] else 0.5
            )

            return {
                "key": "classification_accuracy",
                "score": score,
                "comment": f"Classified as: {primary_intent}",
            }
        except Exception as e:
            return {
                "key": "classification_accuracy",
                "score": 0,
                "comment": f"Error: {str(e)}",
            }

    evaluators.append(evaluate_classification)

    # Response Quality Evaluator
    def evaluate_response_quality(run, example) -> dict:
        """Evaluate the quality of the final response."""
        try:
            outputs = run.outputs or {}
            final_response = outputs.get("final_response", {})

            if not final_response:
                return {
                    "key": "response_quality",
                    "score": 0,
                    "comment": "No final response",
                }

            response_body = final_response.get("response_body", "")

            # Simple scoring based on response length and presence
            if len(response_body) > 50:
                score = 1.0
                comment = "Response generated successfully"
            elif len(response_body) > 0:
                score = 0.5
                comment = "Short response generated"
            else:
                score = 0.0
                comment = "No response body"

            return {"key": "response_quality", "score": score, "comment": comment}
        except Exception as e:
            return {
                "key": "response_quality",
                "score": 0,
                "comment": f"Error: {str(e)}",
            }

    evaluators.append(evaluate_response_quality)

    # Workflow Completion Evaluator
    def evaluate_workflow_completion(run, example) -> dict:
        """Evaluate whether the workflow completed successfully."""
        try:
            outputs = run.outputs or {}
            errors = outputs.get("errors", {})

            # Check if we have the required outputs
            has_classification = outputs.get("email_analysis") is not None
            has_response = outputs.get("final_response") is not None
            has_errors = bool(errors)

            if has_classification and has_response and not has_errors:
                score = 1.0
                comment = "Workflow completed successfully"
            elif has_classification and has_response:
                score = 0.8
                comment = "Workflow completed with minor issues"
            elif has_classification or has_response:
                score = 0.5
                comment = "Workflow partially completed"
            else:
                score = 0.0
                comment = "Workflow failed to complete"

            return {"key": "workflow_completion", "score": score, "comment": comment}
        except Exception as e:
            return {
                "key": "workflow_completion",
                "score": 0,
                "comment": f"Error: {str(e)}",
            }

    evaluators.append(evaluate_workflow_completion)

    return evaluators


async def run_evaluation(
    dataset_name: str,
    experiment_name: str | None = None,
    max_examples: int | None = None,
) -> dict[str, Any]:
    """Run evaluation on a LangSmith dataset.

    Args:
        dataset_name: Name of the LangSmith dataset to evaluate
        experiment_name: Name for the experiment (auto-generated if None)
        max_examples: Maximum number of examples to evaluate (None for all)

    Returns:
        Dictionary with evaluation results
    """
    if not experiment_name:
        experiment_name = f"hermes_eval_{uuid.uuid4().hex[:8]}"

    print(f"Starting evaluation: {experiment_name}")
    print(f"Dataset: {dataset_name}")
    if max_examples:
        print(f"Max examples: {max_examples}")

    # Create target function and evaluators
    target = create_target_function()
    evaluators = create_evaluators()

    # Run LangSmith evaluation using the correct API
    results = evaluate(
        target,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_name,
        max_concurrency=2,  # Don't overwhelm the API
    )

    print(f"Evaluation completed: {experiment_name}")
    print(f"View results at: https://smith.langchain.com/")

    return {
        "experiment_name": experiment_name,
        "dataset_name": dataset_name,
        "results": results,
        "langsmith_url": f"https://smith.langchain.com/",
    }


def main():
    """CLI entry point for evaluation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate Hermes workflow with LangSmith"
    )
    parser.add_argument("dataset_name", help="Name of the LangSmith dataset")
    parser.add_argument("--experiment-name", help="Custom experiment name")
    parser.add_argument(
        "--max-examples", type=int, help="Maximum number of examples to evaluate"
    )

    args = parser.parse_args()

    # Run the evaluation
    result = asyncio.run(
        run_evaluation(
            dataset_name=args.dataset_name,
            experiment_name=args.experiment_name,
            max_examples=args.max_examples,
        )
    )

    print(f"\nEvaluation complete!")
    print(f"Experiment: {result['experiment_name']}")
    print(f"View results: {result['langsmith_url']}")


if __name__ == "__main__":
    main()
