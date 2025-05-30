from typing import TypeVar
import traceback

from ..workflow.types import WorkflowNodeOutput
from hermes.model.enums import Agents
from hermes.model.errors import Error

SpecificAgent = TypeVar("SpecificAgent", bound=Agents)
OutputType = TypeVar("OutputType")


def create_node_response(
    agent: SpecificAgent, output_or_error: OutputType | Exception
) -> WorkflowNodeOutput[SpecificAgent, OutputType]:
    """Creates a standardized response dictionary for a workflow node (agent).

    Args:
        agent (SpecificAgent): The specific agent enum member producing the response.
        output_or_error (OutputType | Exception): The successful output of the agent or an exception.

    Returns:
        AgentOutput[SpecificAgent, OutputType]: A dictionary formatted for LangGraph state updates.
                                               Either {agent: output} or {"errors": {agent: error}}.

    Raises:
        TypeError: If output_or_error is neither OutputType nor Exception.

    """
    if isinstance(output_or_error, Exception):
        # Error case
        # Create and return the error structure
        error_details = output_or_error.__dict__
        if (
            hasattr(output_or_error, "__traceback__")
            and output_or_error.__traceback__ is not None
        ):
            error_details["traceback"] = "".join(
                traceback.format_tb(output_or_error.__traceback__)
            )

        return {
            "errors": {
                agent: Error(
                    message=str(output_or_error),
                    source=agent.value,
                    exception_type=output_or_error.__class__.__name__,
                    details=error_details,
                )
            }
        }
    else:
        # Success case (assuming output_or_error is OutputType)
        # Return the success structure
        return {agent: output_or_error}
