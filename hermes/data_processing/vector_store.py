"""Module for vector store operations in Hermes using a singleton pattern.
This handles creating, updating, and querying the vector database (ChromaDB).
"""

import os
from typing import Any, List, Sequence, cast

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from hermes.config import HermesConfig
from hermes.data_processing.load_data import load_products_df
from hermes.model.enums import ProductCategory, Season

# Import Hermes models
from hermes.model.product import Product
from hermes.model.vector import (
    ProductSearchQuery,
    ProductSearchResult,
    SimilarProductQuery,
)
from hermes.custom_types import SingletonMeta

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


class VectorStore(metaclass=SingletonMeta["VectorStore"]):
    """Singleton class for managing vector store operations."""

    _collection = None

    def __init__(self, hermes_config: HermesConfig = HermesConfig()):
        """Initialize the VectorStore with a configuration.

        Args:
            hermes_config: Hermes configuration with API keys and paths

        """
        if self._collection is None:
            self._get_vector_store(hermes_config)

    def _get_vector_store(
        self,
        hermes_config: HermesConfig,
    ) -> Collection:
        """Get the vector store from cache or initialize it.
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
                        ),  # type: ignore
                    )
                    print(f"Successfully loaded existing vector store with {self._collection.count()} items.")
                except Exception as e:
                    print(f"Error loading existing vector store: {e}")
                    print("Creating new vector store instead...")
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
        """Create a new vector store using ChromaDB from a dataframe of products.
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
            ),  # type: ignore
        )

        # Process data in batches to handle large datasets
        total_rows = len(products_df)
        batch_count = (total_rows // BATCH_SIZE) + (1 if total_rows % BATCH_SIZE > 0 else 0)

        print(f"Processing {total_rows} products in {batch_count} batches")

        for batch_idx in range(batch_count):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min((batch_idx + 1) * BATCH_SIZE, total_rows)

            print(f"Processing batch {batch_idx + 1}/{batch_count} (records {start_idx}-{end_idx})")

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
        query: ProductSearchQuery,
    ) -> list[Product]:
        """Search products by description using the vector store.

        Args:
            query: ProductSearchQuery with search parameters

        Returns:
            List of Product objects matching the search

        """
        # Make sure we have a vector store
        if self._collection is None:
            raise ValueError("Vector store has not been initialized yet.")

        # Prepare filter criteria
        filter_criteria = {}
        if query.filter_criteria:
            filter_criteria.update(query.filter_criteria)

        # Query the vector store
        results = self._collection.query(
            query_texts=[query.query_text],
            n_results=query.n_results,
            where=filter_criteria if filter_criteria else None,
        )

        # Convert results to Product objects
        products = []
        if results and "metadatas" in results and results["metadatas"]:
            for metadata_list in results["metadatas"]:
                for metadata in metadata_list:
                    product = self.convert_to_product_model(cast(dict[str, Any], metadata))
                    products.append(product)

        return products

    def convert_to_product_model(self, metadata: dict[str, Any]) -> Product:
        """Convert a metadata dictionary from ChromaDB to a Product model.
        Assumes all required fields are present in the metadata.
        """
        # Convert seasons from string to list of Season enums
        seasons_list = []
        seasons_str = metadata.get("seasons", "")
        if isinstance(seasons_str, str):
            for season_str in seasons_str.split(","):
                season_str = season_str.strip()
                if season_str == "All seasons":
                    # Include all seasons
                    seasons_list = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
                    break
                if season_str:
                    seasons_list.append(Season(season_str))

        # Create additional metadata dict if any extra fields exist
        additional_metadata = {
            key: value
            for key, value in metadata.items()
            if key not in [
                "product_id",
                "name",
                "description",
                "category",
                "product_type",
                "stock",
                "seasons",
                "price",
            ]
        }

        # Ensure all fields have the correct types
        product_id = str(metadata["product_id"])
        name = str(metadata["name"])
        description = str(metadata["description"])
        
        # Handle category conversion safely - map from test data to enum values
        category_str = str(metadata["category"])
        try:
            # Try direct conversion first
            category = ProductCategory(category_str)
        except ValueError:
            # Handle the test data format
            if category_str == "Men's Clothing":
                category = ProductCategory.MENS_CLOTHING
            elif category_str == "Women's Clothing":
                category = ProductCategory.WOMENS_CLOTHING
            elif category_str == "Men's Shoes":
                category = ProductCategory.MENS_SHOES
            elif category_str == "Women's Shoes":
                category = ProductCategory.WOMENS_SHOES
            elif category_str == "Kid's Clothing":
                category = ProductCategory.KIDS_CLOTHING
            else:
                # Default to first category if unknown
                category = ProductCategory.ACCESSORIES
        
        product_type = str(metadata.get("product_type", ""))
        stock = int(float(metadata["stock"]))
        price = float(metadata["price"])

        # Create and return the Product
        return Product(
            product_id=product_id,
            name=name,
            description=description,
            category=category,
            product_type=product_type,
            stock=stock,
            seasons=seasons_list,
            price=price,
            metadata=additional_metadata if additional_metadata else None,
        )

    def find_similar_products(
        self,
        query: SimilarProductQuery,
    ) -> list[Product]:
        """Find products similar to a reference product.

        Args:
            query: SimilarProductQuery with search parameters

        Returns:
            List of similar Product objects

        """
        # Make sure we have a vector store
        if self._collection is None:
            raise ValueError("Vector store has not been initialized yet.")

        # Get the reference product
        product_id = query.product_id
        if not product_id:
            raise ValueError("Product ID is required for finding similar products")

        # Get the document embedding for the reference product
        product_results = self._collection.get(
            ids=[product_id],
            include=["embeddings", "metadatas"],
        )

        if not product_results or not product_results["embeddings"]:
            raise ValueError(f"Product with ID {product_id} not found in vector store")

        # Get the embedding of the reference product
        reference_embedding = product_results["embeddings"][0]
        
        # Cast the embedding to the expected type (Sequence[float])
        embedding_list = cast(Sequence[float], reference_embedding)

        # Prepare filter criteria
        filter_criteria = {}
        if query.filter_criteria:
            filter_criteria.update(query.filter_criteria)

        # Query the vector store using the reference embedding
        results = self._collection.query(
            query_embeddings=[embedding_list],
            n_results=query.n_results + (1 if query.exclude_reference else 0),
            where=filter_criteria if filter_criteria else None,
        )

        # Convert results to Product objects
        products = []
        if results and "metadatas" in results and results["metadatas"]:
            for metadata_list in results["metadatas"]:
                for metadata in metadata_list:
                    # Skip the reference product if requested
                    if query.exclude_reference and metadata["product_id"] == product_id:
                        continue
                    product = self.convert_to_product_model(cast(dict[str, Any], metadata))
                    products.append(product)

        # Limit to requested number
        return products[:query.n_results]

    def similarity_search_with_score(
        self,
        query: ProductSearchQuery,
    ) -> list[ProductSearchResult]:
        """Perform a similarity search with scores.

        Args:
            query: ProductSearchQuery with search parameters

        Returns:
            List of ProductSearchResult objects sorted by relevance

        """
        # Make sure we have a vector store
        if self._collection is None:
            raise ValueError("Vector store has not been initialized yet.")

        # Query the vector store
        results = self._collection.query(
            query_texts=[query.query_text],
            n_results=query.n_results,
            where=query.filter_criteria,
        )

        # Process results
        search_results = []
        if (
            results
            and "metadatas" in results
            and results["metadatas"] is not None
            and "distances" in results
            and results["distances"] is not None
        ):
            for i, (metadata_list, distance_list) in enumerate(zip(results["metadatas"], results["distances"])):
                for j, (metadata, distance) in enumerate(zip(metadata_list, distance_list)):
                    # Convert distance to similarity score (1.0 = identical, 0.0 = completely different)
                    score = 1.0 - distance  # Assuming cosine distance
                    
                    # Create ProductSearchResult with proper type handling
                    search_result = ProductSearchResult(
                        product_id=str(metadata["product_id"]),
                        product_name=str(metadata["name"]),
                        product_metadata=cast(dict[str, Any], metadata),
                        similarity_score=score,
                    )
                    search_results.append(search_result)

        # Sort by similarity score (highest first)
        search_results.sort(key=lambda x: x.similarity_score, reverse=True)

        return search_results
