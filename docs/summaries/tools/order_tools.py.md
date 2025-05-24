# Summary of hermes/tools/order_tools.py

This module, `order_tools.py`, provides tools for managing product inventory and aspects of order processing within the Hermes system. These tools are primarily intended for use by agents like the Fulfiller to check stock, update inventory, find alternatives for out-of-stock items, and calculate discounts.

## Key Components and Responsibilities:

-   **Product Data Interaction:** Leverages `hermes.data_processing.load_data.load_products_df` to access the product catalog DataFrame for stock levels and product details.
-   **Pydantic Models:** Defines and uses several Pydantic models for structured input and output:
    -   `StockStatus`: Represents the stock status of a product, including current stock, availability, and requested quantity.
    -   `StockUpdateResult`: Details the outcome of a stock update operation (e.g., success, insufficient stock).
    -   `DiscountResult`: Describes the result of a discount calculation, including original price, discounted price, and an explanation.
-   **Error Handling:** Uses `ProductNotFound` (from `hermes.model.errors`) for cases where a product ID is invalid or the catalog isn't loaded.
-   **Tool Definitions:** Core functionalities are exposed as Langchain `@tool` decorated functions.

    -   `check_stock(tool_input: str) -> StockStatus | ProductNotFound`:
        -   Checks if a product is in stock and has sufficient quantity.
        -   Input: JSON string with `product_id` and optional `requested_quantity`.
        -   Returns a `StockStatus` object or `ProductNotFound`.
    -   `update_stock(tool_input: str) -> StockUpdateResult`:
        -   Updates the stock level for a product, typically decrementing quantity after order fulfillment.
        -   Input: JSON string with `product_id` and `quantity_to_decrement`.
        -   **Important:** Modifies the product DataFrame in place.
        -   Returns a `StockUpdateResult` indicating the outcome.
    -   `find_alternatives_for_oos(tool_input: str) -> list[AlternativeProduct] | ProductNotFound`:
        -   Finds and suggests in-stock alternative products if a requested item is out of stock.
        -   Uses `VectorStore` (from `hermes.data_processing.vector_store`) for semantic similarity search based on the original product's description.
        -   Input: JSON string with `original_product_id` and optional `limit`.
        -   Filters alternatives to ensure they are in stock and different from the original product.
        -   Returns a list of `AlternativeProduct` objects (defined in `hermes.model.product`) or `ProductNotFound`.
    -   `calculate_discount_price(tool_input: str) -> DiscountResult`:
        -   Calculates the discounted price for a product based on promotional text found in its description or associated promotions.
        -   Input: JSON string with `product_id` and `promotional_text`.
        -   Uses regex to parse discount percentages (e.g., "X% off") or fixed amounts from the text.
        -   Returns a `DiscountResult` object.

## Relationships:

-   **Product Catalog:** Directly interacts with the product catalog data (loaded as a pandas DataFrame via `load_products_df`) to get stock levels and product details.
-   **Vector Store:** `find_alternatives_for_oos` uses `VectorStore` for finding semantically similar products, implying a dependency on an underlying vector database and embedding model.
-   **Core Models:** Uses `Product`, `AlternativeProduct`, `Season` from `hermes.model.product`, and `ProductNotFound` from `hermes.model.errors`.
-   **Configuration:** May implicitly use `HermesConfig` for settings related to vector store or other configurations.
-   **Agent Usage:** Primarily designed for the Fulfiller agent to manage inventory and order details. Other agents might use `check_stock` or `calculate_discount_price` for informational purposes.

Architecturally, `order_tools.py` is crucial for the operational side of Hermes, ensuring inventory accuracy, providing solutions for stock issues, and applying basic discount calculations. It bridges the gap between product data and the order fulfillment process.

[Link to source file](../../../../hermes/tools/order_tools.py) 