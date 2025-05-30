"""Common error models used across the Hermes system."""

from pydantic import BaseModel, Field


class Error(BaseModel):
    """Represents an error that occurred during processing."""

    message: str = Field(description="Human-readable error message")
    source: str | None = Field(
        default=None, description="Source of the error (e.g., agent name)"
    )
    code: str | None = Field(
        default=None, description="Error code for programmatic handling"
    )
    exception_type: str | None = Field(
        default=None, description="The type of the exception that occurred"
    )
    details: str | None = Field(
        default=None,
        description="Additional error details and context information in natural language",
    )


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

    message: str = Field(
        description="Error message explaining why the product was not found"
    )
    query_product_id: str | None = Field(
        default=None, description="The product ID that was queried"
    )
    query_product_name: str | None = Field(
        default=None, description="The product name that was queried"
    )
