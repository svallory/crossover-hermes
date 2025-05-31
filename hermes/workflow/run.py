"""Entry point for running the Hermes workflow.
This initializes the vector store and runs the workflow.
"""

from langchain_core.runnables import RunnableConfig

from hermes.config import HermesConfig
from hermes.data.vector_store import get_vector_store
from hermes.utils.logger import logger, get_agent_logger

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
    logger.info(get_agent_logger("Workflow", "Ensuring vector store is initialized..."))
    get_vector_store()

    # Ensure the configuration includes HermesConfig under the 'configurable' key
    runnable_config_obj = RunnableConfig(configurable={"hermes_config": hermes_config})

    # Create a typed config for the LangGraph StateGraph
    runnable_config: RunnableConfig = runnable_config_obj  # type: ignore

    # Run the workflow with the email from the input state and config
    # Create an OverallState with the email
    logger.info(
        get_agent_logger(
            "Workflow",
            f"Running workflow for email [cyan]{input_state.email.email_id}[/cyan]...",
        )
    )

    result = await workflow.ainvoke(input=input_state, config=runnable_config)

    if result["errors"]:
        # Log the error details before raising the exception
        for agent_name_enum, error_obj in result["errors"].items():
            agent_name_str = (
                agent_name_enum.value.capitalize()
                if hasattr(agent_name_enum, "value")
                else str(agent_name_enum)
            )
            logger.error(
                get_agent_logger(
                    "Workflow",
                    f"Error in [bold red]{agent_name_str}[/bold red] for email [cyan]{input_state.email.email_id}[/cyan]: {error_obj.message}",
                ),
                exc_info=False,
            )
        raise Exception(
            f"Workflow failed for email {input_state.email.email_id}. Errors: {result['errors']}"
        )

    logger.info(
        get_agent_logger(
            "Workflow",
            f"Workflow completed for email [cyan]{input_state.email.email_id}[/cyan]",
        )
    )

    # Convert the result to an OverallState
    if isinstance(result, dict):
        final_state = WorkflowOutput.model_validate(result)
    else:
        # If result is already an OverallState, use it directly
        final_state = result

    return final_state
