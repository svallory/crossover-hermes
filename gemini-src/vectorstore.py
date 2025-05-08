""" {cell}
## Vector Store Management

This module is responsible for setting up and managing the vector store used for
Retrieval-Augmented Generation (RAG) in the Hermes application. The primary use case
is to enable semantic search over the product catalog, allowing the Inquiry Responder
agent to find relevant products based on natural language queries from customers.

Key functionalities include:
-   **Embedding Generation**: Creating vector embeddings for product information
    (e.g., product name, description, category) using a specified embedding model
    (e.g., OpenAI's `text-embedding-ada-002`).
-   **Vector Store Initialization**: Setting up a vector database (e.g., ChromaDB)
    and populating it with the product embeddings and associated metadata.
    This includes handling persistence to disk.
-   **Similarity Search**: Providing functions to perform semantic similarity searches
    against the vector store. This will allow retrieval of the most relevant products
    based on a query vector.
-   **Metadata Filtering**: Supporting filtering of search results based on metadata
    (e.g., product category, season, price range) to refine search relevance.
    The assignment specifically mentions category-based pre-filtering for efficiency.

**Design Considerations**:
-   **Choice of Vector Store**: ChromaDB is specified in `reference-solution-spec.md`
    due to its ease of use, local persistence, and good LangChain integration.
-   **Embedding Strategy**: Embeddings will be generated for product descriptions combined
    with names and categories to capture rich semantic meaning. Product IDs will be stored
    as metadata for easy lookup of full product details after retrieval.
-   **Batching**: For initial catalog embedding, batching should be considered to improve
    efficiency and manage API rate limits if using a cloud-based embedding service.
-   **Configuration**: Relies on `HermesConfig` for parameters like the embedding model
    name, vector store path, and collection name.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import logging

# LangChain components
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

# Assuming HermesConfig is in src.config
from ..config import HermesConfig
# Assuming Product model is defined elsewhere. For now, we'll work with DataFrame directly.

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Manages the creation, loading, and querying of a Chroma vector store
    for product information.
    """
    def __init__(self, config: HermesConfig, product_catalog_df: Optional[pd.DataFrame] = None, initialize_new_store: bool = False):
        """
        Initializes the VectorStoreManager.

        Args:
            config: HermesConfig object with settings like API keys, model names, and paths.
            product_catalog_df: Optional pandas DataFrame containing the product catalog.
                                If provided and initialize_new_store is True, a new store will be built.
            initialize_new_store: If True, will attempt to build and persist a new vector store
                                 from product_catalog_df, potentially overwriting an existing one
                                 at the same path/collection. If False, attempts to load an existing store.
        """
        self.config = config
        self.embeddings_model = OpenAIEmbeddings(
            model=self.config.embedding_model_name,
            openai_api_key=self.config.llm_api_key.get_secret_value() if self.config.llm_api_key else None,
            openai_api_base=self.config.llm_base_url
        )
        
        self.vector_store_path = self.config.vector_store_path
        self.collection_name = self.config.chroma_collection_name

        logger.info(f"Initializing Chroma vector store. Path: {self.vector_store_path}, Collection: {self.collection_name}")

        if initialize_new_store:
            if product_catalog_df is not None and not product_catalog_df.empty:
                logger.info("initialize_new_store is True. Building new vector store from product catalog.")
                self._build_and_persist_store(product_catalog_df)
            elif product_catalog_df is None or product_catalog_df.empty:
                logger.warning("initialize_new_store is True, but no product_catalog_df provided or it's empty. Cannot build new store.")
                # Initialize an empty store that can be loaded or added to later
                self.vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings_model,
                    persist_directory=self.vector_store_path
                )
                self.vector_store.persist() # Persist even if empty to create the structure
            else: # product_catalog_df is not None but initialize_new_store is False
                 self._load_existing_store()
        else:
            self._load_existing_store()

    def _load_existing_store(self):
        """Loads an existing Chroma vector store from the persist_directory."""
        try:
            logger.info(f"Attempting to load existing vector store from: {self.vector_store_path} with collection: {self.collection_name}")
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings_model,
                persist_directory=self.vector_store_path
            )
            # Test if the store is populated by trying a count or a dummy query
            if self.vector_store._collection.count() == 0:
                 logger.warning(f"Loaded vector store from {self.vector_store_path}, but collection '{self.collection_name}' is empty.")
            else:
                 logger.info(f"Successfully loaded existing vector store. Collection count: {self.vector_store._collection.count()}")

        except Exception as e:
            logger.error(f"Failed to load vector store from {self.vector_store_path}: {e}. "
                         f"An empty store will be used. You might need to initialize it first.")
            # Fallback to an empty store if loading fails, so the app can still run,
            # though RAG capabilities will be limited.
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings_model,
                persist_directory=self.vector_store_path
            )
            # It's important to persist here so that subsequent attempts to load
            # find a valid (though possibly empty) Chroma structure.
            self.vector_store.persist()


    def _build_and_persist_store(self, product_catalog_df: pd.DataFrame, batch_size: int = 100):
        """Builds a new vector store from product data and persists it."""
        logger.info(f"Building new vector store. Batch size: {batch_size}")
        documents = self._create_documents_from_products(product_catalog_df)
        if not documents:
            logger.warning("No documents created from product catalog. Vector store will be empty.")
            # Initialize an empty store and persist it
            self.vector_store = Chroma.from_documents(
                documents=[], # empty list
                embedding=self.embeddings_model,
                collection_name=self.collection_name,
                persist_directory=self.vector_store_path
            )
        else:
            logger.info(f"Adding {len(documents)} documents to the vector store in batches.")
            # Chroma.from_documents handles batching internally if not explicitly managed here.
            # For very large datasets, manual batching with add_documents might be preferred.
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings_model,
                collection_name=self.collection_name,
                persist_directory=self.vector_store_path
            )
        
        self.vector_store.persist()
        logger.info(f"Vector store built and persisted at {self.vector_store_path}. Collection count: {self.vector_store._collection.count()}")


    def _create_documents_from_products(self, product_catalog_df: pd.DataFrame) -> List[Document]:
        """Converts product data from DataFrame to LangChain Document objects for embedding."""
        documents: List[Document] = []
        if product_catalog_df.empty:
            logger.warning("Product catalog DataFrame is empty. No documents will be created.")
            return documents

        # Standardize column names (example: 'product ID' -> 'product_id')
        # This should align with the actual CSV column names.
        # For now, we'll assume they match the keys used below or are lowercased with spaces removed.
        product_catalog_df.columns = product_catalog_df.columns.str.lower().str.replace(' ', '_')

        required_cols = ['product_id', 'name', 'description', 'category']
        for col in required_cols:
            if col not in product_catalog_df.columns:
                logger.error(f"Missing required column '{col}' in product catalog DataFrame. Cannot create documents.")
                # Depending on strictness, either return empty or raise error
                return [] 

        for index, row in product_catalog_df.iterrows():
            try:
                content_parts = [
                    f"Product Name: {row.get('name', 'N/A')}",
                    f"Category: {row.get('category', 'N/A')}",
                    f"Description: {row.get('description', 'N/A')}"
                ]
                # Add optional fields if they exist and are not null
                if 'season' in row and pd.notna(row['season']):
                    content_parts.append(f"Season: {row['season']}")
                if 'color' in row and pd.notna(row['color']):
                    content_parts.append(f"Color: {row['color']}")
                if 'size' in row and pd.notna(row['size']):
                    content_parts.append(f"Size: {row['size']}")
                
                content = "\\n".join(content_parts)
                
                metadata = {
                    "product_id": str(row['product_id']),
                    "category": str(row['category']),
                    "name": str(row.get('name', 'N/A')),
                    # Add other relevant metadata for filtering or display
                }
                if 'price_eur' in row and pd.notna(row['price_eur']):
                    metadata["price_eur"] = float(row['price_eur'])
                if 'stock_amount' in row and pd.notna(row['stock_amount']):
                     metadata["stock_amount"] = int(row['stock_amount'])

                documents.append(Document(page_content=content, metadata=metadata))
            except Exception as e:
                logger.error(f"Error processing row {index} into a Document: {e}. Row data: {row.to_dict()}")
        
        logger.info(f"Created {len(documents)} documents from product catalog.")
        return documents

    def add_products(self, product_catalog_df: pd.DataFrame, batch_size: int = 100) -> None:
        """
        Adds new products from a DataFrame to the existing vector store.
        Handles batching for large catalogs.
        """
        if not hasattr(self, 'vector_store') or self.vector_store is None:
            logger.error("Vector store not initialized. Cannot add documents.")
            # Optionally, attempt to load or initialize here
            # self._load_existing_store() # or initialize a new one if that's desired behavior
            # if not hasattr(self, 'vector_store') or self.vector_store is None:
            #     return # Still failed
            return

        logger.info(f"Starting to add products to existing vector store. Batch size: {batch_size}")
        documents = self._create_documents_from_products(product_catalog_df)
        if not documents:
            logger.warning("No documents created from the provided product data. Nothing to add.")
            return

        # Add documents in batches using the vector store's method
        # Some vector stores handle batching internally, others might require manual batching.
        # Chroma's add_documents can take a list of Documents.
        try:
            # For very large additions, explicit batching loop might be safer for memory/API limits
            # For now, rely on Chroma's internal handling or simple batching
            total_docs = len(documents)
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                self.vector_store.add_documents(batch)
                logger.info(f"Added batch of {len(batch)} documents to vector store. ({i+len(batch)}/{total_docs})")
            
            self.vector_store.persist() # Ensure data is saved to disk
            logger.info(f"Product addition and embedding process complete. Store persisted. New count: {self.vector_store._collection.count()}")
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")


    def similarity_search(self, query: str, top_k: int = 5, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Performs similarity search in the vector store.

        Args:
            query: The natural language query string.
            top_k: Number of top similar documents to retrieve.
            category_filter: Optional product category to filter the search by.
                             (Case-insensitive match for category value).

        Returns:
            A list of dictionaries, where each dictionary contains the retrieved product\'s metadata
            (including product_id, name, category) and similarity score.
        """
        if not hasattr(self, 'vector_store') or self.vector_store is None:
            logger.warning("Vector store not initialized or empty. Cannot perform search.")
            return []
        
        if self.vector_store._collection.count() == 0:
            logger.warning("Vector store collection is empty. Search will yield no results.")
            return []

        logger.debug(f"Performing similarity search for query: '{query}', k={top_k}, category_filter: {category_filter}")
        
        # Chroma uses a 'where' clause for metadata filtering (SQL-like).
        # Example: filter={"category": "Electronics"}
        # For case-insensitive, if Chroma doesn't support it directly, it might need pre-processing
        # of metadata or more complex query capabilities if available.
        # Let's assume category is stored consistently, or we retrieve more and filter post-retrieval if needed.
        # For simple direct filtering, if the stored category metadata is already cased consistently:
        filter_dict = {}
        if category_filter:
            # Chroma's filtering is exact match. If category casing varies in data,
            # this might miss items. Solution: normalize category data upon ingestion.
            filter_dict["category"] = category_filter 
            # For more complex filtering (e.g. case-insensitive, multiple values)
            # refer to ChromaDB documentation for supported operators ($in, $regex if supported)
            # Example for multiple categories if supported: filter_dict["category"] = {"$in": ["Dresses", "Skirts"]}

        try:
            # similarity_search_with_score returns List[Tuple[Document, float]]
            results_with_scores = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=filter_dict if filter_dict else None
            )
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return []

        formatted_results = []
        for doc, score in results_with_scores:
            # Ensure all expected metadata keys are present or have defaults
            formatted_results.append({
                "product_id": doc.metadata.get("product_id"),
                "name": doc.metadata.get("name"),
                "category": doc.metadata.get("category"),
                "price_eur": doc.metadata.get("price_eur"), # Example, might not be in all docs
                "stock_amount": doc.metadata.get("stock_amount"), # Example
                "score": score,
                "description_snippet": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content,
                "full_content": doc.page_content # For full context if needed by agent
            })
        
        logger.debug(f"Similarity search returned {len(formatted_results)} results.")
        return formatted_results

    def get_retriever(self, top_k: int = 5, category_filter: Optional[str] = None) -> Any: # Should be BaseRetriever
        """
        Returns a LangChain retriever instance from the vector store.
        """
        if not hasattr(self, 'vector_store') or self.vector_store is None:
            logger.error("Vector store not initialized. Cannot create retriever.")
            # Return a dummy retriever or raise an error
            raise ValueError("Vector store must be initialized before a retriever can be obtained.")

        search_kwargs = {'k': top_k}
        if category_filter:
            # This assumes the category filter is applied during the search
            search_kwargs['filter'] = {'category': category_filter}
        
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)


# Global instance (or manage through application context/dependency injection)
# For simplicity in a script-like setup, a global might be used, but for larger apps, pass instances.
_vector_store_manager_instance: Optional[VectorStoreManager] = None

def initialize_vector_store(config: HermesConfig, product_catalog_df: pd.DataFrame, force_rebuild: bool = False) -> VectorStoreManager:
    """
    Initializes the global vector store manager instance.
    If force_rebuild is True, it will rebuild the store from the DataFrame.
    Otherwise, it will try to load an existing store, or build if not found/empty and df provided.
    """
    global _vector_store_manager_instance
    
    # Determine if we should attempt to build fresh vs load.
    # `initialize_new_store` in VectorStoreManager constructor handles actual build logic.
    # `force_rebuild` here means we definitely want to try building.
    # If not forcing rebuild, we rely on VectorStoreManager to try loading first.
    
    # Simplified logic: if force_rebuild, then initialize_new_store = True.
    # Else, VectorStoreManager will try to load, and if that fails or is empty,
    # it might still create a new empty one if no df is provided.
    # If df is provided and not force_rebuild, it should ideally load.

    # Let's refine the logic for initialize_new_store passed to constructor:
    # It should be true if we are forcing a rebuild OR if the store doesn't exist (which load_existing_store would handle by creating empty)
    # For simplicity, let's tie `initialize_new_store` directly to `force_rebuild` for this factory.
    # The VectorStoreManager constructor itself has logic to load if initialize_new_store=False.
    
    if _vector_store_manager_instance is None or force_rebuild:
        logger.info(f"Creating new VectorStoreManager instance. Force rebuild: {force_rebuild}")
        _vector_store_manager_instance = VectorStoreManager(
            config=config,
            product_catalog_df=product_catalog_df if force_rebuild or _vector_store_manager_instance is None else None, # Only pass df if rebuilding
            initialize_new_store=force_rebuild # If true, it will use the df to build. If false, it will try to load.
        )
        # If not force_rebuild, and an instance was loaded, but it's empty, and we have a df, we might want to populate.
        # This logic is getting complex for a simple factory. VectorStoreManager should be robust.
        # Let's adjust: If force_rebuild, it builds. If not, it tries to load. If loading results in an empty store
        # AND product_catalog_df is available, then populate it.

        if not force_rebuild and _vector_store_manager_instance and \
           _vector_store_manager_instance.vector_store._collection.count() == 0 and \
           product_catalog_df is not None and not product_catalog_df.empty:
            logger.info("Loaded vector store is empty and product catalog is available. Populating the store.")
            # This implies we need a way to add to an existing (but empty) loaded store.
            # The current _build_and_persist_store overwrites. Let's use add_products.
            # Or, more simply, if it's empty after load, and we have data, treat as initial build.
            _vector_store_manager_instance._build_and_persist_store(product_catalog_df)


    elif product_catalog_df is not None and not product_catalog_df.empty and \
         _vector_store_manager_instance.vector_store._collection.count() == 0:
        # Instance exists, not forced rebuild, but store is empty and we have data.
        logger.info("Vector store instance exists but is empty, and product catalog is available. Populating.")
        _vector_store_manager_instance._build_and_persist_store(product_catalog_df) # or .add_products()

    return _vector_store_manager_instance

def get_vector_store_retriever(config: Optional[HermesConfig] = None, 
                               product_catalog_df: Optional[pd.DataFrame] = None, 
                               force_rebuild: bool = False,
                               top_k: int = 5, 
                               category_filter: Optional[str] = None) -> Any: # BaseRetriever
    """
    Factory function to get an initialized vector store retriever.
    Manages a global instance of VectorStoreManager.
    """
    global _vector_store_manager_instance
    
    if _vector_store_manager_instance is None or force_rebuild:
        if config is None:
            raise ValueError("HermesConfig must be provided to initialize vector store for the first time or for rebuild.")
        if product_catalog_df is None and force_rebuild : # if not force_rebuild, df is not strictly needed for loading
             logger.warning("Product catalog DataFrame not provided during forced rebuild. Store might be empty if not already persisted.")
        
        # Pass product_catalog_df only if rebuilding or if it's the very first init and df is available
        df_for_init = None
        if force_rebuild and product_catalog_df is not None:
            df_for_init = product_catalog_df
        elif _vector_store_manager_instance is None and product_catalog_df is not None: # First time init
             df_for_init = product_catalog_df


        _vector_store_manager_instance = VectorStoreManager(
            config=config,
            product_catalog_df=df_for_init,
            initialize_new_store=force_rebuild # True if we want to build fresh, False to attempt load
        )
         # If after attempting to load (initialize_new_store=False), the store is empty and we have a df, populate it.
        if not force_rebuild and product_catalog_df is not None and not product_catalog_df.empty and \
           _vector_store_manager_instance.vector_store._collection.count() == 0:
            logger.info("Loaded vector store is empty and product catalog DataFrame is available. Populating the store.")
            _vector_store_manager_instance._build_and_persist_store(product_catalog_df)


    if _vector_store_manager_instance is None:
         raise RuntimeError("Failed to initialize VectorStoreManager instance.")

    return _vector_store_manager_instance.get_retriever(top_k=top_k, category_filter=category_filter)

""" {cell}
### Usage Notes:

- **Initialization**: 
    - Call `initialize_vector_store(config, product_catalog_df, force_rebuild=True)` once at application startup if you want to ensure the vector store is built/rebuilt from the latest `product_catalog_df`.
    - Call `initialize_vector_store(config, product_catalog_df)` (with `force_rebuild=False` or omitted) to attempt to load an existing store. If it's empty and `product_catalog_df` is provided, it will then populate it.
    - `HermesConfig` needs to be properly loaded with API keys, paths, etc.
    - `product_catalog_df` is a pandas DataFrame, presumably loaded from the CSV/Google Sheet.
- **Getting a Retriever**: 
    - Once initialized, use `get_vector_store_retriever(config, top_k=..., category_filter=...)` to obtain a LangChain `BaseRetriever` object. 
    - The `config` is needed by `get_vector_store_retriever` in case the store needs to be initialized on first call. `product_catalog_df` and `force_rebuild` can also be passed if initialization might be needed.
- **Dependencies**:
    - Requires `pandas`, `langchain-openai`, `langchain-community` (for Chroma), `langchain`. Ensure these are in `pyproject.toml`.
    - Assumes `HermesConfig` is correctly defined in `src.config.py`.
    - Column names in the input DataFrame for product catalog are expected to be consistent (e.g., 'product_id', 'name', 'description', 'category'). The `_create_documents_from_products` method attempts to standardize them.
- **Persistence**: ChromaDB persists data to the directory specified in `config.vector_store_path`. The store will be loaded from this path on subsequent runs if `force_rebuild` is not `True`.
- **Error Handling and Logging**: Basic logging is included. Robust applications would expand on this.
- **Metadata Filtering**: The `similarity_search` and `get_retriever` methods support a `category_filter`. Chroma's filtering capabilities can be explored for more advanced scenarios (e.g., numeric range filters on price if that metadata is added).
- **Singleton Pattern**: The `initialize_vector_store` and `get_vector_store_retriever` functions manage a global-like instance (`_vector_store_manager_instance`). In larger, more complex applications, consider using dependency injection frameworks or passing the `VectorStoreManager` instance explicitly.
""" 