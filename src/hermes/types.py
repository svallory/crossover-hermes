from typing import Any, Generic, Literal, TypeVar

from .model.enums import Agents
from .model.error import Error

# Type for standardized agent return values
SpecificAgent = TypeVar("SpecificAgent", bound=Agents)
OutputType = TypeVar("OutputType")

# Define common error return type
ErrorReturn = dict[Literal["errors"], dict[SpecificAgent, Error]]

# Generic agent output type that combines success and error cases
WorkflowNodeOutput = dict[SpecificAgent, OutputType] | ErrorReturn[SpecificAgent]

# Type variable for singleton metaclass
T = TypeVar("T")


class SingletonMeta(type, Generic[T]):
    """Metaclass for implementing the singleton pattern."""

    _instances: dict[type, Any] = {}

    def __call__(cls, *args, **kwargs) -> T:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
