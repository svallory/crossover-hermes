# Summary of hermes/tools/promotion_tools.py

This module, `promotion_tools.py`, provides a specialized tool for applying promotions to a list of ordered items and constructing a comprehensive `Order` object. Its primary function is to calculate discounts and adjust item prices based on defined promotion specifications.

## Key Components and Responsibilities:

-   **Input Processing:** Takes a JSON string as input, which should contain:
    -   `ordered_items`: A list of dictionaries, each representing an item with `product_id`, `description`, `quantity`, and `base_price`.
    -   `promotion_specs`: A list of promotion specifications. These can be dictionaries or `PromotionSpec` objects.
    -   `email_id`: An identifier for the email associated with the order.
-   **Pydantic Models:** Relies heavily on Pydantic models from `hermes.model.order` and `hermes.model.promotions`:
    -   `OrderLine`: Used to structure each line item in the order, including applied promotion details.
    -   `Order`: The final output object, encapsulating all order lines, total discount, total price, and other order-level information.
    -   `PromotionSpec`: Defines the structure of a promotion, including its conditions (e.g., `min_quantity`, `product_combination`, `applies_every`) and effects (e.g., `apply_discount`, `free_items`, `free_gift`).
-   **Promotion Logic:** The core `apply_promotion` tool iterates through ordered items and applies relevant promotions based on `PromotionSpec` data.
    -   Handles percentage and fixed amount discounts.
    -   Handles "free items" promotions (e.g., buy X get Y free) by adjusting the effective unit price.
    -   Notes free gifts in the promotion description.
    -   Currently has placeholder logic for more complex conditions like `product_combination` and `applies_every`, indicating areas for future enhancement.
-   **Error Handling:** If the input JSON is invalid or there's an attribute error during parsing, it returns a minimal `Order` object with an "error" `email_id` and "no_valid_products" status.
-   **Output Generation:** Constructs and returns an `Order` object, populated with `OrderLine` instances for each item, reflecting any applied promotions, and calculated totals (total discount, total price).

## Tool Definition:

-   `apply_promotion(tool_input: str) -> Order`:
    -   The single tool provided by this module.
    -   Processes ordered items and applies promotions based on `promotion_specs`.
    -   Calculates discounts (percentage, fixed, free items) and adjusts unit prices.
    -   Aggregates total discount and final order price.
    -   Returns a comprehensive `Order` object.

## Relationships:

-   **Order and Promotion Models:** Tightly coupled with `Order`, `OrderLine` from `hermes.model.order` and `PromotionSpec` from `hermes.model.promotions`. These models define the data structures it consumes and produces.
-   **Agent Usage:** This tool is likely used by an agent responsible for finalizing order details after items have been selected and before payment or fulfillment (e.g., a Composer agent or part of the Fulfiller's finalization step).
-   **Upstream Data:** Expects `ordered_items` (potentially from a cart or user selection) and `promotion_specs` (which might be retrieved from a promotions database or configuration).

Architecturally, `promotion_tools.py` centralizes the complex logic of applying various types of promotions to an order. By taking structured item and promotion data as input and producing a fully calculated `Order` object, it ensures consistent and accurate application of discounts and promotional offers within the Hermes system.

[Link to source file](../../../../hermes/tools/promotion_tools.py) 