"""Pydantic models for the product resolver agent."""

from pydantic import BaseModel, Field

from hermes.agents.classifier import ClassifierOutput
from hermes.model.email import CustomerEmail, ProductMention
from hermes.model.product import Product


class StockkeeperInput(BaseModel):
    """Input model for the product resolver function."""

    email: CustomerEmail = Field(description="Email object containing the email_id")

    classifier: ClassifierOutput = Field(
        description="Complete EmailAnalysisResult from the analyzer"
    )


class StockkeeperOutput(BaseModel):
    """Output model for the product resolver function."""

    resolved_products: list[Product] = Field(
        default_factory=list,
        description="Products that were successfully resolved from mentions",
    )

    unresolved_mentions: list[ProductMention] = Field(
        default_factory=list,
        description="Product mentions that could not be resolved to catalog products",
    )

    metadata: str | None = Field(
        default=None,
        description="Metadata about the resolution process in natural language",
    )

    @property
    def resolution_rate(self) -> float:
        """Calculate the percentage of products that were successfully resolved."""
        total_mentions = len(self.resolved_products) + len(self.unresolved_mentions)
        if total_mentions == 0:
            return 1.0  # If no products to resolve, count as 100% successful
        return len(self.resolved_products) / total_mentions
