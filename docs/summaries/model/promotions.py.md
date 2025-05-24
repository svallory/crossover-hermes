# Summary of src/hermes/model/promotions.py

This file, `promotions.py`, defines a suite of Pydantic data models and supporting `Literal` types used to specify, structure, and validate complex promotional rules within the Hermes system. These models are critical for agents, particularly the Fulfiller, that need to accurately interpret and apply promotions to customer orders, ensuring correct pricing and communication of offers.

Key Pydantic models, Literals, and concepts defined:
-   **`ConditionLiteral` and `EffectLiteral` (Literals)**: These define the allowed string values for types of promotion conditions and effects, ensuring type safety and restricting inputs to known types.
    -   `ConditionLiteral`: Includes values like `"min_quantity"`, `"applies_every"`, `"product_combination"`.
    -   `EffectLiteral`: Includes values like `"free_items"`, `"free_gift"`, `"apply_discount"`.

-   **`DiscountSpec` (Pydantic Model)**: A model specifically detailing how a discount should be applied. Key fields:
    -   `to_product_id` (Optional[str]): The ID of the product the discount applies to. If `None`, the discount may apply more broadly (e.g., to the item triggering the promotion or all items in an order, depending on context).
    -   `type` (Literal["percentage", "fixed", "bogo_half"]): The type of discount (e.g., percentage off, fixed amount off, buy-one-get-one-half-price).
    -   `amount` (PositiveFloat): The magnitude of the discount (e.g., 20 for 20%, 10.00 for a fixed amount). Must be greater than 0.

-   **`PromotionConditions` (Pydantic Model)**: A strongly-typed model that aggregates various possible conditions that must be met to trigger a promotion. It uses Pydantic validators to ensure logical consistency (e.g., at least one condition must be specified). Key fields:
    -   `min_quantity` (Optional[PositiveInt]): Minimum quantity of a product that must be purchased (e.g., buy 2 of item X).
    -   `applies_every` (Optional[PositiveInt]): Specifies if the promotion applies to every Nth item (e.g., get a discount on every 3rd item X).
    -   `product_combination` (Optional[List[str]]): A list of product IDs that must all be present in the order for the promotion to apply (e.g., buy product X and product Y together).
    -   Includes a root validator (`model_validator`) to ensure that at least one condition field is actually set.

-   **`PromotionEffects` (Pydantic Model)**: A strongly-typed model that aggregates various possible effects or benefits that a customer receives when promotion conditions are met. It also uses Pydantic validators. Key fields:
    -   `free_items` (Optional[PositiveInt]): Number of free items of the same product that are given (e.g., buy 2, get 1 free).
    -   `free_gift` (Optional[str]): A description of a free gift that is provided (e.g., "Free Tote Bag").
    -   `apply_discount` (Optional[`DiscountSpec`]): The discount to be applied, using the `DiscountSpec` model.
    -   Includes a root validator (`model_validator`) to ensure at least one effect field is set.

-   **`PromotionSpec` (Pydantic Model)**: The main, top-level model representing a complete promotion. It combines `PromotionConditions` and `PromotionEffects` and includes comprehensive validation. Key fields:
    -   `description` (str): A human-readable description of the promotion.
    -   `conditions` (`PromotionConditions`): The conditions that trigger this promotion.
    -   `effects` (`PromotionEffects`): The effects or benefits of this promotion.
    -   It likely includes validators to ensure that both `conditions` and `effects` are properly specified and are logically sound together. The original summary mentions JSON schema examples for documentation, implying good developer support.

Architecturally, `promotions.py` provides a robust, standardized, structured, and type-safe framework for defining potentially complex promotional rules. The use of Pydantic models with built-in validation ensures data integrity and prevents the configuration of invalid or ambiguous promotions. This clear definition allows agents (like the Fulfiller) to programmatically parse, validate, and apply these rules consistently and accurately. The separation of conditions and effects into distinct, composable models (`PromotionConditions`, `PromotionEffects`) within the overarching `PromotionSpec` promotes clarity, modularity, and maintainability, making it easier to define new promotions and for the system to interpret and execute the promotional logic. This is crucial for accurate order total calculations, inventory adjustments (if free items are involved), and clear communication of applied promotions to customers.

[Link to source file](../../../src/hermes/model/promotions.py) 