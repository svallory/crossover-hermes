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

# Should be using the correct import for embedding functions
try:
    # Modern chromadb versions
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:
    try:
        # Old chromadb versions might have it in a different location
        from chromadb.utils import SentenceTransformerEmbeddingFunction
    except ImportError:
        # Fallback for very old versions or if the module structure changed
        logging.error(
            "Could not import SentenceTransformerEmbeddingFunction - vector store will not be functional"
        )
        SentenceTransformerEmbeddingFunction = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vector_store")

from src.hermes.model import ProductCategory, Product, Season


def create_openai_embedding_function(
    model_name: str = "text-embedding-3-small",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Any:
    """
    Create an embedding function using OpenAI's embedding models.

    Args:
        model_name: The name of the OpenAI embedding model to use
        api_key: Optional API key to use (if None, will use OPENAI_API_KEY from environment)
        base_url: Optional base URL for OpenAI API (useful for custom API endpoints)

    Returns:
        An embedding function compatible with ChromaDB

    Raises:
        ValueError: If OpenAI API key is missing or embedding creation fails
    """
    from langchain_openai import OpenAIEmbeddings

    # Try to import LangchainEmbeddings from different possible locations
    try:
        # Modern chromadb versions
        from chromadb.utils.embedding_functions import LangchainEmbeddings
    except ImportError:
        try:
            # Alternative location in some versions
            from chromadb.utils import LangchainEmbeddings
        except ImportError:
            # Fallback solution for testing
            logger.warning(
                "Could not import LangchainEmbeddings. Using direct embedding function instead."
            )

            # Define a simple wrapper class that mimics LangchainEmbeddings for testing
            class MockLangchainEmbeddings:
                def __init__(self, embeddings_model):
                    self.embeddings_model = embeddings_model

                def __call__(self, input):
                    # Direct call to the embeddings model's embed_documents method
                    # ChromaDB expects 'input' parameter (not 'texts')
                    if isinstance(input, str):
                        input = [input]
                    return self.embeddings_model.embed_documents(input)

            LangchainEmbeddings = MockLangchainEmbeddings

    # Get API key from arguments or environment
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OpenAI API key is required. Provide it as an argument or set OPENAI_API_KEY environment variable."
        )

    # Initialize embeddings with optional base_url
    kwargs = {"model": model_name, "openai_api_key": api_key}
    if base_url:
        kwargs["openai_api_base"] = base_url

    openai_embeddings = OpenAIEmbeddings(**kwargs)
    embedding_function = LangchainEmbeddings(openai_embeddings)
    logger.info(f"Created OpenAI embedding function using {model_name}")
    return embedding_function


def _create_embedding_function(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: str = "text-embedding-3-small",
) -> Any:
    """
    Create an embedding function using OpenAI's embedding models exclusively.

    Args:
        api_key: Optional OpenAI API key
        base_url: Optional base URL for OpenAI API
        model_name: The name of the OpenAI embedding model to use

    Returns:
        An embedding function for ChromaDB

    Raises:
        ValueError: If embedding function creation fails
    """
    return create_openai_embedding_function(
        model_name=model_name, api_key=api_key, base_url=base_url
    )


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
        embedding_function = _create_embedding_function(
            api_key=api_key, base_url=base_url, model_name=model_name
        )

    # Get or create the collection
    collection = chroma_client.get_or_create_collection(
        name=collection_name, embedding_function=embedding_function
    )
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
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
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
    product_name = next(
        (product.get(field, "") for field in name_fields if field in product), ""
    )
    product_description = next(
        (product.get(field, "") for field in description_fields if field in product), ""
    )
    product_category = next(
        (product.get(field, "") for field in category_fields if field in product), ""
    )
    product_type = next(
        (product.get(field, "") for field in type_fields if field in product), ""
    )

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
    exclude_fields = set(
        name_fields + description_fields + category_fields + type_fields
    )
    for key, value in product.items():
        if key not in exclude_fields and value and not key.startswith("_"):
            text_parts.append(f"{key}: {value}")

    return " ".join(text_parts)


def _extract_product_metadata(
    product: Union[Dict[str, Any], pd.Series],
) -> Dict[str, Any]:
    """
    Extract metadata from a product for filtering in ChromaDB.

    Args:
        product: Product data as dictionary or pandas Series

    Returns:
        Dictionary of metadata
    """
    metadata = {}

    # Map column names for flexibility
    id_fields = ["product_id", "id"]
    name_fields = ["product_name", "name"]
    category_fields = ["product_category", "category"]
    type_fields = ["product_type", "type"]
    price_fields = ["price"]
    stock_fields = ["stock", "stock_amount"]
    season_fields = ["seasons", "season"]

    # Extract core product attributes as metadata using multiple possible field names
    # Product ID
    for field in id_fields:
        if field in product:
            metadata["product_id"] = str(product[field])
            break

    # Product Name
    for field in name_fields:
        if field in product:
            metadata["product_name"] = str(product[field])
            break

    # Product Category
    for field in category_fields:
        if field in product:
            if isinstance(product[field], ProductCategory):
                metadata["product_category"] = product[field].value
            else:
                metadata["product_category"] = str(product[field])
            break

    # Product Type
    for field in type_fields:
        if field in product:
            metadata["product_type"] = str(product[field])
            break

    # Price
    for field in price_fields:
        if field in product and pd.notna(product[field]):
            metadata["price"] = float(product[field])
            break

    # Stock
    for field in stock_fields:
        if field in product and pd.notna(product[field]):
            metadata["stock"] = int(product[field])
            break

    # Seasons
    for field in season_fields:
        if field in product and product[field]:
            if isinstance(product[field], list):
                seasons_str = ",".join(
                    [
                        s.value if isinstance(s, Season) else str(s)
                        for s in product[field]
                    ]
                )
                metadata["seasons"] = seasons_str
            elif not pd.isna(product[field]):
                metadata["seasons"] = str(product[field])
            break

    # Clean metadata by removing None values
    return {k: v for k, v in metadata.items() if v is not None}


def query_vector_store(
    collection: chromadb.Collection,
    query_text: str,
    n_results: int = 5,
    filter_criteria: Optional[Dict[str, Any]] = None,
) -> Dict[str, List]:
    """
    Query the vector store for similar products.

    Args:
        collection: ChromaDB collection to query
        query_text: Text to search for
        n_results: Number of results to return
        filter_criteria: Dictionary of metadata filters

    Returns:
        Dictionary with query results
    """
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=filter_criteria,
    )

    return results


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
        embedding_function = _create_embedding_function(
            api_key=api_key, base_url=base_url, model_name=model_name
        )

    # Get the collection
    collection = chroma_client.get_or_create_collection(
        name=collection_name, embedding_function=embedding_function
    )

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
    formatted_results = []
    if results and results["metadatas"] and results["metadatas"][0]:
        for i, metadata in enumerate(results["metadatas"][0]):
            # Convert distance to similarity score (1 - normalized distance)
            # ChromaDB returns cosine distance, so lower is better
            distance = (
                results["distances"][0][i]
                if "distances" in results and results["distances"][0]
                else 1.0
            )
            score = 1.0 - min(distance, 1.0)  # Ensure score is in [0, 1]

            # Add document text to metadata for reference
            if "documents" in results and results["documents"][0]:
                metadata["document"] = results["documents"][0][i]

            formatted_results.append((metadata, score))

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
        product_description = metadata.get("description")

    # Handle product category (convert string to enum)
    product_category_str = metadata.get("product_category", "")
    try:
        product_category = ProductCategory(product_category_str)
    except ValueError:
        # Default to first category if invalid
        product_category = next(iter(ProductCategory))
        logger.warning(
            f"Invalid product category: {product_category_str}, defaulting to {product_category}"
        )

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
    # Handle edge cases
    if not query or not query.strip():
        logger.warning("Empty query provided to search_products_by_description")
        return []

    if collection is None:
        logger.error("No collection provided to search_products_by_description")
        return []

    # Prepare filter criteria - support both old and new filtering methods
    filter_criteria = filters or {}

    # For backward compatibility with category_filter parameter
    if category_filter and "product_category" not in filter_criteria:
        filter_criteria["product_category"] = category_filter

    try:
        # Execute similarity search
        search_results = similarity_search_with_score(
            collection=collection,
            query_text=query,
            k=top_k,
            filter=filter_criteria if filter_criteria else None,
        )

        # Convert results to Product models
        products = []
        for metadata, score in search_results:
            product = convert_to_product_model(metadata)
            # Add the search score to the product's metadata for potential use
            if not hasattr(product, "metadata"):
                product.metadata = {}
            product.metadata["search_score"] = score
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
    if not product_name or not product_name.strip():
        logger.warning("Empty product name provided to search_products_by_name")
        return []

    if collection is None:
        logger.error("No collection provided to search_products_by_name")
        return []

    # Create a search query focused on product name
    query_text = f"Product: {product_name}"

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
            if not hasattr(product, "metadata"):
                product.metadata = {}
            product.metadata["search_score"] = score
            products.append(product)

        logger.info(
            f"Found {len(products)} products with names similar to: '{product_name}'"
        )
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
        filters["seasons"] = {"$contains": season}

    # Add stock filter (greater than or equal to)
    if min_stock is not None:
        filters["stock"] = {"$gte": min_stock}

    # Add price range filter
    if price_range and len(price_range) == 2:
        min_price, max_price = price_range
        if min_price is not None:
            filters["price"] = {"$gte": min_price}
        if max_price is not None:
            if "price" in filters:
                filters["price"]["$lte"] = max_price
            else:
                filters["price"] = {"$lte": max_price}

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
    filters = create_filter_dict(
        category=category, season=season, min_stock=min_stock, price_range=price_range
    )

    # Choose the search method based on search_type
    if search_type.lower() == "name":
        return search_products_by_name(
            collection=collection, product_name=query, top_k=top_k, filters=filters
        )
    else:  # Default to description search
        return search_products_by_description(
            collection=collection,
            query=query,
            top_k=top_k,
            filters=filters,  # Pass the filters directly
        )
