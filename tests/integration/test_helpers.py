"""Helper functions for integration testing the Hermes agent system.

This module provides utilities for:
1. Saving test inputs and outputs to YAML files
2. Wrapping agent functions to capture and save their outputs
3. Patching functions from the main module for testing purposes
4. Preparing output data for assignment submission
"""

import json
import os
from typing import Any

import pandas as pd
import yaml
from pydantic import BaseModel

# Default output directory for tests
OUTPUT_DIR_TEST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "output_test_integration",
)

# Store results in memory to write a single consolidated file
email_results = {}


# Function to prepare output data for assignment format
async def prepare_output_data(
    results: dict[str, dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Prepare the assignment output data frames from processing results.

    Args:
        results: Dictionary of processing results by email_id

    Returns:
        Tuple of DataFrames: (email_classification, order_status, order_response, inquiry_response)

    """
    # Prepare email classification data
    classification_data = []
    for email_id, result in results.items():
        classification_data.append({"email ID": email_id, "category": result["classification"] or "unknown"})

    # Prepare order status data
    order_status_data = []
    for result in results.values():
        order_status_data.extend(result["order_status"])

    # Prepare response data - split by classification
    order_response_data = []
    inquiry_response_data = []

    for email_id, result in results.items():
        if not result["response"]:
            continue

        response_entry = {"email ID": email_id, "response": result["response"]}

        if result["classification"] == "order_request":
            order_response_data.append(response_entry)
        elif result["classification"] == "product_inquiry":
            inquiry_response_data.append(response_entry)
        else:
            # If classification is unknown or error, add to both for safety
            order_response_data.append(response_entry)
            inquiry_response_data.append(response_entry)

    # Convert to DataFrames
    email_classification_df = pd.DataFrame(classification_data)
    order_status_df = pd.DataFrame(order_status_data)
    order_response_df = pd.DataFrame(order_response_data)
    inquiry_response_df = pd.DataFrame(inquiry_response_data)

    return (
        email_classification_df,
        order_status_df,
        order_response_df,
        inquiry_response_df,
    )


def save_results_locally(results: dict[str, dict[str, Any]], output_dir: str = OUTPUT_DIR_TEST):
    """Save processing results locally as JSON files.

    Args:
        results: Dictionary mapping email_id to processed results
        output_dir: Directory to save results

    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # Save each result as a separate JSON file
    for email_id, result in results.items():
        file_path = os.path.join(output_dir, f"{email_id}-result.json")

        # Convert any Pydantic models to dictionaries
        serializable_result = {}
        for key, value in result.items():
            if isinstance(value, BaseModel):
                serializable_result[key] = value.model_dump()
            elif key == "workflow_state":
                # Handle the workflow state specially
                serializable_state = {}
                for state_key, state_value in value.items():
                    if isinstance(state_value, BaseModel):
                        serializable_state[state_key] = state_value.model_dump()
                    elif state_value is not None:
                        serializable_state[state_key] = state_value
                serializable_result[key] = serializable_state
            else:
                serializable_result[key] = value

        try:
            with open(file_path, "w") as f:
                json.dump(serializable_result, f, indent=2)
        except Exception as e:
            print(f"Error saving result for {email_id}: {e}")


def save_agent_input_to_yaml(email_id: str, agent_name: str, agent_input: Any):
    """Saves the given agent input to a YAML file."""
    if not os.path.exists(OUTPUT_DIR_TEST):
        try:
            os.makedirs(OUTPUT_DIR_TEST)
        except OSError as e:
            print(f"Error creating directory {OUTPUT_DIR_TEST}: {e}")
            return

    file_path = os.path.join(OUTPUT_DIR_TEST, f"{email_id}-{agent_name}-input.yaml")
    try:
        # If the input is a Pydantic model, dump its dictionary representation
        dump_data = agent_input.model_dump() if isinstance(agent_input, BaseModel) else agent_input
        with open(file_path, "w") as f:
            yaml.dump(dump_data, f, sort_keys=False, indent=2)
    except Exception as e:
        print(f"  Error saving agent input {file_path}: {e}")

    # Also save to consolidated results
    save_to_consolidated_yaml(email_id, agent_name.replace("-", "_"), agent_input, is_input=True)


def save_to_consolidated_yaml(email_id: str, stage: str, data: Any, is_input: bool = False):
    """Adds data to the consolidated results for an email."""
    if email_id not in email_results:
        email_results[email_id] = {"input": {}, "output": {}}

    # If it's email analyzer input, extract the raw email details for top-level input
    if is_input and stage == "classifier":
        if isinstance(data, dict):
            email_results[email_id]["input"] = {
                "email_id": data.get("email_id", email_id),
                "email_subject": data.get("email_subject", ""),
                "email_message": data.get("email_message", ""),
            }
    # For all other data, organize within the output section by stage
    elif not is_input:
        # Convert pydantic models to dict if necessary
        model_data = data.model_dump() if isinstance(data, BaseModel) else data

        # For output, store under agent name in output section
        stage_name = stage.replace("_", "-") if "-" not in stage else stage
        email_results[email_id]["output"][stage_name] = model_data

    # Write the entire consolidated result to a YAML file
    if not os.path.exists(OUTPUT_DIR_TEST):
        try:
            os.makedirs(OUTPUT_DIR_TEST)
        except OSError as e:
            print(f"Error creating directory {OUTPUT_DIR_TEST}: {e}")
            return

    file_path = os.path.join(OUTPUT_DIR_TEST, f"{email_id}-result.yaml")
    try:
        with open(file_path, "w") as f:
            yaml.dump(email_results[email_id], f, sort_keys=False, indent=2)
    except Exception as e:
        print(f"  Error saving consolidated YAML {file_path}: {e}")


class OutputSaver:
    """Wraps agents to save their outputs to the consolidated YAML files."""

    @staticmethod
    async def wrapped_analyze_email(original_func, state, runnable_config):
        output = await original_func(state, runnable_config)
        email_id = state.get("email_id", "unknown_id")

        # Store in consolidated results
        if output.analysis_result:
            save_to_consolidated_yaml(
                email_id=email_id,
                stage="email-analyzer",
                data=output.analysis_result,
                is_input=False,
            )

        if output.verification and output.verification.corrected_analysis:
            save_to_consolidated_yaml(
                email_id=email_id,
                stage="email-analyzer-verification",
                data=output.verification.corrected_analysis,
                is_input=False,
            )
        return output

    @staticmethod
    async def wrapped_process_order(original_func, state, runnable_config):
        try:
            output = await original_func(state, runnable_config)
            email_id = state.email_id or "unknown_id"

            if hasattr(output, "order_result"):
                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="order-processor",
                    data=output.order_result,
                    is_input=False,
                )
                return output.order_result
            else:
                # If we have a direct ProcessOrderResult
                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="order-processor",
                    data=output,
                    is_input=False,
                )
                return output
        except Exception as e:
            print(f"Error in wrapped_process_order: {e}")
            # Return empty result on error
            return None

    @staticmethod
    async def wrapped_respond_to_inquiry(original_func, state, runnable_config):
        try:
            output = await original_func(state, runnable_config)

            # Extract email_id safely from various possible structures
            email_id = getattr(state.email_analysis, "email_id", None)
            if email_id is None and hasattr(state.email_analysis, "model_dump"):
                analysis_dict = state.email_analysis.model_dump()
                email_id = analysis_dict.get("email_id", "unknown_id")
            elif email_id is None and isinstance(state.email_analysis, dict):
                email_id = state.email_analysis.get("email_id", "unknown_id")
            else:
                email_id = "unknown_id"

            # Check output type and handle it appropriately
            from src.hermes.agents.advisor import (
                AdvisorOutput,
                InquiryAnswers,
            )

            if isinstance(output, AdvisorOutput):
                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="inquiry-responder",
                    data=output.inquiry_answers,
                    is_input=False,
                )
                return output.inquiry_answers
            elif isinstance(output, InquiryAnswers):
                # Direct InquiryResponse object (already unwrapped by patched function)
                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="inquiry-responder",
                    data=output,
                    is_input=False,
                )
                return output
            elif hasattr(output, "inquiry_response"):
                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="inquiry-responder",
                    data=output.inquiry_response,
                    is_input=False,
                )
                return output.inquiry_response
            else:
                # Some other structure, save it as is
                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="inquiry-responder",
                    data=output,
                    is_input=False,
                )
                return output
        except Exception as e:
            print(f"Error in wrapped_respond_to_inquiry: {e}")
            # Return empty result on error
            return None

    @staticmethod
    async def wrapped_compose_response(original_func, state, runnable_config):
        try:
            output = await original_func(state, runnable_config)

            # Extract email_id from state using multiple fallback methods
            email_id = None

            # From email_analysis
            if hasattr(state.email_analysis, "email_id"):
                email_id = state.email_analysis.email_id
            elif isinstance(state.email_analysis, dict) and "email_id" in state.email_analysis:
                email_id = state.email_analysis["email_id"]

            # From order_result
            if email_id is None and hasattr(state, "order_result") and hasattr(state.order_result, "email_id"):
                email_id = state.order_result.email_id

            # From inquiry_response
            if email_id is None and hasattr(state, "inquiry_response") and hasattr(state.inquiry_response, "email_id"):
                email_id = state.inquiry_response.email_id

            # Default fallback
            if email_id is None:
                email_id = "unknown_id"

            if hasattr(output, "composed_response"):
                # Ensure email_id is set correctly in the composed response
                if hasattr(output.composed_response, "email_id") and output.composed_response.email_id == "unknown_id":
                    output.composed_response.email_id = email_id

                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="response-composer",
                    data=output.composed_response,
                    is_input=False,
                )
                return output
            else:
                # Ensure email_id is set correctly in the composed response
                if hasattr(output, "email_id") and output.email_id == "unknown_id":
                    output.email_id = email_id

                save_to_consolidated_yaml(
                    email_id=email_id,
                    stage="response-composer",
                    data=output,
                    is_input=False,
                )
                return output
        except Exception as e:
            print(f"Error in wrapped_compose_response: {e}")
            # Return original output on error
            return output


def patch_agent_functions():
    """Patch the agent functions in the main module to capture and save outputs.

    Returns:
        A tuple containing (original_funcs, patched_funcs) that can be used
        to restore the original functions after testing.

    """
    from src.hermes.agents.advisor import respond_to_inquiry
    from src.hermes.agents.classifier import analyze_email
    from src.hermes.agents.composer import compose_response
    from src.hermes.agents.fulfiller import process_order

    original_funcs = {
        "analyze_email": analyze_email,
        "process_order": process_order,
        "respond_to_inquiry": respond_to_inquiry,
        "compose_response": compose_response,
    }

    # Create patched versions
    async def patched_analyze_email(state, runnable_config=None):
        return await OutputSaver.wrapped_analyze_email(original_funcs["analyze_email"], state, runnable_config)

    async def patched_process_order(state, runnable_config=None):
        try:
            output = await OutputSaver.wrapped_process_order(original_funcs["process_order"], state, runnable_config)
            # Extract order_result from the output to pass to the next agent
            if output and hasattr(output, "order_result"):
                return output.order_result
            return output
        except Exception as e:
            print(f"Error in patched_process_order: {e}")
            return None

    async def patched_respond_to_inquiry(state, runnable_config=None):
        try:
            output = await OutputSaver.wrapped_respond_to_inquiry(
                original_funcs["respond_to_inquiry"], state, runnable_config
            )
            # Extract inquiry_response from the output to pass to the next agent
            if output and hasattr(output, "inquiry_response"):
                return output.inquiry_response
            return output
        except Exception as e:
            print(f"Error in patched_respond_to_inquiry: {e}")
            return None

    async def patched_compose_response(state, runnable_config=None):
        try:
            return await OutputSaver.wrapped_compose_response(
                original_funcs["compose_response"], state, runnable_config
            )
        except Exception as e:
            print(f"Error in patched_compose_response: {e}")
            return None

    patched_funcs = {
        "analyze_email": patched_analyze_email,
        "process_order": patched_process_order,
        "respond_to_inquiry": patched_respond_to_inquiry,
        "compose_response": patched_compose_response,
    }

    return original_funcs, patched_funcs


def apply_patches():
    """Apply patches to the main module for testing.

    Returns:
        A dictionary of original functions that can be restored after testing.

    """
    import src.hermes.agents.advisor as advisor_module
    import src.hermes.agents.classifier as classifier_module
    import src.hermes.agents.composer as composer_module
    import src.hermes.agents.fulfiller as fulfiller_module

    original_funcs, patched_funcs = patch_agent_functions()

    # Apply to relevant modules
    classifier_module.agent = patched_funcs["analyze_email"]
    fulfiller_module.agent = patched_funcs["process_order"]
    advisor_module.agent = patched_funcs["respond_to_inquiry"]
    composer_module.agent = patched_funcs["compose_response"]

    return original_funcs


def restore_patches(original_funcs):
    """Restore the original functions after testing.

    Args:
        original_funcs: Dictionary of original functions from apply_patches()

    """
    import src.hermes.agents.advisor as advisor_module
    import src.hermes.agents.classifier as classifier_module
    import src.hermes.agents.composer as composer_module
    import src.hermes.agents.fulfiller as fulfiller_module

    # Restore original functions
    classifier_module.agent = original_funcs["analyze_email"]
    fulfiller_module.agent = original_funcs["process_order"]
    advisor_module.agent = original_funcs["respond_to_inquiry"]
    composer_module.agent = original_funcs["compose_response"]

    # Clear the results dict
    email_results.clear()
