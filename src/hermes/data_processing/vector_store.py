"""
Module for vector store operations in Hermes.
This handles creating, updating, and querying the vector database (ChromaDB).
"""

import os
import logging
import pandas as pd
import asyncio
from typing import Optional, List, Dict, Any, Union, Tuple
import uuid

import chromadb
from chromadb.utils import embedding_functions

# Import Hermes models
from src.hermes.model import Product, ProductCategory, Season

# Sentinel for in-memory storage
IN_MEMORY_SENTINEL = "___IN_MEMORY___"

# Define a type variable instead
SentenceTransformerEmbeddingFunction: Any = None
try:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:
    pass

# For OpenAI embeddings
try:
    from langchain_openai import OpenAIEmbeddings as LangchainEmbeddings
except ImportError:
    try:
        from langchain.embeddings import OpenAIEmbeddings as LangchainEmbeddings
    except ImportError:
        LangchainEmbeddings = None

logger = logging.getLogger(__name__)

# Type for embedding function - use Any for flexibility
EmbeddingFunction = Any


def get_embedding_function(
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    use_openai: bool = False,
    openai_api_key: Optional[str] = None,
    **kwargs: Any,
) -> EmbeddingFunction:
    """
    Get an embedding function for the vector store.

    Args:
        embedding_model: Name of the embedding model to use
        use_openai: Whether to use OpenAI's embedding API
        openai_api_key: OpenAI API key if using OpenAI embeddings
        **kwargs: Additional arguments to pass to the embedding function

    Returns:
        An embedding function compatible with ChromaDB
    """
    if use_openai:
        # Create OpenAI embedding function
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key or os.environ.get("OPENAI_API_KEY"), 
            model_name=embedding_model
        )
        return openai_ef
    else:
        # Use sentence-transformers for local embeddings
        return SentenceTransformerEmbeddingFunction(model_name=embedding_model)


async def create_vector_store(
    products_df: pd.DataFrame,
    collection_name: str = "products",
    embedding_function: Optional[Any] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: str = "text-embedding-3-small",
    storage: str = "./chroma_db",
) -> chromadb.Collection:
    """
    Create a vector store using ChromaDB from a dataframe of products.

    If storage is IN_MEMORY_STORAGE_SENTINEL, runs in memory.
    Otherwise, uses a persistent client, storing data at the specified storage path.

    Args:
        products_df: DataFrame containing product data
        collection_name: Name of the collection in ChromaDB
        embedding_function: Custom embedding function (if None, will create an OpenAI embedding function)
        api_key: Optional OpenAI API key
        base_url: Optional base URL for OpenAI API
        model_name: The OpenAI embedding model to use
        storage: Path for persistent storage, or IN_MEMORY_STORAGE_SENTINEL for in-memory.
                 Defaults to "./chroma_db".

    Returns:
        The created ChromaDB collection
    """
    # Run the synchronous parts in a separate thread
    def create_store():
        # Initialize ChromaDB client
        if storage == IN_MEMORY_SENTINEL:
            chroma_client = chromadb.Client()
        else:
            chroma_client = chromadb.PersistentClient(path=storage)
            
        # Create embedding function if not provided
        nonlocal embedding_function
        if embedding_function is None:
            embedding_function = get_embedding_function(model_name=model_name, use_openai=True, openai_api_key=api_key)

        # Get or create the collection
        collection = chroma_client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []

        for _, row in products_df.iterrows():
            # Extract product text representation for embedding
            product_text = _create_product_text(row)
            documents.append(product_text)

            # Extract metadata
            metadata = _extract_product_metadata(row)
            metadatas.append(metadata)

            # Use product_id as document id if available, otherwise generate one
            product_id = str(row.get("product_id", str(uuid.uuid4())))
            ids.append(product_id)

        # Add products to the collection
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

        return collection

    # Run the synchronous function in a separate thread
    return await asyncio.to_thread(create_store)


def _create_product_text(product: Union[Dict[str, Any], pd.Series]) -> str:
    """
    Create a text representation of a product for embedding.

    Args:
        product: Product data as dictionary or pandas Series

    Returns:
        Text representation of the product
    """
    # Map column names for flexibility
    name_fields = ["product_name", "name"]
    description_fields = ["product_description", "description"]
    category_fields = ["product_category", "category"]
    type_fields = ["product_type", "type"]

    # Extract available product information
    product_name = next((product.get(field, "") for field in name_fields if field in product), "")
    product_description = next((product.get(field, "") for field in description_fields if field in product), "")
    product_category = next((product.get(field, "") for field in category_fields if field in product), "")
    product_type = next((product.get(field, "") for field in type_fields if field in product), "")

    # Create a comprehensive text representation
    text_parts = []
    if product_name:
        text_parts.append(f"Product: {product_name}")
    if product_description:
        text_parts.append(f"Description: {product_description}")
    if product_category:
        text_parts.append(f"Category: {product_category}")
    if product_type:
        text_parts.append(f"Type: {product_type}")

    # Additional product details if available
    for key, value in product.items():
        if value is not None and isinstance(key, str) and not key.startswith("_"):
            # Skip fields we already processed
            if key in name_fields or key in description_fields or key in category_fields or key in type_fields:
                continue
            text_parts.append(f"{key}: {value}")

    return " ".join(text_parts)


def _extract_product_metadata(
    product: Union[Dict[str, Any], pd.Series],
) -> Dict[str, Union[str, int, float, bool, None]]:
    """
    Extract metadata from a product for storing in ChromaDB.

    Args:
        product: Product data as dictionary or pandas Series

    Returns:
        A dictionary of metadata
    """
    # Define mappings from possible field names to standard field names
    field_mappings = {
        "product_id": ["product_id", "id"],
        "product_name": ["product_name", "name"],
        "product_type": ["product_type", "type"],
        "product_category": ["product_category", "category"],
        "price": ["price", "unit_price"],
        "stock": ["stock", "inventory", "quantity"],
        "seasons": ["seasons", "season"],
    }

    # Helper function to get the first matching field value
    def get_value(fields: List[str]) -> Any:
        for field in fields:
            if field in product:
                return product[field]
        return None

    # Build metadata dictionary with standardized field names
    metadata = {}
    for standard_name, possible_fields in field_mappings.items():
        value = get_value(possible_fields)
        if value is not None:
            # Convert to appropriate type based on field
            if standard_name == "price":
                try:
                    metadata[standard_name] = float(value)
                except (ValueError, TypeError):
                    metadata[standard_name] = 0.0
            elif standard_name == "stock":
                try:
                    metadata[standard_name] = int(value)
                except (ValueError, TypeError):
                    metadata[standard_name] = 0
            else:
                # For text fields, ensure it's a string
                metadata[standard_name] = str(value)

    # Add all remaining fields as metadata
    for key, value in product.items():
        # Skip fields we've already processed
        if any(key in fields for fields in field_mappings.values()):
            continue
        # Skip private fields
        if isinstance(key, str) and not key.startswith("_"):
            if isinstance(value, (str, int, float, bool)) or value is None:
                metadata[key] = value
            else:
                metadata[key] = str(value)

    return metadata


async def query_vector_store(
    collection: chromadb.Collection,
    query_text: str,
    n_results: int = 5,
    filter_criteria: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Any]]:
    """
    Query the vector store for similar documents.

    Args:
        collection: ChromaDB collection to query
        query_text: Text to search for
        n_results: Number of results to return
        filter_criteria: Dictionary of metadata filters to apply

    Returns:
        Query results as a dictionary with lists
    """
    # Run the query in a separate thread
    def run_query():
        query_result = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_criteria,
            include=["metadatas", "documents", "distances"],
        )
        
        # Convert QueryResult to Dict
        result_dict: Dict[str, List[Any]] = {}
        for key, value in query_result.items():
            if isinstance(value, list):
                result_dict[key] = value
            else:
                result_dict[key] = [value]
                
        return result_dict
    
    # Use asyncio to prevent blocking
    return await asyncio.to_thread(run_query)


async def load_vector_store(
    collection_name: str = "products",
    embedding_function: Optional[Any] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: str = "text-embedding-3-small",
    storage_path: str = "./chroma_db",
) -> chromadb.Collection:
    """
    Load an existing ChromaDB vector store from a persistent path.

    Args:
        collection_name: Name of the collection in ChromaDB
        embedding_function: Custom embedding function (if None, will create an OpenAI embedding function)
        api_key: Optional OpenAI API key
        base_url: Optional base URL for OpenAI API
        model_name: The OpenAI embedding model to use
        storage_path: Path to the persistent storage. Defaults to "./chroma_db".

    Returns:
        The loaded ChromaDB collection
    """
    # Run the synchronous function in a separate thread
    def load_store():
        # Initialize the persistent ChromaDB client
        chroma_client = chromadb.PersistentClient(path=storage_path)
        
        # Create embedding function if not provided
        nonlocal embedding_function
        if embedding_function is None:
            embedding_function = get_embedding_function(model_name=model_name, use_openai=True, openai_api_key=api_key)

        # Get the collection
        collection = chroma_client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)
        return collection

    return await asyncio.to_thread(load_store)


async def search_products_by_description(
    collection: chromadb.Collection,
    query: str,
    top_k: int = 5,
    category_filter: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Product]:
    """
    Search for products based on a natural language description.
    This is the core function for RAG-based product inquiries, supporting the catalog_tools implementation.

    Args:
        collection: ChromaDB collection to query
        query: Natural language query describing the desired product
        top_k: Number of top matching products to return
        category_filter: Optional category to filter the search (deprecated, use filters)
        filters: Optional dictionary of metadata filters (including category and season)

    Returns:
        List of Product objects matching the query
    """
    # Ensure filters is a dictionary
    if filters is None:
        filters = {}

    # Add category filter if specified
    if category_filter and "product_category" not in filters:
        filters["product_category"] = category_filter

    # Run similarity search with filters
    results = await query_vector_store(collection, query, n_results=top_k, filter_criteria=filters)
    
    # Convert results to Product models
    products = []
    if "metadatas" in results and results["metadatas"] and results["metadatas"][0]:
        for i, metadata in enumerate(results["metadatas"][0]):
            # Add distance as search_score
            score = 1.0
            if "distances" in results and results["distances"] and i < len(results["distances"][0]):
                score = 1.0 - min(results["distances"][0][i], 1.0)
            
            metadata["search_score"] = score
            
            # Add document text to metadata if available
            if "documents" in results and results["documents"] and i < len(results["documents"][0]):
                metadata["document"] = results["documents"][0][i]
                
            product = convert_to_product_model(metadata)
            products.append(product)
    
    return products


def convert_to_product_model(metadata: Dict[str, Any]) -> Product:
    """
    Convert metadata from ChromaDB to a Product model.

    Args:
        metadata: Metadata from ChromaDB query result

    Returns:
        Product model instance
    """
    # Extract required fields with defaults
    product_id = metadata.get("product_id", "")
    product_name = metadata.get("product_name", "")
    product_description = metadata.get("document", "")
    if "description" in metadata:
        product_description = str(metadata.get("description", ""))

    # Handle product category (convert string to enum)
    product_category_str = metadata.get("product_category", "")
    try:
        product_category = ProductCategory(product_category_str)
    except ValueError:
        # Default to first category if invalid
        product_category = next(iter(ProductCategory))

    # Extract other fields with defaults
    product_type = metadata.get("product_type", "")
    stock = int(metadata.get("stock", 0))
    price = float(metadata.get("price", 0.0))

    # Handle seasons (convert comma-separated string to list)
    seasons = []
    if "seasons" in metadata:
        seasons_str = metadata.get("seasons", "")
        if seasons_str:
            season_names = seasons_str.split(",")
            for season_name in season_names:
                try:
                    seasons.append(Season(season_name.strip()))
                except ValueError:
                    pass

    # Create and return Product instance
    return Product(
        product_id=product_id,
        product_name=product_name,
        product_description=product_description,
        product_category=product_category,
        product_type=product_type,
        stock=stock,
        seasons=seasons,
        price=price,
    )


def create_openai_embedding_function(
    model_name: str = "text-embedding-3-small",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Any:
    """
    Create an OpenAI embedding function for ChromaDB.

    Args:
        model_name: The name of the OpenAI embedding model to use
        api_key: OpenAI API key
        base_url: Optional base URL for the OpenAI API

    Returns:
        An embedding function compatible with ChromaDB
    """
    # Get API key from environment if not provided
    openai_api_key = api_key or os.environ.get("OPENAI_API_KEY")
    
    # Create embedding function kwargs
    ef_kwargs = {"api_key": openai_api_key, "model_name": model_name}

    # Add base_url if provided
    if base_url:
        ef_kwargs["api_base"] = base_url

    # Create and return the OpenAI embedding function
    return embedding_functions.OpenAIEmbeddingFunction(**ef_kwargs)
