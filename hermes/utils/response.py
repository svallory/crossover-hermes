from typing import TypeVar, cast, Any
import traceback
import json

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
        # Error case - create natural language error details
        error_details_parts = []

        # Add traceback if available
        if (
            hasattr(output_or_error, "__traceback__")
            and output_or_error.__traceback__ is not None
        ):
            traceback_str = "".join(traceback.format_tb(output_or_error.__traceback__))
            error_details_parts.append(f"Traceback: {traceback_str}")

        # Add any additional exception attributes
        exception_dict = output_or_error.__dict__
        if exception_dict:
            try:
                exception_info = json.dumps(exception_dict)
                error_details_parts.append(f"Exception details: {exception_info}")
            except (TypeError, ValueError):
                # If serialization fails, store as string representation
                error_details_parts.append(f"Exception details: {str(exception_dict)}")

        # Combine all details into a natural language string
        details_str = "; ".join(error_details_parts) if error_details_parts else None

        # Create the error response using dict casting
        error_dict: dict[str, Any] = {
            "errors": {
                agent: Error(
                    message=str(output_or_error),
                    source=agent.value,
                    exception_type=output_or_error.__class__.__name__,
                    details=details_str,
                )
            }
        }
        return cast(WorkflowNodeOutput[SpecificAgent, OutputType], error_dict)
    else:
        # Success case (assuming output_or_error is OutputType)
        # Return the success structure
        success_dict: dict[SpecificAgent, OutputType] = {agent: output_or_error}
        return cast(WorkflowNodeOutput[SpecificAgent, OutputType], success_dict)
