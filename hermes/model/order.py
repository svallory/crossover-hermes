from enum import Enum
from typing import List, Literal

from pydantic import BaseModel, Field

from .product import AlternativeProduct
from .promotions import PromotionSpec


class OrderLineStatus(str, Enum):
    """Status of an order line item."""

    CREATED = "created"
    OUT_OF_STOCK = "out of stock"


class OrderLine(BaseModel):
    """Represents a single line item in an order.

    This model serves as both input to the order processing system (with minimal fields)
    and output after processing (with additional fields populated).
    """

    # Core fields (present in initial request)
    product_id: str = Field(description="Unique identifier for the product")
    description: str = Field(description="Description of the product")
    quantity: int = Field(ge=1, description="The quantity ordered")

    # Price fields
    base_price: float = Field(
        description="Original price per unit before any discounts"
    )
    unit_price: float | None = Field(
        default=None, description="Final price per unit after discounts"
    )
    total_price: float | None = Field(
        default=None, description="Total price for this line (quantity × unit_price)"
    )

    # Status and inventory fields
    status: OrderLineStatus | None = Field(
        default=None, description="Status of this order line"
    )
    stock: int | None = Field(
        default=None, description="Current stock level for this product"
    )

    # Promotion fields
    promotion_applied: bool = Field(
        default=False, description="Whether a promotion was applied to this line"
    )
    promotion_description: str | None = Field(
        default=None, description="Description of the applied promotion"
    )
    promotion: PromotionSpec | None = Field(
        default=None,
        description="Detailed specification for any promotion associated with this product",
    )

    # Alternative product suggestions
    alternatives: List[AlternativeProduct] = Field(
        default_factory=list,
        description="Alternative products suggested if this item is out of stock",
    )


class Order(BaseModel):
    """Represents a complete customer order with processing results."""

    email_id: str = Field(
        description="The ID of the email containing this order request"
    )

    overall_status: Literal[
        "created", "out of stock", "partially_fulfilled", "no_valid_products"
    ] = Field(description="The overall status of this order")

    lines: List[OrderLine] = Field(
        default_factory=list,
        description="List of line items in this order with their statuses",
    )

    total_price: float | None = Field(
        default=None, description="Total price for all available items in the order"
    )

    total_discount: float = Field(
        default=0.0, description="Total discount amount applied to this order"
    )

    message: str | None = Field(
        default=None,
        description="Additional information about this order processing result",
    )

    stock_updated: bool = Field(
        default=False,
        description="Whether stock levels have been updated for this order",
    )
