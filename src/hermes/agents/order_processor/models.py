"""
Pydantic models for the order processor agent.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any, Union
from enum import Enum

from src.hermes.model import Product
from src.hermes.state import AlternativeProduct


class OrderItemStatus(str, Enum):
    """Status of an order item."""

    CREATED = "created"
    OUT_OF_STOCK = "out_of_stock"


class OrderedItem(BaseModel):
    """A single item in a processed order."""

    product_id: str = Field(description="The unique identifier for the product")
    product_name: str = Field(description="The name of the product")
    quantity: int = Field(ge=1, description="The quantity ordered")
    status: OrderItemStatus = Field(description="The status of this order item")
    price: Optional[float] = Field(default=None, description="Price per unit if available")
    total_price: Optional[float] = Field(default=None, description="Total price for this item")
    available_stock: int = Field(description="Current stock level for this product")
    alternatives: List[AlternativeProduct] = Field(
        default_factory=list,
        description="Alternative products suggested if this item is out of stock",
    )
    promotion: Optional[Union[Dict[str, str], str]] = Field(
        default=None,
        description="Any promotion details associated with this product, either as a dictionary or a simple string",
    )


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


class OrderProcessorInput(BaseModel):
    """Input data for the order processor function."""

    email_analysis: Dict[str, Any] = Field(description="Analysis of the customer email containing the order request")
    email_id: Optional[str] = Field(default=None, description="The ID of the email containing this order request")


class OrderProcessorOutput(BaseModel):
    """Output data for the order processor function."""

    order_result: ProcessedOrder = Field(description="The complete result of processing the order request")
