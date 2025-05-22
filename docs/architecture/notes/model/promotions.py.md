This file, `promotions.py`, defines the Pydantic data models used to specify and structure promotions within the Hermes system. These models are essential for agents, particularly the Fulfiller, that need to understand and apply promotional rules to customer orders.

Key models and concepts defined:
-   `Condition` and `Effect` Literals: Define the possible types of conditions that can trigger a promotion (e.g., `min_quantity`, `product_combination`) and the types of effects that can result (e.g., `free_items`, `apply_discount`).
-   `DiscountSpec`: A model detailing how a discount should be applied, including whether it applies to a specific product or the entire order, the `type` (percentage or fixed), and the discount `amount`.
-   `PromotionConditions`: A strongly typed model aggregating different condition types. It includes optional fields for `min_quantity`, `applies_every`, and `product_combination`, along with validation to ensure at least one condition is specified.
-   `PromotionEffects`: A strongly typed model aggregating different effect types. It includes optional fields for adding `free_items`, including a `free_gift` (by description), or applying a `apply_discount` (using `DiscountSpec`), with validation to ensure at least one effect is specified.
-   `PromotionSpec`: The main model representing a complete promotion. It combines a `PromotionConditions` object with a `PromotionEffects` object, defining the 'if this happens, then do this' logic of a promotion. It also includes validation to ensure both conditions and effects are specified.

Architecturally, `promotions.py` provides a standardized, structured, and type-safe way to define complex promotional rules. This allows the system to parse, validate, and programmatically apply promotions consistently. The separation of conditions and effects into distinct models within the `PromotionSpec` promotes clarity and modularity, making it easier for agents to interpret and execute promotional logic. This is crucial for the accurate calculation of order totals and the communication of promotion details to the customer.

[Link to source file](../../../../src/hermes/model/promotions.py) 