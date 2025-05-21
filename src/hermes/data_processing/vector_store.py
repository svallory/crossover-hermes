"""
Module for vector store operations in Hermes using a singleton pattern.
This handles creating, updating, and querying the vector database (ChromaDB).
"""

import os
from typing import Optional, List, Dict, Any, Tuple, cast

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Import Hermes models
from src.hermes.model.product import Product
from src.hermes.model.enums import ProductCategory, Season
from src.hermes.config import HermesConfig
from src.hermes.data_processing.load_data import load_products_df
from src.hermes.types import SingletonMeta

# Sentinel for in-memory storage
IN_MEMORY_SENTINEL = "___IN_MEMORY___"

# Default collection name
COLLECTION_NAME = "products_catalog"

# Batch size for processing large catalogs
BATCH_SIZE = 500

# Embedding model dimensions (text-embedding-3-small is 1536, 
# text-embedding-ada-002 is 1536, update as needed)
EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
    "text-embedding-3-large": 3072,
}

class VectorStore(metaclass=SingletonMeta['VectorStore']):
    """Singleton class for managing vector store operations."""

    _collection = None

    def __init__(self, hermes_config: HermesConfig = HermesConfig()):
        """
        Initialize the VectorStore with a configuration.
        
        Args:
            hermes_config: Hermes configuration with API keys and paths
        """
        if self._collection is None:
            self._get_vector_store(hermes_config)

    def _get_vector_store(
        self,
        hermes_config: HermesConfig,
    ) -> Collection:
        """
        Get the vector store from cache or initialize it.
        This method first checks if a vector store is already loaded in memory.
        If not, it attempts to load an existing one from disk or creates a new one.

        Args:
            hermes_config: Hermes configuration with API keys and paths

        Returns:
            A ChromaDB collection containing product data

        Raises:
            Exception: If there's an error creating or loading the vector store
        """
        # If vector store is already initialized, return it
        if self._collection is not None:
            print(f"Using existing vector store with {self._collection.count()} items.")
            return self._collection

        try:
            print("Initializing vector store...")
            storage_path = hermes_config.vector_store_path
                  
            # Initialize ChromaDB client
            if storage_path == IN_MEMORY_SENTINEL:
                chroma_client = chromadb.EphemeralClient()
                print("Using in-memory ChromaDB")
            else:
                # Ensure directory exists
                os.makedirs(storage_path, exist_ok=True)
                chroma_client = chromadb.PersistentClient(path=storage_path)
                print(f"Using persistent ChromaDB at {storage_path}")
            
            # For in-memory mode, always create a new store
            if storage_path == IN_MEMORY_SENTINEL:
                self._collection = self._create_vector_store(
                    chroma_client=chroma_client,
                    hermes_config=hermes_config,
                )
                return self._collection

            # For persistent storage, check if database file exists
            db_file = os.path.join(storage_path, "chroma.sqlite3")
            
            if os.path.exists(db_file):
                print(f"Found existing ChromaDB at {db_file}")
                try:
                    self._collection = chroma_client.get_collection(
                        name=COLLECTION_NAME,
                        embedding_function=OpenAIEmbeddingFunction(
                            api_key=hermes_config.openai_api_key,
                            api_base=hermes_config.openai_base_url,
                            model_name=hermes_config.embedding_model_name,
                            dimensions=EMBEDDING_DIMENSIONS.get(hermes_config.embedding_model_name, 1536),
                        ) # type: ignore
                    )
                    print(f"Successfully loaded existing vector store with {self._collection.count()} items.")
                except Exception as e:
                    print(f"Error loading existing vector store: {e}")
                    print(f"Creating new vector store instead...")
                    self._collection = self._create_vector_store(
                        chroma_client=chroma_client,
                        hermes_config=hermes_config,
                    )
            else:
                print(f"No existing ChromaDB found at {storage_path}")
                print("Creating new vector store...")
                self._collection = self._create_vector_store(
                    chroma_client=chroma_client,
                    hermes_config=hermes_config,
                )

            print(f"Vector store initialized with {self._collection.count()} items.")
            return self._collection

        except Exception as e:
            raise Exception(f"Error initializing vector store: {str(e)}")

    def _create_vector_store(
        self,
        chroma_client: Any,
        hermes_config: HermesConfig,
        collection_name: str = COLLECTION_NAME,
    ) -> Collection:
        """
        Create a new vector store using ChromaDB from a dataframe of products.
        Optimized for large catalogs by using batch processing.

        Args:
            chroma_client: ChromaDB client (persistent or ephemeral)
            hermes_config: Hermes configuration with input spreadsheet IDs
            collection_name: Name of the collection to create

        Returns:
            The created ChromaDB collection
        """
        # Load product data
        products_df = load_products_df(hermes_config.input_spreadsheet_id)
        
        # Get or create the collection
        collection = chroma_client.get_or_create_collection(
            name=collection_name, 
            embedding_function=OpenAIEmbeddingFunction(
                api_key=hermes_config.openai_api_key,
                api_base=hermes_config.openai_base_url,
                model_name=hermes_config.embedding_model_name,
                dimensions=EMBEDDING_DIMENSIONS.get(hermes_config.embedding_model_name, 1536),
            ) # type: ignore
        )
        
        # Process data in batches to handle large datasets
        total_rows = len(products_df)
        batch_count = (total_rows // BATCH_SIZE) + (1 if total_rows % BATCH_SIZE > 0 else 0)
        
        print(f"Processing {total_rows} products in {batch_count} batches")
        
        for batch_idx in range(batch_count):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min((batch_idx + 1) * BATCH_SIZE, total_rows)
            
            print(f"Processing batch {batch_idx+1}/{batch_count} (records {start_idx}-{end_idx})")
            
            batch_df = products_df.iloc[start_idx:end_idx]
            
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for _, row in batch_df.iterrows():
                ids.append(str(row["product_id"]))
                documents.append(row.to_json())
                metadatas.append(row.to_dict())

            # Add batch to the collection
            collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
            
        return collection

    def search_products_by_description(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Product]:
        """
        Search products by description using the vector store.

        Args:
            query: Search query
            top_k: Maximum number of results to return
            category_filter: Optional category filter
            filters: Optional additional filters

        Returns:
            List of Product objects matching the search
        """
        # Make sure we have a vector store
        if self._collection is None:
            raise ValueError(
                "Vector store has not been initialized yet."
            )

        # Prepare filter criteria
        filter_criteria = {}
        if filters:
            filter_criteria.update(filters)
        if category_filter:
            filter_criteria["category"] = category_filter

        # Query the vector store
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter_criteria if filter_criteria else None,
        )

        # Convert results to Product objects
        products = []
        if results and "metadatas" in results and results["metadatas"]:
            for metadata_list in results["metadatas"]:
                for metadata in metadata_list:
                    product = self.convert_to_product_model(cast(Dict[str, Any], metadata))
                    products.append(product)

        return products

    def convert_to_product_model(self, metadata: Dict[str, Any]) -> Product:
        """
        Convert a metadata dictionary from ChromaDB to a Product model.
        Assumes all required fields are present in the metadata.
        """
        # Convert seasons from string to list of Season enums
        seasons_list = []
        seasons_str = metadata["seasons"]
        for season_str in seasons_str.split(","):
            season_str = season_str.strip()
            if season_str == "All seasons":
                # Include all seasons
                seasons_list = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
                break
            if season_str:
                seasons_list.append(Season(season_str))
        
        # Create additional metadata dict if any extra fields exist
        additional_metadata = {}
        for key, value in metadata.items():
            if key not in ["product_id", "name", "description", "category", "product_type", "stock", "seasons", "price"]:
                additional_metadata[key] = value
        
        # Create and return the Product
        return Product(
            product_id=metadata["product_id"],
            name=metadata["name"],
            description=metadata["description"],
            category=ProductCategory(metadata["category"]),
            product_type=metadata["product_type"],
            stock=int(metadata["stock"]),
            seasons=seasons_list,
            price=float(metadata["price"]),
            metadata=additional_metadata if additional_metadata else None,
        )

    def similarity_search_with_score(
        self,
        query_text: str,
        n_results: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform a similarity search with scores.

        Args:
            query_text: The query text
            n_results: Maximum number of results
            filter_criteria: Optional filter criteria

        Returns:
            List of (metadata, score) tuples sorted by relevance
        """
        # Make sure we have a vector store
        if self._collection is None:
            raise ValueError(
                "Vector store has not been initialized yet."
            )

        # Query the vector store
        results = self._collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_criteria,
        )

        # Process results
        items_with_scores = []
        if (results and "metadatas" in results and results["metadatas"] is not None and 
                "distances" in results and results["distances"] is not None):
            for i, (metadata_list, distance_list) in enumerate(
                zip(results["metadatas"], results["distances"])
            ):
                for j, (metadata, distance) in enumerate(
                    zip(metadata_list, distance_list)
                ):
                    # Convert distance to similarity score (1.0 = identical, 0.0 = completely different)
                    score = 1.0 - distance  # Assuming cosine distance
                    items_with_scores.append((cast(Dict[str, Any], metadata), score))

        # Sort by similarity score (highest first)
        items_with_scores.sort(key=lambda x: x[1], reverse=True)

        return items_with_scores
