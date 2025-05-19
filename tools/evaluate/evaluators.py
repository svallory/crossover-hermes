#!/usr/bin/env python
"""
Master Evaluator for Hermes.

This module provides a comprehensive evaluator for all Hermes components in a single pass,
significantly reducing API calls and improving evaluation efficiency.
"""

import json
from typing import Dict, Any

# Import LangChain evaluator tools
from langchain.evaluation import load_evaluator

# Import utility functions
from .utils import read_prompt


class HermesJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle Hermes custom types."""

    def default(self, obj):
        # Convert any object to a dictionary if it has a __dict__ attribute
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        # If the object has a to_dict method, use that
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        # Handle any other special cases
        if hasattr(obj, "model_dump"):  # For Pydantic models
            return obj.model_dump()
        # Let the base class handle the rest (will raise TypeError for non-serializable objects)
        return super().default(obj)


def convert_to_serializable(obj):
    """
    Recursively convert an object to a serializable format.

    Args:
        obj: Any Python object

    Returns:
        A JSON-serializable representation of the object
    """
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        # Basic types that are already JSON serializable
        return obj
    elif hasattr(obj, "items"):
        # Handle dict-like objects including mappingproxy
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif hasattr(obj, "__dict__"):
        return convert_to_serializable(obj.__dict__)
    elif hasattr(obj, "model_dump"):  # For Pydantic models
        return convert_to_serializable(obj.model_dump())
    elif hasattr(obj, "to_dict"):
        return convert_to_serializable(obj.to_dict())
    else:
        # For any other non-serializable object, convert to string
        try:
            return str(obj)
        except Exception:
            return f"<Non-serializable object of type {type(obj).__name__}>"


def create_evaluator(model, criteria, prompt_name):
    """
    Create an evaluator for a specific component.

    Args:
        model: LLM model to use
        criteria: Dictionary of criteria for evaluation
        prompt_name: Name of the prompt file (without .md extension)

    Returns:
        LangChain evaluator
    """
    evaluation_template = read_prompt(prompt_name)

    return load_evaluator(
        "labeled_criteria",
        criteria=criteria,
        evaluation_template=evaluation_template,
        llm=model,
    )


async def evaluate_master(
    client, experiment_name: str, email_id: str, workflow_state: Dict[str, Any], model
) -> Dict[str, Any]:
    """
    Comprehensive evaluator that evaluates all agent outputs in a single pass.

    Args:
        client: LangSmith client
        experiment_name: Name of the experiment
        email_id: ID of the email
        workflow_state: Complete Hermes workflow state containing all outputs
        model: LLM model for evaluation

    Returns:
        Comprehensive evaluation results for all components
    """
    try:
        print(f"  Running comprehensive evaluation for email {email_id}...")

        # Extract relevant data from workflow state
        email_subject = workflow_state.get("email_subject", "")
        email_message = workflow_state.get("email_message", "")
        email_analyzer_output = workflow_state.get("email_analysis", {})
        order_processor_output = workflow_state.get("order_result", {})
        inquiry_responder_output = workflow_state.get("inquiry_response", {})
        response_composer_output = workflow_state.get("final_response", {})

        # Convert non-serializable objects to serializable dictionaries
        email_analyzer_dict = convert_to_serializable(email_analyzer_output)
        order_processor_dict = convert_to_serializable(order_processor_output)
        inquiry_responder_dict = convert_to_serializable(inquiry_responder_output)
        response_composer_dict = convert_to_serializable(response_composer_output)

        # Determine which components were executed
        has_order_processing = order_processor_output is not None
        has_inquiry_response = inquiry_responder_output is not None

        # Create comprehensive evaluator with all criteria
        criteria = {
            # Email Analyzer criteria
            "email_analyzer_intent": "Did the agent correctly identify the primary intent of the email?",
            "email_analyzer_extraction": "Did the agent extract all relevant entities and details?",
            "email_analyzer_segmentation": "Did the agent properly segment the email?",
            # Order Processor criteria (if applicable)
            "order_processor_identification": "Did the agent correctly identify all ordered items?",
            "order_processor_inventory": "Did the agent correctly handle inventory checks?",
            "order_processor_response": "Did the agent provide appropriate order status info?",
            # Inquiry Responder criteria (if applicable)
            "inquiry_responder_questions": "Did the agent correctly identify all customer questions?",
            "inquiry_responder_accuracy": "Are the answers factually correct based on available information?",
            "inquiry_responder_completeness": "Did the agent address all aspects of the questions?",
            # Response Composer criteria
            "response_composer_tone": "Is the tone suitable for the customer's situation?",
            "response_composer_completeness": "Does the response address all aspects of the customer's email?",
            "response_composer_clarity": "Is the response clear, well-structured, and professional?",
            "response_composer_cta": "Does it include appropriate next steps?",
            # End-to-End criteria
            "end_to_end_understanding": "Did the system understand the customer's request and situation?",
            "end_to_end_accuracy": "Is the response factually correct and appropriate?",
            "end_to_end_helpfulness": "Does the response effectively help the customer?",
            "end_to_end_professionalism": "Is the response professional with an appropriate tone?",
        }

        # Load master evaluator prompt
        evaluation_template = read_prompt("master_evaluator")

        # Create evaluator
        evaluator = load_evaluator(
            "labeled_criteria",
            criteria=criteria,
            evaluation_template=evaluation_template,
            llm=model,
        )

        # Format data for the master evaluator
        evaluation_input = {
            "email_subject": email_subject,
            "email_message": email_message,
            "email_analysis": json.dumps(email_analyzer_dict, indent=2),
            "has_order_processing": has_order_processing,
            "order_result": json.dumps(order_processor_dict, indent=2) if has_order_processing else "Not applicable",
            "has_inquiry_response": has_inquiry_response,
            "inquiry_response": json.dumps(inquiry_responder_dict, indent=2)
            if has_inquiry_response
            else "Not applicable",
            "response_subject": response_composer_dict.get("subject", ""),
            "response_body": response_composer_dict.get("response_body", ""),
        }

        # Run evaluation
        eval_result = evaluator.evaluate_strings(
            prediction=json.dumps(evaluation_input, indent=2),
            input=f"Subject: {email_subject}\nMessage: {email_message}",
            reference="",
        )

        # Log to LangSmith
        run_id = None
        try:
            run = client.create_run(
                project_name=experiment_name,
                name=f"Comprehensive Evaluation - {email_id}",
                inputs={"email": f"Subject: {email_subject}\nMessage: {email_message}"},
                outputs={"workflow_results": json.dumps(convert_to_serializable(workflow_state), indent=2)},
                tags=["master_evaluator", email_id],
                run_type="llm",
            )

            if run and hasattr(run, "id"):
                run_id = run.id

                # Add evaluation feedback for each component
                for criterion, score in eval_result.items():
                    if criterion.endswith("_reasoning"):
                        continue

                    try:
                        client.create_feedback(
                            run_id,
                            criterion,
                            score=score == "Y" if isinstance(score, str) else score,
                            comment=eval_result.get(f"{criterion}_reasoning", ""),
                        )
                    except Exception as feedback_error:
                        print(f"    Error creating feedback for {criterion}: {feedback_error}")

                print(f"    Logged comprehensive evaluation to LangSmith: {run_id}")
            else:
                print("    Warning: Could not create LangSmith run (run object invalid)")
        except Exception as run_error:
            print(f"    Error creating LangSmith run: {run_error}")

        # Organize results by component
        organized_results = {
            "email_analyzer": {
                "intent_accuracy": eval_result.get("email_analyzer_intent", 0),
                "information_extraction": eval_result.get("email_analyzer_extraction", 0),
                "segmentation_quality": eval_result.get("email_analyzer_segmentation", 0),
                "reasoning": eval_result.get("email_analyzer_intent_reasoning", ""),
            },
            "order_processor": {
                "order_identification": eval_result.get("order_processor_identification", 0),
                "inventory_handling": eval_result.get("order_processor_inventory", 0),
                "response_appropriateness": eval_result.get("order_processor_response", 0),
                "reasoning": eval_result.get("order_processor_identification_reasoning", ""),
            }
            if has_order_processing
            else None,
            "inquiry_responder": {
                "question_identification": eval_result.get("inquiry_responder_questions", 0),
                "answer_accuracy": eval_result.get("inquiry_responder_accuracy", 0),
                "answer_completeness": eval_result.get("inquiry_responder_completeness", 0),
                "reasoning": eval_result.get("inquiry_responder_questions_reasoning", ""),
            }
            if has_inquiry_response
            else None,
            "response_composer": {
                "tone_appropriateness": eval_result.get("response_composer_tone", 0),
                "response_completeness": eval_result.get("response_composer_completeness", 0),
                "clarity_professionalism": eval_result.get("response_composer_clarity", 0),
                "call_to_action": eval_result.get("response_composer_cta", 0),
                "reasoning": eval_result.get("response_composer_tone_reasoning", ""),
            },
            "end_to_end": {
                "understanding": eval_result.get("end_to_end_understanding", 0),
                "response_accuracy": eval_result.get("end_to_end_accuracy", 0),
                "helpfulness": eval_result.get("end_to_end_helpfulness", 0),
                "tone_professionalism": eval_result.get("end_to_end_professionalism", 0),
                "reasoning": eval_result.get("end_to_end_understanding_reasoning", ""),
            },
        }

        return organized_results

    except Exception as e:
        print(f"  Error in comprehensive evaluation: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
