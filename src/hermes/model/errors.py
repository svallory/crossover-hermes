"""Common error models used across the Hermes system."""

from typing import Any

from pydantic import BaseModel, Field


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
    """

    message: str = Field(description="Error message describing what went wrong")
    source: str | None = Field(default=None, description="Source of the error (e.g., agent name)")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details if available")


class ProductNotFound(BaseModel):
    """Indicates that a product was not found in the catalog.
    
    This error is raised when a product reference cannot be resolved
    to an actual product in the catalog, either because the ID doesn't exist
    or because the descriptive information is insufficient for a match.
    
    Attributes:
        message: Explanation of why the product couldn't be found
        query_product_id: The product ID that was searched for, if provided
        query_product_name: The product name that was searched for, if provided
    """

    message: str = Field(description="Error message explaining why the product was not found")
    query_product_id: str | None = Field(default=None, description="The product ID that was queried")
    query_product_name: str | None = Field(default=None, description="The product name that was queried") 