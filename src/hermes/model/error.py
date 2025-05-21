from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class Error(BaseModel):
    """Error information for agent responses."""

    message: str = Field(description="Error message describing what went wrong")
    source: Optional[str] = Field(default=None, description="Source of the error (e.g., agent name)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details if available")