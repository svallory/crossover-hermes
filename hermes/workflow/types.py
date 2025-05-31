from typing import Dict, TypeVar

from ..model.errors import Error

from ..model.enums import Agents

# Type for standardized agent return values
SpecificAgent = TypeVar("SpecificAgent", bound=Agents)
OutputType = TypeVar("OutputType")

# Generic agent output type that combines success and error cases
# WorkflowNodeOutput: TypeAlias = dict[SpecificAgent, OutputType]

WorkflowNodeOutput = Dict[SpecificAgent, OutputType | Error]

# class WorkflowNodeOutput(
#     Generic[SpecificAgent, OutputType], Dict[SpecificAgent, OutputType | None]
# ):
#     """Workflow node output that may contain agent results and/or errors.

#     Can contain:
#     - Agent keys (e.g., 'classifier': ClassifierOutput)
#     - errors: Dict[str, Error] for any errors

#     Both are optional, allowing flexible combinations.
#     """

#     errors: Dict[SpecificAgent, Error | Exception] | None
