This file, `promotions.py`, defines the Pydantic data models used to specify and structure promotions within the Hermes system. These models are essential for agents, particularly the Fulfiller, that need to understand and apply promotional rules to customer orders.

Key models and concepts defined:
-   `Condition` and `Effect` Literals: Define the possible types of conditions that can trigger a promotion (`min_quantity`, `applies_every`, `product_combination`) and the types of effects that can result (`free_items`, `free_gift`, `apply_discount`).
-   `DiscountSpec`: A model detailing how a discount should be applied, including:
    - `to_product_id`: Optional product ID to apply discount to (if omitted, applies to all)
    - `type`: Type of discount ("percentage", "fixed", or "bogo_half")
    - `amount`: Discount amount (must be greater than 0)
-   `PromotionConditions`: A strongly typed model aggregating different condition types with validation:
    - `min_quantity`: Minimum quantity required (≥1)
    - `applies_every`: How many items the promotion applies to (≥1)
    - `product_combination`: List of product IDs that must all be present (minimum 1 item)
    - Includes validation to ensure at least one condition is specified
-   `PromotionEffects`: A strongly typed model aggregating different effect types with validation:
    - `free_items`: Number of free items of the same product (≥1)
    - `free_gift`: Description of a free gift (non-empty string)
    - `apply_discount`: Discount specification using `DiscountSpec`
    - Includes validation to ensure at least one effect is specified
-   `PromotionSpec`: The main model representing a complete promotion that combines `PromotionConditions` with `PromotionEffects`. It includes comprehensive validation to ensure both conditions and effects are properly specified and provides JSON schema examples for documentation.

Architecturally, `promotions.py` provides a standardized, structured, and type-safe way to define complex promotional rules with robust validation. This allows the system to parse, validate, and programmatically apply promotions consistently. The separation of conditions and effects into distinct models within the `PromotionSpec` promotes clarity and modularity, making it easier for agents to interpret and execute promotional logic. The comprehensive validation ensures data integrity and prevents invalid promotion configurations. This is crucial for the accurate calculation of order totals and the communication of promotion details to customers.

[Link to source file](../../../src/hermes/model/promotions.py) 