The `vector_store.py` file implements a singleton class `VectorStore` responsible for managing interactions with the ChromaDB vector store in Hermes. This comprehensive module provides vector-based product search capabilities essential for semantic product discovery.

**Key Features:**
- **Singleton Pattern**: Uses `SingletonMeta` to ensure only one vector store instance exists
- **Flexible Storage**: Supports both in-memory and persistent ChromaDB storage modes
- **Configuration Integration**: Uses `HermesConfig` for API keys, storage paths, and embedding model settings
- **Batch Processing**: Handles large product catalogs efficiently with configurable batch sizes (default 500)
- **OpenAI Embeddings**: Integrates with OpenAI's embedding models (text-embedding-3-small, text-embedding-ada-002, text-embedding-3-large)

**Core Methods:**
- `_get_vector_store()`: Initializes or loads existing vector store with intelligent fallback handling
- `_create_vector_store()`: Creates new vector store from Google Sheets product data with batch processing
- `search_products_by_description()`: Performs semantic search using natural language queries with optional filtering
- `find_similar_products()`: Finds products similar to a reference product using embedding similarity
- `similarity_search_with_score()`: Returns search results with similarity scores for ranking
- `convert_to_product_model()`: Converts ChromaDB metadata to Pydantic Product models with robust type handling

**Advanced Capabilities:**
- Automatic database persistence and recovery
- Category mapping for test data compatibility
- Season parsing from various formats including "All seasons"
- Flexible metadata handling for extensibility
- Distance-to-similarity score conversion for intuitive ranking

This component is crucial for enabling semantic search and retrieval of products within the Hermes system, supporting agents like the Stockkeeper and Advisor in finding relevant products based on natural language queries, product similarity, and complex filtering criteria.

[Link to source file](../../../src/hermes/data_processing/vector_store.py) 