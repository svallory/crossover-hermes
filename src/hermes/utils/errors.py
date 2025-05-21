from typing import Dict, Any, Optional, Literal, TypeVar, Union

from src.hermes.model.error import Error

from src.hermes.model.enums import Agents
from src.hermes.types import ErrorReturn, WorkflowNodeOutput

SpecificAgent = TypeVar('SpecificAgent', bound=Agents)
OutputType = TypeVar('OutputType')

def create_node_response(
    agent: SpecificAgent,
    output_or_error: OutputType | Exception
) -> WorkflowNodeOutput[SpecificAgent, OutputType]:
    """
    Creates a standardized response dictionary for a workflow node (agent).

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
        return {
            "errors": {
                agent: Error(message=str(output_or_error), source=agent)
            }
        }
    else:
        # Success case (assuming output_or_error is OutputType)
        # Return the success structure
        return {agent: output_or_error}
