"""Pydantic models for the order processor agent."""

from pydantic import BaseModel, Field
from typing import Tuple

from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.stockkeeper.models import StockkeeperOutput
from ...model.email import CustomerEmail, ProductMention
from hermes.model.product import Product
from hermes.model.order import Order


class FulfillerInput(BaseModel):
    """Input data for the order processor function."""

    email: CustomerEmail = Field(description="The customer email being processed")
    classifier: ClassifierOutput = Field(description="The output of the email analyzer")
    stockkeeper: StockkeeperOutput = Field(
        description="The output of the stockkeeper agent"
    )


class FulfillerOutput(BaseModel):
    """Output data for the order processor function."""

    order_result: Order = Field(
        description="The complete result of processing the order request"
    )
    unresolved_mentions: list[ProductMention] = Field(
        default_factory=list,
        description="Product mentions from the stockkeeper that were not resolved confidently enough for order processing.",
    )
    stockkeeper_metadata: str | None = Field(
        default=None,
        description="Metadata from the stockkeeper about its resolution process.",
    )
    candidate_products_for_mention: list[Tuple[ProductMention, list[Product]]] = Field(
        default_factory=list,
        description="For stockkeeper's unresolved mentions, provides the original mention and a list of potential product candidates found by catalog tools, for composer to use.",
    )
