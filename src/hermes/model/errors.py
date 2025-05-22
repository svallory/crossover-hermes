"""Common error models used across the Hermes system."""

from pydantic import BaseModel, Field


class ProductNotFound(BaseModel):
    """Indicates that a product was not found in the catalog."""

    message: str = Field(description="Error message explaining why the product was not found")
    query_product_id: str | None = Field(default=None, description="The product ID that was queried")
    query_product_name: str | None = Field(default=None, description="The product name that was queried") 