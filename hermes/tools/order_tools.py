import pandas as pd  # type: ignore
from enum import Enum
from pydantic import BaseModel
import logging  # Add logging import

from hermes.data.load_data import load_products_df
from hermes.model.errors import ProductNotFound
# Removed: from hermes.tools.catalog_tools import update_product_stock as catalog_update_product_stock

logger = logging.getLogger(__name__)  # Initialize logger


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

    # Load the products DataFrame
    products_df = load_products_df()

    if (
        products_df is None
    ):  # Should ideally be handled by load_products_df raising an error
        logger.error(
            "Products DataFrame is not loaded. Cannot update stock for product_id: %s",
            product_id,
        )
        return StockUpdateStatus.PRODUCT_NOT_FOUND

    # Find the product
    product_rows = products_df[products_df["product_id"] == product_id]
    if product_rows.empty:
        logger.warning(
            "Product ID '%s' not found in DataFrame for stock update attempt.",
            product_id,
        )
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
        logger.error(
            "Error converting stock value for product ID '%s'. Value: %s",
            product_id,
            current_stock_val,
            exc_info=True,
        )
        current_stock = 0  # Treat as 0 if conversion fails

    # Check if we have enough stock
    if current_stock < quantity_to_decrement:
        logger.info(
            "Insufficient stock for product ID '%s'. Requested: %d, Available: %d",
            product_id,
            quantity_to_decrement,
            current_stock,
        )
        return StockUpdateStatus.INSUFFICIENT_STOCK

    # Calculate the new stock level
    new_stock_level = current_stock - quantity_to_decrement

    # Ensure new_stock_level is non-negative (already done in previous logic, but good to be explicit)
    if new_stock_level < 0:
        logger.warning(
            "Calculated new_stock_level for product ID '%s' is %d (decrementing %d from %d). Setting to 0.",
            product_id,
            new_stock_level,
            quantity_to_decrement,
            current_stock,
        )
        new_stock_level = 0

    # Directly update the stock in the DataFrame
    products_df.loc[product_row_index, "stock"] = new_stock_level
    logger.info(
        "Stock for product ID '%s' updated to %d in the in-memory DataFrame (decremented by %d from %d).",
        product_id,
        new_stock_level,
        quantity_to_decrement,
        current_stock,
    )

    return StockUpdateStatus.SUCCESS
