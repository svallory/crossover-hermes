from typing import Dict, Literal, TypeVar, Union, Type, Any, Generic
from .model.enums import Agents
from .model.error import Error

# Type for standardized agent return values
SpecificAgent = TypeVar('SpecificAgent', bound=Agents)
OutputType = TypeVar('OutputType')

# Define common error return type
ErrorReturn = Dict[Literal["errors"], Dict[SpecificAgent, Error]]

# Generic agent output type that combines success and error cases
WorkflowNodeOutput = Union[Dict[SpecificAgent, OutputType], ErrorReturn[SpecificAgent]]

# Type variable for singleton metaclass
T = TypeVar('T')

class SingletonMeta(type, Generic[T]):
    """Metaclass for implementing the singleton pattern."""
    _instances: Dict[Type, Any] = {}
    
    def __call__(cls, *args, **kwargs) -> T:
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]