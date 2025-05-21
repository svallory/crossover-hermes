"""Entry point for running the Hermes workflow.
This initializes the vector store and runs the workflow.
"""

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.hermes.agents.classifier.models import ClassifierInput
from src.hermes.agents.workflow.graph import workflow
from src.hermes.agents.workflow.states import OverallState
from src.hermes.config import HermesConfig
from src.hermes.data_processing.vector_store import VectorStore

async def run_workflow(
    input_state: ClassifierInput,
    hermes_config: HermesConfig,
) -> OverallState:
    """Run the workflow with the given input state and configuration.
    Ensures the vector store is initialized before running.

    Args:
        input_state: The input state for the workflow.
        hermes_config: The configuration for the workflow.

    Returns:
        The final state of the workflow.

    """
    # Initialize the vector store using the singleton
    VectorStore(hermes_config=hermes_config)

    # Prepare the runnable config
    config: dict[str, dict[str, Any]] = {
        "configurable": {
            "hermes_config": hermes_config,
        }
    }

    # Create a typed config for the LangGraph StateGraph
    runnable_config: RunnableConfig = config  # type: ignore

    # Run the workflow with the input state and config
    print(f"Running workflow for email {input_state.email_id}...")
    result = await workflow.ainvoke(input_state, config=runnable_config)

    print(f"Workflow completed for email {input_state.email_id}")

    # Convert the result to an OverallState
    if isinstance(result, dict):
        final_state = OverallState.model_validate(result)
    else:
        # If result is already an OverallState, use it directly
        final_state = result

    return final_state
