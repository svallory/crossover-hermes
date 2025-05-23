This file, `order.py`, defines the Pydantic data models used to represent customer orders and their line items within the Hermes system. These models are crucial for structuring the data processed by agents involved in order fulfillment, particularly the Fulfiller agent.

Key models defined:
-   `OrderLineStatus`: An enumeration that tracks the processing status of individual items within an order: `CREATED` and `OUT_OF_STOCK`. This provides type-safe status tracking for each line item.

-   `OrderLine`: Represents a single item in a customer order. This model serves dual purposes as both input to the order processing system (with minimal fields) and output after processing (with additional fields populated). Key fields include:
    - Core fields: `product_id`, `description`, `quantity` (minimum 1)
    - Price fields: `base_price` (original price), `unit_price` (final price after discounts), `total_price` (quantity × unit_price)
    - Status and inventory: `status` (using `OrderLineStatus`), `stock` (current stock level)
    - Promotion fields: `promotion_applied` flag, `promotion_description`, detailed `promotion` spec
    - `alternatives`: List of `AlternativeProduct` suggestions if the item is unavailable

-   `Order`: Represents the complete customer order with processing results. Key fields include:
    - `email_id`: ID of the originating email
    - `overall_status`: One of "created", "out_of_stock", "partially_fulfilled", or "no_valid_products"
    - `lines`: List of `OrderLine` objects representing all items
    - Summary fields: `total_price`, `total_discount`
    - `message`: Additional processing information
    - `stock_updated`: Flag indicating if inventory levels were modified

Architecturally, these models serve as the standardized data format for exchanging order information within the Hermes workflow. They define the structure for how order details are parsed from emails, how processing results (like stock checks, pricing, and promotions) are stored and communicated, and how the final state of the order is represented. The models are designed to support both initial order parsing and enriched results after agent processing, ensuring consistent data flow between agents and reliable order fulfillment tracking.

[Link to source file](../../../src/hermes/model/order.py) 