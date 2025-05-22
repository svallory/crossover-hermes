"""DEPRECATED: Error models have been moved to errors.py.

This module is maintained for backward compatibility only and will be removed in a future version.
"""

import warnings
from typing import Any

from pydantic import BaseModel, Field

# Issue deprecation warning
warnings.warn(
    "The error.py module is deprecated. Use errors.py instead.",
    DeprecationWarning,
    stacklevel=2,
)

class Error(BaseModel):
    """Error information for agent responses.
    
    This model provides a standardized structure for error responses
    across all agents in the system. It includes details about what
    went wrong, which component encountered the error, and additional
    context if available.
    
    Attributes:
        message: Primary error message describing what went wrong
        source: Name of the agent or component that generated the error
        details: Additional context or technical details about the error
        
    Note:
        This class is deprecated. Use the Error class from errors.py instead.
    """

    message: str = Field(description="Error message describing what went wrong")
    source: str | None = Field(default=None, description="Source of the error (e.g., agent name)")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details if available")
