# Summary of src/hermes/model/order.py

This file, `order.py`, defines the Pydantic data models used to represent customer orders, their constituent line items, and related status information within the Hermes system. These models are fundamental for structuring order-related data that is created, processed, and manipulated by various agents, particularly the Fulfiller agent during order processing and inventory management.

Key Pydantic models and enums defined:
-   **`OrderLineStatus` (Enum)**: An enumeration (`Enum`) that defines the possible processing statuses for individual line items within an order. Common statuses include:
    -   `CREATED`: Indicates the order line has been successfully created and is awaiting further processing (e.g., stock check).
    -   `OUT_OF_STOCK`: Indicates that the product requested in this line item is currently out of stock.
    This enum provides type-safe and explicit status tracking for each item in an order.

-   **`OrderLine` (Pydantic Model)**: Represents a single item (a line) within a customer's order. This model is designed to be versatile, serving both as an input structure when an order is initially parsed (potentially with minimal fields) and as an enriched output structure after processing by agents (with additional fields populated, such as price, stock status, and promotions). Key fields include:
    -   Core item details: `product_id` (str), `description` (str), `quantity` (PositiveInt, must be at least 1).
    -   Pricing information: `base_price` (float, original price of the item), `unit_price` (float, the final price per unit after any discounts or promotions), `total_price` (float, calculated as `quantity * unit_price`).
    -   Status and inventory: `status` (using the `OrderLineStatus` enum), `stock` (Optional[int], current available stock level for the product).
    -   Promotion details: `promotion_applied` (bool, flag indicating if a promotion was applied to this line), `promotion_description` (Optional[str]), and potentially a more detailed `promotion` specification (e.g., using a `PromotionSpec` model from `promotions.py`).
    -   Alternatives: `alternatives` (Optional[List[`AlternativeProduct`]], a list of suggested alternative products if the original item is unavailable or if upselling is desired).

-   **`Order` (Pydantic Model)**: Represents the complete customer order, aggregating multiple `OrderLine` objects and providing an overall summary of the order's status and processing results. Key fields include:
    -   `email_id` (str): An identifier for the originating email or customer interaction that led to this order.
    -   `overall_status` (str): A string indicating the consolidated status of the entire order (e.g., "created", "out_of_stock" if all items are unavailable, "partially_fulfilled" if some items are out of stock, "fulfilled", "no_valid_products" if no processable items were found).
    -   `lines` (List[`OrderLine`]): A list of `OrderLine` objects, representing all the items included in the order.
    -   Summary calculations: `total_price` (float, the sum of `total_price` for all lines), `total_discount` (Optional[float], the total discount amount applied across the order).
    -   `message` (Optional[str]): A field for any additional messages, notes, or information related to the processing of the order (e.g., explanations for out-of-stock items, confirmation messages).
    -   `stock_updated` (bool): A flag indicating whether inventory levels were modified as a result of processing this order.

Architecturally, the models in `order.py` serve as the canonical data interchange format for all order-related information within the Hermes workflow. They define a clear and consistent structure for how order details are initially captured (e.g., parsed from customer emails), how they are enriched with processing results (such as stock availability checks, price calculations, and promotion applications by agents like the Fulfiller), and how the final state of an order is represented and communicated. The design of these models to support both initial raw data and subsequently enriched data facilitates a smooth and reliable flow of information between different agents and stages of the order fulfillment process, contributing to accurate tracking and processing.

[Link to source file](../../../src/hermes/model/order.py) 