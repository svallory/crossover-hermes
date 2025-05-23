This file defines the data structures for products within the Hermes system, providing comprehensive models for product representation and alternative product recommendations.

Key models defined:
-   `Product`: Represents a single product with comprehensive details:
    - `product_id`: Unique identifier for the product
    - `name`: Product name
    - `description`: Detailed product description
    - `category`: Product category (using `ProductCategory` enum)
    - `product_type`: Fundamental product type within the general category
    - `stock`: Number of items currently in stock
    - `seasons`: List of seasons the product is ideal for (using `Season` enum)
    - `price`: Product price
    - `metadata`: Optional additional metadata dictionary
    - `promotion`: Optional active promotion specification (using `PromotionSpec`)
    - `promotion_text`: Optional descriptive text for the active promotion

-   `AlternativeProduct`: Represents a recommended alternative product when the requested item is unavailable or for upselling:
    - `product`: The `Product` being recommended as an alternative
    - `similarity_score`: Numerical similarity score to the requested product
    - `reason`: Explanation for why this product is recommended as an alternative

These models are fundamental to how products are represented and managed throughout the Hermes workflow. The `Product` model serves as the core data structure for catalog items and includes promotion integration for dynamic pricing. The `AlternativeProduct` model enables intelligent product recommendations with scoring and reasoning, which is particularly useful for the Stockkeeper and Fulfiller agents when handling out-of-stock scenarios.

[Link to source file](../../../src/hermes/model/product.py) 