"""
Order and Inventory Tools

This module provides tools for managing product inventory and processing orders.
These tools are essential for the Order Processor agent to verify stock availability,
update stock levels as orders are processed, and handle situations where items
may be out of stock by suggesting alternatives. Additionally, a tool for extracting
promotional information from product descriptions is included here, as promotions
can affect order processing and customer communication.

Key functionalities include:
- Checking the current stock quantity for a given product.
- Updating stock quantities (decrementing when an order is fulfilled).
- Finding suitable alternative products if a requested item is out of stock.
- Extracting details of any ongoing promotions associated with a product.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import pandas as pd
import re
from langchain_core.tools import tool

from src.hermes.model import Product
from src.hermes.state import AlternativeProduct
from src.hermes.data_processing.load_data import products_df


class ProductNotFound(BaseModel):
    """Indicates that a product was not found."""

    message: str
    query_product_id: Optional[str] = None


class StockStatus(BaseModel):
    """Represents the stock status of a product."""

    product_id: str
    product_name: str
    current_stock: int
    is_available: bool = Field(
        description="True if current_stock >= requested_quantity"
    )
    requested_quantity: int = Field(
        description="The quantity requested by the customer"
    )
    expected_restock_date: Optional[str] = Field(
        default=None, description="Expected date of restock if available"
    )


class StockUpdateResult(BaseModel):
    """Result of a stock update operation."""

    product_id: str
    product_name: str
    previous_stock: int
    new_stock: int
    quantity_changed: int  # Negative for decrement, positive for increment
    status: str  # "success", "insufficient_stock", "product_not_found"
    message: Optional[str] = None


class PromotionDetails(BaseModel):
    """Details of an extracted promotion."""

    has_promotion: bool
    promotion_text: Optional[str] = None
    discount_percentage: Optional[float] = None
    buy_one_get_one: Optional[bool] = None
    free_item_name: Optional[str] = None
    limited_time: Optional[bool] = None


@tool
def check_stock(
    product_id: str, requested_quantity: int = 1
) -> Union[StockStatus, ProductNotFound]:
    """
    Check if a product is in stock and has enough inventory to fulfill an order.
    This tool validates stock levels before processing an order.

    Args:
        product_id: The Product ID to check availability for.
        requested_quantity: The number of items the customer wants to order. Defaults to 1.

    Returns:
        A StockStatus object with availability information, or ProductNotFound if the product ID is invalid.
    """
    # Standardize the product ID format
    product_id = product_id.replace(" ", "").upper()

    # Look up the product in the DataFrame
    product_data = products_df[products_df["product_id"] == product_id]

    if product_data.empty:
        return ProductNotFound(
            message=f"Product with ID '{product_id}' not found in catalog.",
            query_product_id=product_id,
        )

    product_row = product_data.iloc[0]
    current_stock = int(product_row["stock"])
    product_name = product_row["name"]

    # Check if the requested quantity is available
    is_available = current_stock >= requested_quantity

    # Determine if we have restock date information
    expected_restock_date = None
    if "restock_date" in product_row and pd.notna(product_row["restock_date"]):
        expected_restock_date = product_row["restock_date"]

    return StockStatus(
        product_id=product_id,
        product_name=product_name,
        current_stock=current_stock,
        is_available=is_available,
        requested_quantity=requested_quantity,
        expected_restock_date=expected_restock_date,
    )


@tool
def update_stock(product_id: str, quantity_to_decrement: int) -> StockUpdateResult:
    """
    Update the stock level for a product by decrementing the specified quantity.
    This should be called when an order is confirmed to be fulfilled. IMPORTANT: This tool modifies the DataFrame in place.

    Args:
        product_id: The Product ID for which to update stock.
        quantity_to_decrement: The number of items to decrement from stock (must be positive).

    Returns:
        A StockUpdateResult object detailing the outcome of the stock update.
    """
    # Validation
    if quantity_to_decrement <= 0:
        return StockUpdateResult(
            product_id=product_id,
            product_name="Unknown",
            previous_stock=0,
            new_stock=0,
            quantity_changed=0,
            status="error_invalid_quantity",
            message=f"Quantity to decrement must be positive. Got: {quantity_to_decrement}",
        )

    # Standardize the product ID format
    product_id = product_id.replace(" ", "").upper()

    # Find the product
    product_rows = products_df[products_df["product_id"] == product_id]
    if product_rows.empty:
        return StockUpdateResult(
            product_id=product_id,
            product_name="Unknown",
            previous_stock=0,
            new_stock=0,
            quantity_changed=0,
            status="product_not_found",
            message=f"Product with ID '{product_id}' not found in catalog.",
        )

    # Get current stock
    product_row_index = product_rows.index[0]
    product_name = products_df.loc[product_row_index, "name"]
    current_stock = int(products_df.loc[product_row_index, "stock"])

    # Check if we have enough stock
    if current_stock < quantity_to_decrement:
        return StockUpdateResult(
            product_id=product_id,
            product_name=product_name,
            previous_stock=current_stock,
            new_stock=current_stock,
            quantity_changed=0,
            status="insufficient_stock",
            message=f"Insufficient stock. Requested: {quantity_to_decrement}, Available: {current_stock}",
        )

    # Update the stock
    new_stock = current_stock - quantity_to_decrement
    products_df.loc[product_row_index, "stock"] = new_stock

    return StockUpdateResult(
        product_id=product_id,
        product_name=product_name,
        previous_stock=current_stock,
        new_stock=new_stock,
        quantity_changed=-quantity_to_decrement,
        status="success",
        message=f"Stock updated successfully. New stock level: {new_stock}",
    )


@tool
def find_alternatives_for_oos(
    original_product_id: str, limit: int = 2
) -> Union[List[AlternativeProduct], ProductNotFound]:
    """
    Find and suggest in-stock alternative products if a requested item is out of stock.
    This helps provide customers with options when their desired item isn't available.

    Args:
        original_product_id: The Product ID for which to find alternatives.
        limit: Maximum number of alternatives to suggest. Defaults to 2.

    Returns:
        A list of AlternativeProduct objects with suggested alternatives, or ProductNotFound if the original product ID is invalid.
    """
    # First, check if the original product exists
    original_product_data = products_df[
        products_df["product_id"] == original_product_id
    ]
    if original_product_data.empty:
        return ProductNotFound(
            message=f"Original product with ID '{original_product_id}' not found in catalog.",
            query_product_id=original_product_id,
        )

    # Get details of the original product
    original_product = original_product_data.iloc[0]
    original_name = original_product["name"]
    original_category = original_product["category"]

    # Find products in the same category with stock > 0
    alternatives_df = products_df[
        (products_df["category"] == original_category)
        & (products_df["product_id"] != original_product_id)
        & (products_df["stock"] > 0)
    ]

    # If no alternatives found, return empty result
    if alternatives_df.empty:
        return [
            AlternativeProduct(
                original_product_id=original_product_id,
                original_product_name=original_name,
                product_id="",
                product_name="",
                stock_available=0,
                reason="No alternatives with available stock found in the same category.",
            )
        ]

    # Sort alternatives by relevance - here we're using stock amount as a simple proxy
    # In a real system, this could use more sophisticated similarity metrics
    alternatives_df = alternatives_df.sort_values(by="stock", ascending=False)

    # Take top alternatives up to the limit
    results = []
    for _, alt_row in alternatives_df.head(limit).iterrows():
        alt_product_id = alt_row["product_id"]
        alt_name = alt_row["name"]
        alt_stock = int(alt_row["stock"])
        alt_price = None
        if "price" in alt_row and pd.notna(alt_row["price"]):
            alt_price = float(alt_row["price"])

        # Generate reason for the alternative
        reason = f"Same category ({original_category}) with available stock ({alt_stock} items)."

        # Add to results
        results.append(
            AlternativeProduct(
                original_product_id=original_product_id,
                original_product_name=original_name,
                product_id=alt_product_id,
                product_name=alt_name,
                stock_available=alt_stock,
                price=alt_price,
                reason=reason,
            )
        )

    return results


@tool
def extract_promotion(
    product_description: str, product_name: Optional[str] = None
) -> PromotionDetails:
    """
    Extract details of any special promotions mentioned in a product's description.
    This helps identify discounts, BOGO offers, free items, etc. to include in customer responses.

    Args:
        product_description: The full text description of the product.
        product_name: Optional name of the product for context.

    Returns:
        A PromotionDetails object indicating if a promotion is found and its details.
    """
    # Default result if no promotion found
    result = PromotionDetails(has_promotion=False)

    # Exit early if no description
    if not product_description:
        return result

    # Lowercase for case-insensitive matching
    description_lower = product_description.lower()

    # Check for common promotion patterns
    # 1. Discount percentages
    discount_patterns = [
        r"(\d+)%\s+off",  # e.g., "25% off"
        r"save\s+(\d+)%",  # e.g., "save 30%"
        r"discount\s+of\s+(\d+)%",  # e.g., "discount of 15%"
    ]

    for pattern in discount_patterns:
        discount_match = re.search(pattern, description_lower)
        if discount_match:
            result.has_promotion = True
            result.discount_percentage = float(discount_match.group(1))
            result.promotion_text = extract_promotion_text(
                product_description, discount_match
            )
            break

    # 2. BOGO offers
    bogo_patterns = [
        r"buy\s+one\s*,?\s*get\s+one",  # e.g., "buy one, get one"
        r"bogo",
        r"two\s+for\s+the\s+price\s+of\s+one",  # e.g., "two for the price of one"
    ]

    for pattern in bogo_patterns:
        if re.search(pattern, description_lower):
            result.has_promotion = True
            result.buy_one_get_one = True
            if (
                not result.promotion_text
            ):  # Don't overwrite if we already found a discount
                result.promotion_text = extract_promotion_text(
                    product_description, re.search(pattern, description_lower)
                )
            break

    # 3. Free items
    free_item_pattern = r"free\s+([\w\s]+)"  # e.g., "free matching beanie"
    free_match = re.search(free_item_pattern, description_lower)
    if free_match:
        result.has_promotion = True
        result.free_item_name = free_match.group(1).strip()
        if not result.promotion_text:
            result.promotion_text = extract_promotion_text(
                product_description, free_match
            )

    # 4. Limited time offers
    limited_patterns = [
        r"limited[\s-]time",
        r"for\s+a\s+limited\s+time",
        r"limited\s+offer",
        r"sale\s+ends",
    ]

    for pattern in limited_patterns:
        if re.search(pattern, description_lower):
            result.has_promotion = True
            result.limited_time = True
            break

    # If we found a promotion but couldn't extract text, use a generic message
    if result.has_promotion and not result.promotion_text:
        if product_name:
            result.promotion_text = f"Special promotion available for {product_name}!"
        else:
            result.promotion_text = "Special promotion available for this product!"

    return result


def extract_promotion_text(description: str, match) -> str:
    """Helper function to extract the full sentence containing a promotion."""
    if not match:
        return ""

    # Find the sentence containing the matched promotion
    start_pos = match.start()
    end_pos = match.end()

    # Look for sentence boundaries
    sentence_start = max(0, description.rfind(".", 0, start_pos) + 1)
    if sentence_start == 0:  # No period found, try exclamation
        sentence_start = max(0, description.rfind("!", 0, start_pos) + 1)

    sentence_end = description.find(".", end_pos)
    if sentence_end == -1:  # No period found, try exclamation
        sentence_end = description.find("!", end_pos)
    if sentence_end == -1:  # Still not found, use end of string
        sentence_end = len(description)

    # Extract and clean the sentence
    promotion_text = description[sentence_start : sentence_end + 1].strip()

    return promotion_text


""" {cell}
### Order Tools Implementation Notes

The order tools provide essential functionality for inventory management and order processing:

1. **Stock Management**: 
   - `check_stock`: Verifies if a product has enough inventory for a requested quantity
   - `update_stock`: Decrements stock when an order is fulfilled, with validation to prevent errors

2. **Out-of-Stock Handling**:
   - `find_alternatives_for_oos`: Suggests alternative products when an item is unavailable
   - This improves customer satisfaction by offering options instead of just saying "out of stock"

3. **Promotion Detection**:
   - `extract_promotion`: Uses regex pattern matching to identify different types of promotions:
     - Percentage discounts (e.g., "25% off")
     - Buy-one-get-one offers
     - Free items
     - Limited-time offers
   - The promotion information is included in customer responses

4. **Error Handling**: Each tool includes comprehensive validation and returns structured error objects:
   - `ProductNotFound`: When a requested product doesn't exist
   - Status codes in `StockUpdateResult`: For various operational outcomes

5. **Helper Functions**: The `extract_promotion_text` helper extracts full sentences containing promotions for natural-sounding responses.

These tools are designed to be called by the Order Processor agent when processing customer order requests, ensuring accurate inventory management and detailed order information.

**Scalability Note**: While pandas DataFrames are suitable for the current scale of this project, for significantly larger product catalogs (e.g., 100,000+ products), direct DataFrame operations for every lookup/update, especially stock updates, might become a performance bottleneck. In such production scenarios, a dedicated database (SQL or NoSQL) for structured product data and stock management, used in conjunction with the vector store, would be a more scalable approach.
"""
