from typing import TypedDict, Optional


class OrderItem(TypedDict):
    """Dictionary representing an item in an order."""
    product_id: str
    description: str
    base_price: float
    quantity: int


class OrderResult(TypedDict):
    """Dictionary representing the result of processing an ordered item."""
    product_id: str
    description: str
    quantity: int
    unit_price: float
    total_price: float
    promotion_applied: bool
    promotion_description: Optional[str]