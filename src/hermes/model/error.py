from typing import Any

from pydantic import BaseModel, Field

class Error(BaseModel):
    """Error information for agent responses."""

    message: str = Field(description="Error message describing what went wrong")
    source: str | None = Field(default=None, description="Source of the error (e.g., agent name)")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details if available")
