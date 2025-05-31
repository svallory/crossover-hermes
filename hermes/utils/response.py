from typing import TypeVar
import traceback

from hermes.model.enums import Agents
from hermes.model.errors import Error
from ..workflow.types import WorkflowNodeOutput

SpecificAgent = TypeVar("SpecificAgent", bound=Agents)
OutputType = TypeVar("OutputType")


def create_node_response(
    agent: SpecificAgent, response: OutputType | Exception | Error
) -> WorkflowNodeOutput[SpecificAgent, OutputType]:
    """Creates a standardized response dictionary for a workflow node (agent).

    Args:
        agent (SpecificAgent): The specific agent enum member producing the response.
        output_or_error (OutputType | Exception): The successful output of the agent or an exception.

    Returns:
        A dictionary formatted for LangGraph state updates.
        Either {agent.value: output} or {"errors": {agent.value: error_obj}}.

    Raises:
        TypeError: If output_or_error is neither OutputType nor Exception.

    """

    if isinstance(response, Error):
        return {agent: response}

    if isinstance(response, Exception):
        return {
            agent: Error(
                message=str(response),
                exception_type=type(response).__name__,
                source=str(agent.value if hasattr(agent, "value") else agent),
                details=traceback.format_exc(),
            )
        }

    return {agent: response}
