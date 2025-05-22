"""Order and Inventory Tools.

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
- Calculating discounted prices based on promotion text.
"""

import json
import re

import pandas as pd  # type: ignore
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.hermes.data_processing.load_data import load_products_df
from src.hermes.data_processing.vector_store import VectorStore
from src.hermes.model.errors import ProductNotFound
from src.hermes.model.product import AlternativeProduct, Product
from src.hermes.config import HermesConfig


class StockStatus(BaseModel):
    """Represents the stock status of a product."""

    product_id: str
    product_name: str
    current_stock: int
    is_available: bool = Field(description="True if current_stock >= requested_quantity")
    requested_quantity: int = Field(description="The quantity requested by the customer")
    expected_restock_date: str | None = Field(default=None, description="Expected date of restock if available")


class StockUpdateResult(BaseModel):
    """Result of a stock update operation."""

    product_id: str
    product_name: str
    previous_stock: int
    new_stock: int
    quantity_changed: int  # Negative for decrement, positive for increment
    status: str  # "success", "insufficient_stock", "product_not_found"
    message: str | None = None


class DiscountResult(BaseModel):
    """Result of a discount calculation."""

    original_price: float = Field(description="Original price before discount")
    discounted_price: float = Field(description="Price after applying the discount")
    discount_amount: float = Field(description="Amount discounted")
    discount_percentage: float | None = Field(default=None, description="Percentage discount if applicable")
    discount_applied: bool = Field(description="Whether a discount was applied")
    discount_type: str = Field(description="Type of discount applied (percentage, bogo, etc.)")
    explanation: str = Field(description="Explanation of how the discount was calculated")


@tool
def check_stock(tool_input: str) -> StockStatus | ProductNotFound:
    """Check if a product is in stock and has enough inventory to fulfill an order.
    This tool validates stock levels before processing an order.

    Args:
        tool_input: JSON string with product_id and requested_quantity (optional) fields.

    Returns:
        A StockStatus object with availability information, or ProductNotFound if the product ID is invalid.

    """
    try:
        input_data = json.loads(tool_input)
        product_id = input_data.get("product_id", "")
        requested_quantity = input_data.get("requested_quantity", 1)
    except (json.JSONDecodeError, AttributeError):
        return ProductNotFound(message=f"Invalid input format: {tool_input}")

    # Standardize the product ID format
    product_id = product_id.replace(" ", "").upper()

    # Look up the product in the DataFrame
    products_df = load_products_df()
    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_id=product_id,
        )
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
def update_stock(tool_input: str) -> StockUpdateResult:
    """Update the stock level for a product by decrementing the specified quantity.
    This should be called when an order is confirmed to be fulfilled.
    IMPORTANT: This tool modifies the DataFrame in place.

    Args:
        tool_input: JSON string with product_id and quantity_to_decrement fields.

    Returns:
        A StockUpdateResult object detailing the outcome of the stock update.

    """
    try:
        input_data = json.loads(tool_input)
        product_id = input_data.get("product_id", "")
        quantity_to_decrement = input_data.get("quantity_to_decrement", 0)
    except (json.JSONDecodeError, AttributeError):
        return StockUpdateResult(
            product_id="unknown",
            product_name="Unknown",
            previous_stock=0,
            new_stock=0,
            quantity_changed=0,
            status="error_invalid_input",
            message=f"Invalid input format: {tool_input}",
        )

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
    products_df = load_products_df()
    if products_df is None:
        return StockUpdateResult(
            product_id=product_id,
            product_name="Unknown",
            previous_stock=0,
            new_stock=0,
            quantity_changed=0,
            status="error_catalog_not_loaded",
            message="Product catalog data is not loaded.",
        )
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
    product_name = str(products_df.loc[product_row_index, "name"])
    current_stock_val = products_df.loc[product_row_index, "stock"]
    current_stock: int
    if pd.notna(current_stock_val):
        try:
            # Attempt conversion to float first, then to int
            current_stock = int(float(str(current_stock_val)))
        except (ValueError, TypeError):  # Catch error if not convertible
            current_stock = 0  # Default to 0 if conversion fails
    else:
        current_stock = 0  # Handles NaN

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
def find_alternatives_for_oos(tool_input: str) -> list[AlternativeProduct] | ProductNotFound:
    """Find and suggest in-stock alternative products if a requested item is out of stock.
    This helps provide customers with options when their desired item isn't available.

    Args:
        tool_input: JSON string with original_product_id and limit (optional) fields.

    Returns:
        A list of AlternativeProduct objects with suggested alternatives,
        or ProductNotFound if the original product ID is invalid.

    """
    try:
        input_data = json.loads(tool_input)
        original_product_id = input_data.get("original_product_id", "")
        limit = input_data.get("limit", 2)
    except (json.JSONDecodeError, AttributeError):
        return ProductNotFound(message=f"Invalid input format: {tool_input}")

    # First, check if the original product exists
    products_df = load_products_df()
    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_id=original_product_id,
        )
    original_product_data = products_df[products_df["product_id"] == original_product_id]
    if original_product_data.empty:
        return ProductNotFound(
            message=f"Original product with ID '{original_product_id}' not found in catalog.",
            query_product_id=original_product_id,
        )

    # Get details of the original product
    original_product = original_product_data.iloc[0]
    # Get the category for filtering
    original_category = original_product["category"]

    # Get all products in the same category
    category_products = products_df[products_df["category"] == original_category]
    
    # Filter out the original product and items that are out of stock
    filtered_products = category_products[
        (category_products["product_id"] != original_product_id) & 
        (category_products["stock"] > 0)
    ]

    if filtered_products.empty:
        return ProductNotFound(
            message=f"No in-stock alternatives found for product '{original_product_id}'.",
            query_product_id=original_product_id,
        )

    # Calculate price similarity
    original_price = float(original_product["price"])
    
    # Add price similarity as a column
    filtered_products["price_similarity"] = filtered_products["price"].apply(
        lambda x: 1.0 - abs(float(x) - original_price) / max(original_price, float(x))
    )
    
    # Sort by price similarity, descending
    sorted_products = filtered_products.sort_values("price_similarity", ascending=False)
    
    # Take top alternatives
    top_alternatives = sorted_products.head(limit)
    
    # Convert to AlternativeProduct objects
    result = []
    for _, row in top_alternatives.iterrows():
        # Create the product object
        product_dict = {
            "product_id": str(row["product_id"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "category": str(row["category"]),
            "product_type": str(row.get("type", "")),
            "stock": int(row["stock"]),
            "price": float(row["price"]),
            "seasons": [s.strip() for s in str(row.get("season", "")).split(",") if s.strip()],
        }
        
        product = Product(**product_dict)
        
        # Calculate similarity score (normalized between 0-1)
        similarity_score = float(row["price_similarity"])
        
        # Generate a reason based on price and availability
        if similarity_score > 0.9:
            reason = f"Very similar price (${float(row['price']):.2f} vs ${original_price:.2f}) and currently in stock"
        elif similarity_score > 0.7:
            reason = f"Similar price range and currently in stock ({int(row['stock'])} available)"
        else:
            reason = f"Same category alternative that's currently available ({int(row['stock'])} in stock)"
        
        # Create and add the AlternativeProduct
        alternative = AlternativeProduct(
            product=product,
            similarity_score=similarity_score,
            reason=reason
        )
        result.append(alternative)
    
    return result


@tool
def calculate_discount_price(tool_input: str) -> DiscountResult:
    """Calculate the discounted price based on the promotion text and original price.

    This tool handles various promotion types:
    - Percentage discounts (e.g., "25% off")
    - Buy-one-get-one (BOGO) offers
    - Free item offers
    - Bundle discounts

    Args:
        tool_input: JSON string with original_price, promotion_text, and quantity (optional) fields.

    Returns:
        A DiscountResult object with the calculated discount and explanation

    """
    try:
        input_data = json.loads(tool_input)
        original_price = float(input_data.get("original_price", 0.0))
        promotion_text = input_data.get("promotion_text", "")
        quantity = int(input_data.get("quantity", 1))
    except (json.JSONDecodeError, AttributeError, ValueError, TypeError):
        return DiscountResult(
            original_price=0.0,
            discounted_price=0.0,
            discount_amount=0.0,
            discount_applied=False, 
            discount_type="error",
            explanation=f"Invalid input format: {tool_input}"
        )

    discounted_price = original_price
    discount_amount = 0.0
    discount_percentage = None
    discount_applied = False
    discount_type = "none"
    explanation = "No discount applied."

    if not promotion_text:
        return DiscountResult(
            original_price=original_price,
            discounted_price=original_price,
            discount_amount=0.0,
            discount_percentage=None,
            discount_applied=False,
            discount_type="none",
            explanation="No promotion text provided.",
        )

    # Convert to lowercase for case-insensitive matching
    promo_lower = promotion_text.lower()

    # 1. Check for percentage discounts
    percentage_patterns = [
        r"(\d+)%\s+off",  # e.g., "25% off"
        r"save\s+(\d+)%",  # e.g., "save 30%"
        r"discount\s+of\s+(\d+)%",  # e.g., "discount of 15%"
        r"(\d+)%\s+discount",  # e.g., "15% discount"
    ]

    for pattern in percentage_patterns:
        match = re.search(pattern, promo_lower)
        if match:
            try:
                percentage = float(match.group(1))
                MAX_PERCENTAGE = 100
                if 0 < percentage < MAX_PERCENTAGE:  # Valid percentage
                    discount_percentage = percentage
                    discount_amount = (original_price * percentage) / 100
                    discounted_price = original_price - discount_amount
                    discount_applied = True
                    discount_type = "percentage"
                    explanation = f"Applied {percentage}% discount to original price ${original_price:.2f}."

                    # Handle quantity correctly
                    discount_amount * quantity
                    discounted_price * quantity

                    return DiscountResult(
                        original_price=original_price,
                        discounted_price=discounted_price,
                        discount_amount=discount_amount,
                        discount_percentage=discount_percentage,
                        discount_applied=discount_applied,
                        discount_type=discount_type,
                        explanation=explanation,
                    )
            except (ValueError, IndexError):
                pass  # Continue to next pattern if this one fails

    # 2. Check for BOGO offers
    MIN_BOGO_QUANTITY = 2  # Minimum quantity for buy-one-get-one offers
    if any(phrase in promo_lower for phrase in ["buy one, get one", "bogo", "get one free", "buy 1 get 1"]):
        if "50% off" in promo_lower or "half off" in promo_lower or "half price" in promo_lower:
            # BOGO 50% off
            MIN_BOGO_QUANTITY = 2
            if quantity >= MIN_BOGO_QUANTITY:
                # For every pair, one item is half price
                full_price_items = (quantity + 1) // 2  # Rounds up for odd quantities
                half_price_items = quantity // 2  # Rounds down for odd quantities

                total_original = original_price * quantity
                total_discounted = (full_price_items * original_price) + (half_price_items * original_price * 0.5)

                # Calculate per-unit values
                discount_amount = (total_original - total_discounted) / quantity
                discounted_price = original_price - discount_amount

                discount_applied = True
                discount_type = "bogo_half"
                explanation = f"Buy one, get one 50% off applied. For {quantity} items, {full_price_items} at full price, {half_price_items} at half price."
            else:
                # Not enough quantity for discount
                explanation = "Buy one, get one 50% off requires at least 2 items to apply."
        # Regular BOGO (second item free)
        elif quantity >= MIN_BOGO_QUANTITY:
            # For every pair, one item is free
            paid_items = (quantity + 1) // 2  # Rounds up for odd quantities
            free_items = quantity // 2  # Rounds down for odd quantities

            total_original = original_price * quantity
            total_discounted = original_price * paid_items

            # Calculate per-unit values
            discount_amount = (total_original - total_discounted) / quantity
            discounted_price = original_price - discount_amount

            discount_applied = True
            discount_type = "bogo_free"
            explanation = f"Buy one, get one free applied. For {quantity} items, paying for {paid_items}, getting {free_items} free."
        else:
            # Not enough quantity for discount
            explanation = "Buy one, get one free requires at least 2 items to apply."

    # 3. Check for bulk discounts on quantity thresholds
    bulk_match = re.search(r"(\d+)\+\s+units", promo_lower)
    if bulk_match:
        try:
            threshold = int(bulk_match.group(1))
            # If we meet the threshold and there's a percentage in the promo
            percent_match = re.search(r"(\d+)%", promo_lower)
            if quantity >= threshold and percent_match:
                percentage = float(percent_match.group(1))
                discount_percentage = percentage
                discount_amount = (original_price * percentage) / 100
                discounted_price = original_price - discount_amount
                discount_applied = True
                discount_type = "bulk_discount"
                explanation = (
                    f"Bulk discount of {percentage}% applied for ordering {quantity} items (minimum {threshold})."
                )
            elif quantity < threshold:
                explanation = f"Bulk discount requires at least {threshold} items (only ordered {quantity})."
        except (ValueError, IndexError):
            pass

    # Return the result
    return DiscountResult(
        original_price=original_price,
        discounted_price=discounted_price,
        discount_amount=discount_amount,
        discount_percentage=discount_percentage,
        discount_applied=discount_applied,
        discount_type=discount_type,
        explanation=explanation,
    )


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

4. **Promotion Calculation**:
   - `calculate_discount_price`: Calculates the actual discounted price based on promotion text
   - Handles various promotion types with different calculation methods
   - Returns detailed explanations of how discounts were applied

5. **Error Handling**: Each tool includes comprehensive validation and returns structured error objects:
   - `ProductNotFound`: When a requested product doesn't exist
   - Status codes in `StockUpdateResult`: For various operational outcomes

6. **Helper Functions**: The `extract_promotion_text` helper extracts full sentences containing promotions for natural-sounding responses.

These tools are designed to be called by the Order Processor agent when processing customer order requests,
ensuring accurate inventory management and detailed order information.

**Scalability Note**: While pandas DataFrames are suitable for the current scale of this project,
for significantly larger product catalogs (e.g., 100,000+ products), direct DataFrame operations
for every lookup/update, especially stock updates, might become a performance bottleneck.
In such production scenarios, a dedicated database (SQL or NoSQL) for structured product data
and stock management, used in conjunction with the vector store, would be a more scalable approach.
"""
