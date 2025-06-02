"""Pydantic models for the product resolver agent."""

from pydantic import BaseModel, Field
from typing import Tuple

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
    """Output model for the product resolver function.
    Provides candidate products for each mention, rather than definitively resolving them.
    Downstream agents (Fulfiller, Advisor) are responsible for selecting from these candidates.
    """

    # resolved_products: list[Product] = Field(
    #     default_factory=list,
    #     description="Products that were successfully resolved (exact ID or L2 distance <= MAX_ACCEPTABLE_L2_DISTANCE) from mentions",
    # )

    candidate_products_for_mention: list[Tuple[ProductMention, list[Product]]] = Field(
        default_factory=list,
        description="For each successfully processed product mention, provides the original mention and a list of potential product candidates found by catalog tools (L2 distance <= MAX_VECTOR_SEARCH_L2_DISTANCE), along with their L2 distances in metadata. Empty list of candidates if resolve_product_mention found none meeting criteria.",
    )

    # products_needing_clarification: list[Product] = Field(
    #     default_factory=list,
    #     description="Products resolved with moderate confidence, requiring customer clarification",
    # )

    unresolved_mentions: list[ProductMention] = Field(
        default_factory=list,
        description="Product mentions for which `resolve_product_mention` returned ProductNotFound or an empty list even before L2 filtering in catalog_tools, indicating no plausible raw candidates were found.",
    )

    exact_id_misses: list[ProductMention] = Field(
        default_factory=list,
        description="Product mentions from the input that had a product_id specified, but for which no exact match was found in the catalog, even if semantic alternatives were found.",
    )

    metadata: str | None = Field(
        default=None,
        description="Metadata about the resolution process in natural language",
    )

    @property
    def resolution_rate(self) -> float:
        """Calculate the percentage of mentions for which at least one candidate was found."""
        total_mentions_input = len(self.candidate_products_for_mention) + len(
            self.unresolved_mentions
        )
        if total_mentions_input == 0:
            return 1.0

        # A mention is considered "resolved" in the sense of having candidates if it appears in candidate_products_for_mention
        # and the list of candidates for it is not empty.
        mentions_with_candidates = 0
        for _, candidate_list in self.candidate_products_for_mention:
            if candidate_list:  # Check if the list of Product candidates is not empty
                mentions_with_candidates += 1

        return (
            mentions_with_candidates / total_mentions_input
            if total_mentions_input > 0
            else 1.0
        )
