# Summary of src/hermes/data_processing/vector_store.py

The `vector_store.py` file implements a singleton class `VectorStore` responsible for managing interactions with the ChromaDB vector store in Hermes. This module provides vector-based product search capabilities essential for semantic product discovery.

Key components and responsibilities:
- **Singleton Pattern Implementation**: Uses a metaclass (`SingletonMeta`) to ensure that only one instance of the `VectorStore` can exist throughout the application lifecycle. This is crucial for managing a shared resource like a database connection.
- **Flexible Storage Options**: Supports both in-memory ChromaDB instances (for development/testing) and persistent storage (for production), configurable via `HermesConfig`.
- **Configuration-Driven**: Leverages `HermesConfig` to obtain necessary parameters such as API keys (e.g., for OpenAI), storage paths, and embedding model names.
- **Batch Processing for Efficiency**: When creating or updating the vector store, it processes product data in configurable batches (defaulting to 500) to handle large catalogs efficiently and avoid overwhelming the embedding service or database.
- **Embedding Model Integration**: Integrates with OpenAI's text embedding models (e.g., `text-embedding-3-small`, `text-embedding-ada-002`, `text-embedding-3-large`) to generate vector representations of product descriptions.
- **Core Vector Store Operations**:
  - `_get_vector_store()`: Initializes a new vector store or loads an existing one from persistent storage. Includes logic to fall back to creating a new store if loading fails.
  - `_create_vector_store()`: Populates a new vector store by fetching product data (likely from Google Sheets via other modules), generating embeddings, and adding them to ChromaDB in batches.
- **Semantic Search Functionality**:
  - `search_products_by_description()`: Allows users to perform semantic searches for products using natural language queries. It can also apply filters (e.g., based on category, season) to narrow down results.
  - `find_similar_products()`: Finds products that are semantically similar to a given reference product by comparing their embeddings.
  - `similarity_search_with_score()`: A lower-level search method that returns results along with their similarity scores, enabling ranked outputs.
- **Data Conversion**: Includes a `convert_to_product_model()` method to transform the metadata retrieved from ChromaDB search results into structured Pydantic `Product` models, ensuring type safety and consistency.
- **Advanced Capabilities**:
    - Manages automatic persistence and recovery of the database when in persistent mode.
    - Includes logic for category mapping, potentially to align test data or different data source schemas with the `ProductCategory` enum.
    - Parses season information from various textual formats (e.g., "All seasons", "Spring/Summer") into the `Season` enum.
    - Provides flexible metadata handling, allowing for future extensions to product information stored in the vector database.
    - Converts raw distance metrics from vector similarity searches into more intuitive similarity scores.

Architecturally, `vector_store.py` is a critical component for enabling intelligent product discovery in Hermes. It abstracts the complexities of interacting with a vector database (ChromaDB) and the embedding models. By providing a robust API for creating, populating, and querying the vector store, it empowers other agents (like Stockkeeper and Advisor) to find relevant products based on semantic meaning rather than just keyword matching. The singleton pattern ensures consistent access to the vector store, and its configurable nature allows for adaptability across different environments and data scales.

[Link to source file](../../../src/hermes/data_processing/vector_store.py) 