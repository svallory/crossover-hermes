# Summary of hermes/tools/catalog_tools.py

This module, `catalog_tools.py`, provides a suite of tools for interacting with the product catalog within the Hermes system. Its primary function is to enable agents to retrieve, search, and filter product information using various methods.

## Key Components and Responsibilities:

-   **Product Data Loading:** Utilizes `hermes.data_processing.load_data.load_products_df` to load the product catalog from a CSV file (`product_catalog.csv`) into a pandas DataFrame. It also initializes and uses a `VectorStore` for semantic search capabilities.
-   **Product Model:** Interacts with the `Product` model (from `hermes.model.product`) and related Pydantic models like `FuzzyMatchResult`, `ProductSearchQuery`, `ProductSearchResult`, and `SimilarProductQuery`. It also uses `ProductCategory` and `Season` enums from `hermes.model`.
-   **Error Handling:** Returns `ProductNotFound` (from `hermes.model.errors`) when products are not found or when issues occur during data retrieval or processing.
-   **Tool Definitions:** Each core functionality is exposed as a Langchain `@tool`.

    -   `find_product_by_id(tool_input: str) -> Product | ProductNotFound`:
        -   Retrieves detailed product information using an exact Product ID.
        -   Input: JSON string with `product_id`.
        -   Standardizes product ID (uppercase, no spaces).
        -   Maps DataFrame row to `Product` model.
    -   `find_product_by_name(product_name: str, *, threshold: float = 0.8, top_n: int = 3) -> list[FuzzyMatchResult] | ProductNotFound`:
        -   Finds products by name using fuzzy matching (via `thefuzz` library).
        -   Useful for typos or slight name variations.
        -   Input: `product_name`, optional `threshold` and `top_n`.
        -   Returns a list of `FuzzyMatchResult` objects.
    -   `search_products_by_description(tool_input: str) -> list[Product] | ProductNotFound`:
        -   Performs semantic search on product descriptions using the `VectorStore`.
        -   Input: JSON string with `query` (search text) and optional `top_k`.
        -   Converts search results from `VectorStore` to `Product` objects.
    -   `find_related_products(tool_input: str) -> list[Product] | ProductNotFound`:
        -   Identifies related or complementary products, primarily by leveraging semantic similarity of product descriptions via the `VectorStore`.
        -   Input: JSON string with `product_id` (of the original product) and optional `top_k`.
        -   Excludes the original product from the results.
    -   `resolve_product_reference(tool_input: str) -> Product | ProductNotFound`:
        -   Resolves a potentially ambiguous product reference (which could be an ID or a name) to a specific product.
        -   Input: JSON string with `product_reference`.
        -   First attempts `find_product_by_id`. If not found or reference isn't ID-like, falls back to `find_product_by_name`.
    -   `filtered_product_search(input: str, *, search_type: str = "description", top_k: int = 3, category: str | None = None, season: str | None = None, min_stock: int | None = None, min_price: float | None = None, max_price: float | None = None) -> list[Product] | ProductNotFound`:
        -   Searches for products based on a query string and allows filtering by various attributes.
        -   Input: `input` (query string), `search_type` ("description" or "name"), `top_k`, and optional filters for `category`, `season`, `min_stock`, `min_price`, `max_price`.
        -   If `search_type` is "description", uses semantic search.
        -   If `search_type` is "name", uses fuzzy name matching.
        -   Applies filters after the initial search.

## Relationships:

-   **Data Source:** Relies on `product_catalog.csv` for product data, loaded via `hermes.data_processing.load_data`.
-   **Vector Embeddings:** Utilizes `hermes.data_processing.vector_store.VectorStore` for semantic search capabilities, which in turn would depend on an embedding model and a vector database.
-   **Core Models:** Heavily uses `Product` and other Pydantic models from `hermes.model` for structuring data and return types.
-   **Agent Usage:** These tools are designed to be used by various Hermes agents (e.g., Advisor, Fulfiller) that need to access or query product catalog information to respond to customer inquiries, process orders, or provide recommendations.

Architecturally, `catalog_tools.py` serves as the primary interface for the Hermes system to access and query detailed information about its products, supporting both exact lookups and more nuanced search functionalities.

[Link to source file](../../../../hermes/tools/catalog_tools.py) 