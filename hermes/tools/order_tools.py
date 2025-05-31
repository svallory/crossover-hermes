import pandas as pd  # type: ignore
from enum import Enum
from pydantic import BaseModel

from hermes.data.load_data import load_products_df
from hermes.model.errors import ProductNotFound


class StockStatus(BaseModel):
    """Represents the stock status of a product."""

    is_available: bool
    current_stock: int


class StockUpdateStatus(str, Enum):
    """Status of a stock update operation."""

    SUCCESS = "success"
    INSUFFICIENT_STOCK = "insufficient_stock"
    PRODUCT_NOT_FOUND = "product_not_found"


def check_stock(
    product_id: str, requested_quantity: int = 1
) -> StockStatus | ProductNotFound:
    """Check if a product is in stock and has enough inventory to fulfill an order.

    Args:
        product_id: The product ID to check stock for.
        requested_quantity: The quantity requested (default: 1).

    Returns:
        A StockStatus object with availability information, or ProductNotFound if the product ID is invalid.
    """
    # Standardize the product ID format
    product_id = product_id.replace(" ", "").upper()

    # Look up the product in the DataFrame
    products_df = load_products_df()

    product_data = products_df[products_df["product_id"] == product_id]
    if product_data.empty:
        return ProductNotFound(
            message=f"Product with ID '{product_id}' not found in catalog.",
            query_product_id=product_id,
        )

    product_row = product_data.iloc[0]
    current_stock = int(product_row["stock"])

    return StockStatus(
        is_available=current_stock >= requested_quantity,
        current_stock=current_stock,
    )


def update_stock(product_id: str, quantity_to_decrement: int) -> StockUpdateStatus:
    """Update the stock level for a product by decrementing the specified quantity.
    This should be called when an order is confirmed to be fulfilled.

    Args:
        product_id: The product ID to update stock for.
        quantity_to_decrement: The amount to decrement from current stock.

    Returns:
        A StockUpdateStatus enum indicating the outcome of the stock update.
    """
    # Standardize the product ID format
    product_id = product_id.replace(" ", "").upper()

    # Find the product
    products_df = load_products_df()

    product_rows = products_df[products_df["product_id"] == product_id]
    if product_rows.empty:
        return StockUpdateStatus.PRODUCT_NOT_FOUND

    # Get current stock
    product_row_index = product_rows.index[0]
    current_stock_val = products_df.loc[product_row_index, "stock"]

    # Handle stock conversion safely
    try:
        current_stock = (
            int(float(str(current_stock_val))) if pd.notna(current_stock_val) else 0
        )
    except (ValueError, TypeError):
        current_stock = 0

    # Check if we have enough stock
    if current_stock < quantity_to_decrement:
        return StockUpdateStatus.INSUFFICIENT_STOCK

    # Update the stock - this modifies the cached DataFrame directly
    new_stock = current_stock - quantity_to_decrement
    products_df.loc[product_row_index, "stock"] = new_stock

    return StockUpdateStatus.SUCCESS
