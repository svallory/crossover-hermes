from typing import Literal, TypeVar, TypeAlias

from ..model.enums import Agents
from ..model.errors import Error

# Type for standardized agent return values
SpecificAgent = TypeVar("SpecificAgent", bound=Agents)
OutputType = TypeVar("OutputType")

# Generic agent output type that combines success and error cases
WorkflowNodeOutput: TypeAlias = (
    dict[SpecificAgent, OutputType]
    | dict[Literal["errors"], dict[SpecificAgent, Error]]
)
