"""Pydantic models for the product resolver agent."""

from typing import Any

from pydantic import BaseModel, Field

from src.hermes.agents.classifier.models import ProductMention
from src.hermes.model.product import Product

class ResolvedProductsOutput(BaseModel):
    """Output model for the product resolver function."""

    resolved_products: list[Product] = Field(
        default_factory=list,
        description="Products that were successfully resolved from mentions",
    )

    unresolved_mentions: list[ProductMention] = Field(
        default_factory=list,
        description="Product mentions that could not be resolved to catalog products",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the resolution process",
    )

    @property
    def resolution_rate(self) -> float:
        """Calculate the percentage of products that were successfully resolved."""
        total_mentions = len(self.resolved_products) + len(self.unresolved_mentions)
        if total_mentions == 0:
            return 1.0  # If no products to resolve, count as 100% successful
        return len(self.resolved_products) / total_mentions
