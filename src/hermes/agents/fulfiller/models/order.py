from enum import Enum

from pydantic import Field

from src.hermes.model.product import AlternativeProduct, Product

from .promotions import PromotionSpec

class OrderedItemStatus(str, Enum):
    """Status of an order item."""

    CREATED = "created"
    OUT_OF_STOCK = "out_of_stock"


class OrderedItem(Product):
    """A single item in a processed order that extends the Product model."""

    quantity: int = Field(ge=1, description="The quantity ordered")
    status: OrderedItemStatus = Field(description="The status of this order item")
    total_price: float | None = Field(default=None, description="Total price for this item")

    alternatives: list[AlternativeProduct] = Field(
        default_factory=list,
        description="Alternative products suggested if this item is out of stock",
    )
    promotion: PromotionSpec | None = Field(
        default=None,
        description="Specification for any promotion associated with this product",
    )
