"""
Pydantic models for the order processor agent.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

from src.hermes.agents.classifier.models import ClassifierInput, ClassifierOutput
from .order import OrderedItem


class ProcessedOrder(BaseModel):
    """Complete result of processing an order request."""

    email_id: str = Field(description="The ID of the email containing this order request")

    overall_status: Literal["created", "out_of_stock", "partially_fulfilled", "no_valid_products"] = Field(
        description="The overall status of this order"
    )

    ordered_items: List[OrderedItem] = Field(
        default_factory=list,
        description="List of items in this order with their statuses",
    )

    total_price: Optional[float] = Field(default=None, description="Total price for all available items in the order")

    message: Optional[str] = Field(
        default=None,
        description="Additional information about this order processing result",
    )

    stock_updated: bool = Field(
        default=False,
        description="Whether stock levels have been updated for this order",
    )


class FulfillerInput(ClassifierInput):
    """Input data for the order processor function."""

    classifier: ClassifierOutput = Field(description="The output of the email analyzer")


class FulfillerOutput(BaseModel):
    """Output data for the order processor function."""

    order_result: ProcessedOrder = Field(description="The complete result of processing the order request")
