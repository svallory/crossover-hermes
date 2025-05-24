# Summary of src/hermes/model/product.py

This file, `product.py`, defines the core Pydantic data models used to represent products and alternative product recommendations within the Hermes system. These models are fundamental for structuring product information that is loaded, managed, searched, and utilized by various agents throughout the workflow, including the Stockkeeper, Fulfiller, and Advisor.

Key Pydantic models defined:
-   **`Product` (Pydantic Model)**: Represents a single product item in the catalog, encapsulating all its relevant attributes. This comprehensive model is central to how product information is stored and exchanged within the system. Key fields include:
    -   `product_id` (str): A unique identifier for the product.
    -   `name` (str): The human-readable name of the product.
    -   `description` (str): A detailed textual description of the product, often used for semantic search and by LLMs for understanding product features.
    -   `category` (`ProductCategory` enum): The category the product belongs to (e.g., `MENS_CLOTHING`, `ACCESSORIES`), using the `ProductCategory` enum defined in `model.enums` for type safety and consistency.
    -   `product_type` (Optional[str]): A more specific classification or type within the general category (e.g., "T-Shirt", "Sneaker").
    -   `stock` (int): The number of units currently available in stock. This field is critical for inventory management.
    -   `seasons` (Optional[List[`Season` enum]]): A list of seasons (e.g., `SPRING`, `WINTER`) for which the product is most suitable or available, using the `Season` enum from `model.enums`.
    -   `price` (float): The retail price of the product.
    -   `metadata` (Optional[Dict[str, Any]]): A flexible dictionary for storing any additional, unstructured metadata related to the product (e.g., supplier information, material details).
    -   `promotion` (Optional[`PromotionSpec`]): An optional field that can hold a structured `PromotionSpec` object (defined in `model.promotions`) if an active promotion applies to this product. This allows for dynamic pricing and promotion handling.
    -   `promotion_text` (Optional[str]): An optional human-readable descriptive text for any active promotion associated with the product.

-   **`AlternativeProduct` (Pydantic Model)**: Represents a product that is recommended as an alternative to another product, typically when the originally requested item is out of stock, or as part of an upselling or cross-selling strategy. Key fields include:
    -   `product` (`Product`): The actual `Product` object being recommended as an alternative. This embeds the full details of the suggested item.
    -   `similarity_score` (Optional[float]): A numerical score (e.g., between 0 and 1) indicating the degree of similarity or relevance of the alternative product to the original request. This helps in ranking alternatives.
    -   `reason` (Optional[str]): A textual explanation for why this particular product is being recommended as an alternative (e.g., "Similar style and color", "Popular alternative for out-of-stock item").

Architecturally, these Pydantic models in `product.py` provide the standardized schema for all product-related data within the Hermes system. The `Product` model is the cornerstone for representing catalog items, integrating essential details from pricing and stock to descriptive attributes and promotional information. The `AlternativeProduct` model supports intelligent recommendation capabilities, crucial for agents like the Stockkeeper and Fulfiller when dealing with inventory shortages or aiming to enhance customer experience by suggesting relevant alternatives. By defining these structures clearly, the system ensures consistent data handling across all components that interact with product information.

[Link to source file](../../../src/hermes/model/product.py) 