"""Entry point for running the Hermes workflow.
This initializes the vector store and runs the workflow.
"""

from langchain_core.runnables import RunnableConfig

from hermes.config import HermesConfig
from hermes.data.vector_store import get_vector_store

from .graph import workflow
from .states import WorkflowInput, WorkflowOutput


async def run_workflow(
    input_state: WorkflowInput,
    hermes_config: HermesConfig,
) -> WorkflowOutput:
    """Run the workflow with the given input state and configuration.
    Ensures the vector store is initialized before running.

    Args:
        input_state: The initial input for the workflow, typically ClassifierInput.
        hermes_config: The Hermes configuration object.

    Returns:
        A dictionary containing the final state of the workflow.
    """
    # First, ensure vector store is initialized
    # This is crucial for the inquiry responder to work
    print("Ensuring vector store is initialized before running workflow...")
    get_vector_store()

    # Ensure the configuration includes HermesConfig under the 'configurable' key
    runnable_config_obj = RunnableConfig(configurable={"hermes_config": hermes_config})

    # Create a typed config for the LangGraph StateGraph
    runnable_config: RunnableConfig = runnable_config_obj  # type: ignore

    # Run the workflow with the email from the input state and config
    # Create an OverallState with the email
    print(f"Running workflow for email {input_state.email.email_id}...")

    result = await workflow.ainvoke(input=input_state, config=runnable_config)

    if result["errors"]:
        raise Exception(result["errors"])

    print(f"Workflow completed for email {input_state.email.email_id}")

    # Convert the result to an OverallState
    if isinstance(result, dict):
        final_state = WorkflowOutput.model_validate(result)
    else:
        # If result is already an OverallState, use it directly
        final_state = result

    return final_state
