from typing import Generic, TypeVar, Dict

from ..model.enums import Agents
from ..model.errors import Error

# Type for standardized agent return values
SpecificAgent = TypeVar("SpecificAgent", bound=Agents)
OutputType = TypeVar("OutputType")

# Generic agent output type that combines success and error cases
# WorkflowNodeOutput: TypeAlias = (
#     dict[SpecificAgent, OutputType]
#     | dict[Literal["errors"], dict[SpecificAgent, Error]]
# )


class WorkflowNodeOutput(
    Generic[SpecificAgent, OutputType], Dict[SpecificAgent, OutputType | None]
):
    """Workflow node output that may contain agent results and/or errors.

    Can contain:
    - Agent keys (e.g., 'classifier': ClassifierOutput)
    - errors: Dict[str, Error] for any errors

    Both are optional, allowing flexible combinations.
    """

    errors: Dict[SpecificAgent, Error] | None
