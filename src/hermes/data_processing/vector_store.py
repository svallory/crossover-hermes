"""
Module for vector store operations in Hermes.
This handles creating, updating, and querying the vector database (ChromaDB).
"""

import os
import logging
import pandas as pd
from typing import Optional, List, Dict, Any, Union, Tuple
import uuid

import chromadb
from chromadb.utils import embedding_functions

# Import Hermes models
from src.hermes.model import Product, ProductCategory, Season

# Import the embedding functions in a way that works with type checking
SentenceTransformerEmbeddingFunction: Any = None  # Define a type variable instead
try:
    # Modern chromadb versions
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction  # type: ignore
except ImportError:
    pass  # Keep the None value for SentenceTransformerEmbeddingFunction

# For OpenAI embeddings
try:
    from langchain_openai import OpenAIEmbeddings as LangchainEmbeddings
except ImportError:
    try:
        # Fallback to older langchain structure
        from langchain.embeddings import OpenAIEmbeddings as LangchainEmbeddings  # type: ignore
    except ImportError:
        LangchainEmbeddings = None  # type: ignore

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
        if LangchainEmbeddings is None:
            raise ImportError("OpenAI embeddings requested but langchain_openai is not installed")

        # Get API key from environment if not provided
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAI embeddings")

        # Create OpenAI embedding function
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(api_key=api_key, model_name=embedding_model)
        return openai_ef
    else:
        # Use sentence-transformers for local embeddings
        if SentenceTransformerEmbeddingFunction is None:
            raise ImportError("SentenceTransformerEmbeddingFunction not found in chromadb")

        return SentenceTransformerEmbeddingFunction(model_name=embedding_model)


def create_vector_store(
    products_df: pd.DataFrame,
    collection_name: str = "products",
    embedding_function: Optional[Any] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: str = "text-embedding-3-small",
) -> chromadb.Collection:
    """
    Create a vector store using ChromaDB from a dataframe of products.
    Always runs in memory.

    Args:
        products_df: DataFrame containing product data
        collection_name: Name of the collection in ChromaDB
        embedding_function: Custom embedding function (if None, will create an OpenAI embedding function)
        api_key: Optional OpenAI API key
        base_url: Optional base URL for OpenAI API
        model_name: The OpenAI embedding model to use

    Returns:
        The created ChromaDB collection
    """
    # Initialize the in-memory ChromaDB client
    chroma_client = chromadb.Client()
    logger.info("Initialized in-memory ChromaDB client")

    # Create embedding function if not provided
    if embedding_function is None:
        embedding_function = get_embedding_function(model_name=model_name, use_openai=True, openai_api_key=api_key)

    # Get or create the collection
    collection = chroma_client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)
    logger.info(f"Created/accessed collection: {collection_name}")

    # Extract product data and prepare for ChromaDB
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
    if documents:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)  # type: ignore
        logger.info(f"Added {len(documents)} products to the vector store")
    else:
        logger.warning("No products found in the dataframe")

    return collection


def _create_product_text(product: Union[Dict[str, Any], pd.Series]) -> str:
    """
    Create a text representation of a product for embedding.

    Args:
        product: Product data as dictionary or pandas Series

    Returns:
        Text representation of the product
    """
    # Map column names for flexibility (support different column naming conventions)
    name_fields = ["product_name", "name"]
    description_fields = ["product_description", "description"]
    category_fields = ["product_category", "category"]
    type_fields = ["product_type", "type"]

    # Extract available product information using multiple possible field names
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
    # Get other key-value pairs not already included in text
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
    Extract metadata from a product for filtering in ChromaDB.

    Args:
        product: Product data as dictionary or pandas Series

    Returns:
        Dictionary of metadata
    """
    metadata: Dict[str, Union[str, int, float, bool, None]] = {}

    # Map column names for flexibility
    id_fields = ["product_id", "id"]
    name_fields = ["product_name", "name"]
    category_fields = ["product_category", "category"]
    type_fields = ["product_type", "type"]
    price_fields = ["price"]
    stock_fields = ["stock", "stock_amount"]
    season_fields = ["seasons", "season"]

    # Helper function to get value from product
    def get_value(fields: List[str]) -> Any:
        if isinstance(product, dict):
            for field in fields:
                if field in product:
                    return product[field]
        else:  # pd.Series
            for field in fields:
                if field in product.index:
                    return product[field]
        return None

    # Extract fields
    product_id = get_value(id_fields)
    if product_id:
        metadata["product_id"] = str(product_id)

    name = get_value(name_fields)
    if name:
        metadata["name"] = str(name)

    category = get_value(category_fields)
    if category:
        metadata["category"] = str(category)

    product_type = get_value(type_fields)
    if product_type:
        metadata["type"] = str(product_type)

    price = get_value(price_fields)
    if price is not None:
        try:
            metadata["price"] = float(price)
        except (ValueError, TypeError):
            pass

    stock = get_value(stock_fields)
    if stock is not None:
        try:
            metadata["stock"] = int(stock)
        except (ValueError, TypeError):
            pass

    season = get_value(season_fields)
    if season:
        if isinstance(season, list):
            metadata["season"] = ",".join(str(s) for s in season)
        else:
            metadata["season"] = str(season)

    return metadata


def query_vector_store(
    collection: chromadb.Collection,
    query_text: str,
    n_results: int = 5,
    filter_criteria: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Any]]:
    """
    Query the vector store for similar documents.

    Args:
        collection: ChromaDB collection to query
        query_text: Text query to search for
        n_results: Number of results to return
        filter_criteria: Optional criteria for filtering results

    Returns:
        Dictionary containing query results
    """
    query_result = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=filter_criteria,
        include=["embeddings", "documents", "metadatas", "distances"],
    )

    # Convert QueryResult to Dict
    result_dict: Dict[str, List[Any]] = {}
    for key, value in query_result.items():
        if isinstance(value, list):
            result_dict[key] = value
        else:
            # Convert non-list values to a list containing the value
            result_dict[key] = [value]

    return result_dict


def load_vector_store(
    collection_name: str = "products",
    embedding_function: Optional[Any] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: str = "text-embedding-3-small",
) -> chromadb.Collection:
    """
    Load an existing ChromaDB vector store.
    Always runs in memory.

    Args:
        collection_name: Name of the collection in ChromaDB
        embedding_function: Custom embedding function (if None, will create an OpenAI embedding function)
        api_key: Optional OpenAI API key
        base_url: Optional base URL for OpenAI API
        model_name: The OpenAI embedding model to use

    Returns:
        The loaded ChromaDB collection
    """
    # Initialize the in-memory ChromaDB client
    chroma_client = chromadb.Client()
    logger.info("Initialized in-memory ChromaDB client")

    # Create embedding function if not provided
    if embedding_function is None:
        embedding_function = get_embedding_function(model_name=model_name, use_openai=True, openai_api_key=api_key)

    # Get the collection
    collection = chroma_client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)

    return collection


def similarity_search_with_score(
    collection: chromadb.Collection,
    query_text: str,
    k: int = 5,
    filter: Optional[Dict[str, Any]] = None,
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Perform similarity search and return results with scores.

    Args:
        collection: ChromaDB collection to query
        query_text: Text to search for
        k: Number of results to return
        filter: Dictionary of metadata filters

    Returns:
        List of tuples with (metadata, score)
    """
    results = collection.query(
        query_texts=[query_text],
        n_results=k,
        where=filter,
        include=["metadatas", "documents", "distances"],
    )

    # Format results as a list of tuples (metadata, score)
    formatted_results: List[Tuple[Dict[str, Any], float]] = []
    if (
        results
        and "metadatas" in results
        and results["metadatas"] is not None
        and len(results["metadatas"]) > 0
        and results["metadatas"][0] is not None
    ):
        for i, metadata in enumerate(results["metadatas"][0]):
            # Convert distance to similarity score (1 - normalized distance)
            # ChromaDB returns cosine distance, so lower is better
            distance = 1.0
            if (
                "distances" in results
                and results["distances"] is not None
                and len(results["distances"]) > 0
                and results["distances"][0] is not None  # Explicitly check the inner list
                and i < len(results["distances"][0])
            ):
                distance = results["distances"][0][i]

            score = 1.0 - min(distance, 1.0)  # Ensure score is in [0, 1]

            # Add document text to metadata for reference
            if (
                "documents" in results
                and results["documents"] is not None
                and len(results["documents"]) > 0
                and results["documents"][0] is not None  # Explicitly check the inner list
                and i < len(results["documents"][0])
            ):
                # Convert metadata to dict if it's not already to ensure copy() is available
                metadata_dict = dict(metadata) if not isinstance(metadata, dict) else metadata.copy()
                metadata_dict["document"] = results["documents"][0][i]
                formatted_results.append((metadata_dict, score))
            else:
                # Ensure we're always returning a Dict[str, Any] for consistent return type
                metadata_dict = dict(metadata) if not isinstance(metadata, dict) else metadata.copy()
                formatted_results.append((metadata_dict, score))

    return formatted_results


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
    product_description = metadata.get("document", "")  # Use document text if available
    if "description" in metadata:
        product_description = str(metadata.get("description", ""))  # Ensure description is string

    # Handle product category (convert string to enum)
    product_category_str = metadata.get("product_category", "")
    try:
        product_category = ProductCategory(product_category_str)
    except ValueError:
        # Default to first category if invalid
        product_category = next(iter(ProductCategory))
        logger.warning(f"Invalid product category: {product_category_str}, defaulting to {product_category}")

    # Extract other fields with defaults
    product_type = metadata.get("product_type", "")
    stock = int(metadata.get("stock", 0))
    price = float(metadata.get("price", 0.0))

    # Handle seasons (convert comma-separated string to list of Season enums)
    seasons = []
    if "seasons" in metadata:
        seasons_str = metadata.get("seasons", "")
        if seasons_str:
            season_names = seasons_str.split(",")
            for season_name in season_names:
                try:
                    seasons.append(Season(season_name.strip()))
                except ValueError:
                    logger.warning(f"Invalid season: {season_name}")

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


def search_products_by_description(
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

    # Handle edge cases
    if not query or not query.strip():
        logger.warning("Empty query provided to search_products_by_description")
        return []

    if collection is None:
        logger.error("No collection provided to search_products_by_description")
        return []

    try:
        # Execute similarity search
        search_results = similarity_search_with_score(
            collection=collection,
            query_text=query,
            k=top_k,
            filter=filters if filters else None,
        )

        # Convert results to Product models
        products = []
        for metadata, score in search_results:
            product = convert_to_product_model(metadata)
            # Add the search score to the product's metadata for potential use
            if product.metadata is None:
                product.metadata = {}
            product.metadata["search_score"] = score  # type: ignore[index]
            products.append(product)

        logger.info(f"Found {len(products)} products matching query: '{query}'")
        return products

    except Exception as e:
        logger.error(f"Error in search_products_by_description: {e}")
        return []


def search_products_by_name(
    collection: chromadb.Collection,
    product_name: str,
    top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Product]:
    """
    Search for products based on similar names using vector similarity search.
    This provides semantic matching rather than just fuzzy string matching.

    Args:
        collection: ChromaDB collection to query
        product_name: Name or partial name to search for
        top_k: Number of top matching products to return
        filters: Optional dictionary of metadata filters (including category and season)

    Returns:
        List of Product objects with names similar to the query
    """
    # Ensure filters is a dictionary
    if filters is None:
        filters = {}

    # Use 'document' field for name search as it contains the product name
    query_text = f"Product: {product_name}"

    if not product_name or not product_name.strip():
        logger.warning("Empty product name provided to search_products_by_name")
        return []

    if collection is None:
        logger.error("No collection provided to search_products_by_name")
        return []

    try:
        # Execute similarity search
        search_results = similarity_search_with_score(
            collection=collection, query_text=query_text, k=top_k, filter=filters
        )

        # Convert results to Product models
        products = []
        for metadata, score in search_results:
            product = convert_to_product_model(metadata)
            # Add the search score to the product's metadata
            if product.metadata is None:
                product.metadata = {}
            product.metadata["search_score"] = score  # type: ignore[index]
            products.append(product)

        logger.info(f"Found {len(products)} products with names similar to: '{product_name}'")
        return products

    except Exception as e:
        logger.error(f"Error in search_products_by_name: {e}")
        return []


def create_filter_dict(
    category: Optional[str] = None,
    season: Optional[str] = None,
    min_stock: Optional[int] = None,
    price_range: Optional[Tuple[float, float]] = None,
    **additional_filters,
) -> Dict[str, Any]:
    """
    Create a filter dictionary for ChromaDB queries with support for common product filters.

    Args:
        category: Optional product category to filter by
        season: Optional season to filter by (will do partial match within seasons list)
        min_stock: Optional minimum stock level
        price_range: Optional tuple of (min_price, max_price)
        **additional_filters: Any additional filter key-value pairs

    Returns:
        Dictionary of filters compatible with ChromaDB where clause
    """
    filters = {}

    # Add category filter
    if category:
        filters["product_category"] = category

    # Add season filter (needs special handling since seasons are stored as comma-separated string)
    if season:
        # ChromaDB has limited filtering capabilities for string contained in a list
        # This approach relies on our data storage format where seasons are comma-separated
        filters["seasons"] = {"$contains": season}  # type: ignore

    # Add stock filter (greater than or equal to)
    if min_stock is not None:
        filters["stock"] = {"$gte": min_stock}  # type: ignore

    # Add price range filter
    if price_range and len(price_range) == 2:
        min_price, max_price = price_range
        if min_price is not None:
            filters["price"] = {"$gte": min_price}  # type: ignore
        if max_price is not None:
            if "price" in filters:
                filters["price"]["$lte"] = max_price  # type: ignore
            else:
                filters["price"] = {"$lte": max_price}  # type: ignore

    # Add any additional filters
    filters.update(additional_filters)

    return filters


def filtered_search_products(
    collection: chromadb.Collection,
    query: str,
    top_k: int = 5,
    category: Optional[str] = None,
    season: Optional[str] = None,
    min_stock: Optional[int] = None,
    price_range: Optional[Tuple[float, float]] = None,
    search_type: str = "description",  # 'description' or 'name'
) -> List[Product]:
    """
    Search for products with flexible filtering options.

    Args:
        collection: ChromaDB collection to query
        query: Text to search for
        top_k: Number of results to return
        category: Optional product category to filter by
        season: Optional season to filter by
        min_stock: Optional minimum stock level
        price_range: Optional tuple of (min_price, max_price)
        search_type: Whether to search by 'description' or 'name'

    Returns:
        List of matching Product objects
    """
    # Create filter dictionary
    filters = create_filter_dict(category=category, season=season, min_stock=min_stock, price_range=price_range)

    # Choose the search method based on search_type
    if search_type.lower() == "name":
        return search_products_by_name(collection=collection, product_name=query, top_k=top_k, filters=filters)
    else:  # Default to description search
        return search_products_by_description(
            collection=collection,
            query=query,
            top_k=top_k,
            filters=filters,  # Pass the filters directly
        )


def create_openai_embedding_function(
    model_name: str = "text-embedding-3-small",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Any:
    """
    Create an OpenAI embedding function for the vector store.

    Args:
        model_name: The OpenAI embedding model to use.
        api_key: Optional OpenAI API key. If not provided, will look for OPENAI_API_KEY env var.
        base_url: Optional base URL for OpenAI API.

    Returns:
        An OpenAI embedding function compatible with ChromaDB.
    """
    # Get API key from environment if not provided
    effective_api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not effective_api_key:
        raise ValueError("OpenAI API key is required for OpenAI embeddings")

    # Create OpenAI embedding function
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=effective_api_key,
        model_name=model_name,
        api_base=base_url,  # This will use the default if None
    )
