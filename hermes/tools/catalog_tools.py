import logging
from typing import Any, Literal

from langchain_core.tools import tool

# Import tool from langchain_core
from pydantic import BaseModel, Field

# For fuzzy matching

# Import the load_products_df function
from hermes.data.load_data import load_products_df

# LangChain Chroma integration

# Explicitly ignore import not found errors
from hermes.model import ProductCategory, Season
from hermes.model.product import AlternativeProduct, Product, Season
from hermes.model.errors import ProductNotFound
from hermes.model.email import ProductMention

# Import get_vector_store and metadata conversion from hermes.data.vector_store
from hermes.data.vector_store import get_vector_store, metadata_to_product

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure resolution thresholds
SIMILAR_MATCH_THRESHOLD = 0.75  # Threshold for potential matches to consider

_vector_store = get_vector_store()


class FuzzyMatchResult(BaseModel):
    """Result of a fuzzy name match."""

    matched_product: Product
    similarity_score: float = Field(description="Similarity score between 0.0 and 1.0")


ResolutionMethod = Literal[
    "exact_id_match",
    "semantic_search",
    "fuzzy_name_match",
    "complementary_category_match",
    "price_similarity_match",
    "filtered_search",
    "occasion_search",
]


def create_metadata_string(
    resolution_confidence: float | None = None,
    resolution_method: ResolutionMethod | None = None,
    requested_quantity: int | None = None,
    search_query: str | None = None,
    similarity_score: float | None = None,
) -> str | None:
    """Create a natural language metadata string from resolution information."""
    parts = []

    if resolution_confidence is not None:
        confidence_pct = int(resolution_confidence * 100)
        parts.append(f"Resolution confidence: {confidence_pct}%")

    if resolution_method:
        method_desc = {
            "exact_id_match": "Found by exact product ID match",
            "semantic_search": "Found through semantic search",
            "fuzzy_name_match": "Found through fuzzy name matching",
            "complementary_category_match": "Found by complementary category",
            "price_similarity_match": "Found by price similarity",
            "filtered_search": "Found by filtered search",
            "occasion_search": "Found by occasion-based search",
        }.get(resolution_method, f"Resolution method: {resolution_method}")
        parts.append(method_desc)

    if requested_quantity is not None:
        parts.append(f"Requested quantity: {requested_quantity}")

    if search_query:
        parts.append(f"Search query: '{search_query}'")

    if similarity_score is not None:
        parts.append(f"Similarity score: {similarity_score:.3f}")

    return "; ".join(parts) if parts else None


def _parse_seasons_string(seasons_str: str | None, product_id: str) -> list[Season]:
    seasons_list: list[Season] = []
    if seasons_str and seasons_str != "None" and seasons_str != "nan":
        seasons_list.extend(
            Season(season.strip())
            for season in seasons_str.split(",")
            if season.strip()
        )

    return seasons_list


def _create_product_from_row(
    product_row: Any, metadata_str: str | None = None
) -> Product:
    # Process seasons
    seasons_list = _parse_seasons_string(
        str(product_row.get("seasons", None)), str(product_row["product_id"])
    )

    return Product(
        product_id=str(product_row["product_id"]),
        name=str(product_row["name"]),
        description=str(product_row["description"]),
        category=ProductCategory(str(product_row["category"])),
        product_type=str(product_row.get("type", "")),
        stock=int(product_row["stock"]),
        price=float(product_row["price"]),
        seasons=seasons_list,
        metadata=metadata_str,
    )


def _add_search_metadata_to_product(
    product: Product,
    raw_score: float,  # Typically distance score from ChromaDB
    resolution_method: ResolutionMethod,
    search_query: str | None = None,
    requested_quantity: int | None = None,
) -> Product:
    """Calculates confidence, creates metadata string, and assigns it to the product.

    Args:
        product: The Product object to modify.
        raw_score: The raw score from vector search (assumed to be distance).
        resolution_method: The method used for resolution.
        search_query: The original search query.
        requested_quantity: The requested quantity, if applicable.

    Returns:
        The Product object with metadata updated.
    """
    # Convert distance score to similarity/confidence (lower distance = higher confidence)
    confidence = max(0.0, min(1.0, 1.0 - (raw_score / 2.0)))

    metadata_str = create_metadata_string(
        resolution_confidence=confidence,
        resolution_method=resolution_method,
        search_query=search_query,
        similarity_score=raw_score,  # Pass the original score for transparency
        requested_quantity=requested_quantity,
    )
    product.metadata = metadata_str
    return product


def _convert_vector_results_to_products(
    results: list[tuple[Any, float]],
    resolution_method: ResolutionMethod,
    search_query: str | None = None,
    requested_quantity: int | None = None,
) -> list[Product]:
    """Convert vector search results to Product objects with metadata.

    Args:
        results: List of (document, score) tuples from vector search
        resolution_method: Method used for resolution (for metadata)
        search_query: Original search query (for metadata)
        requested_quantity: Requested quantity (for metadata)

    Returns:
        List of Product objects with search metadata attached
    """
    products = []

    for doc, score_val in results:  # Renamed score to score_val
        try:
            product = metadata_to_product(doc.metadata)

            product = _add_search_metadata_to_product(
                product, score_val, resolution_method, search_query, requested_quantity
            )

            products.append(product)
        except Exception as e:
            logger.error(f"Error converting document to product: {e}")
            continue

    return products


@tool(parse_docstring=True)
def find_product_by_id(product_id: str) -> Product | ProductNotFound:
    """Find a product by its exact product ID.

    Args:
        product_id: The exact product ID to search for.

    Returns:
        The matching Product object, or ProductNotFound if no match exists.
    Raises:
        ValueError: If the product catalog cannot be loaded.
    """
    products_df = load_products_df()

    # Filter for exact product ID match (case-insensitive)
    matching_products = products_df[
        products_df["product_id"].str.upper() == product_id.upper()
    ]

    if matching_products.empty:
        return ProductNotFound(
            message=f"No product found with ID '{product_id}'",
            query_product_id=product_id,
        )

    # Get the first (and should be only) match
    product_row = matching_products.iloc[0]

    # Create Product object with metadata
    metadata_str = create_metadata_string(
        resolution_confidence=1.0, resolution_method="exact_id_match"
    )

    return _create_product_from_row(product_row, metadata_str)


@tool(parse_docstring=True)
def find_product_by_name(
    *, product_name: str, threshold: float | None, top_n: int | None
) -> list[FuzzyMatchResult] | ProductNotFound:
    """Find products by name using fuzzy matching.

    Args:
        product_name: The product name to search for.
        threshold: Minimum similarity score. If None, defaults to 0.6.
        top_n: Maximum number of results. If None, defaults to 5.

    Returns:
        List of FuzzyMatchResult objects sorted by similarity score (highest first),
        or ProductNotFound if no matches above threshold.
    Raises:
        ValueError: If the product catalog cannot be loaded.
        ImportError: If rapidfuzz is not installed.
        Exception: For other unexpected errors during the fuzzy matching process.
    """
    # Handle None values with defaults
    if threshold is None:
        threshold = 0.6
    if top_n is None:
        top_n = 5

    # These can raise ImportError and ValueError respectively, should propagate
    from rapidfuzz import fuzz

    products_df = load_products_df()

    try:
        # Calculate similarity scores for all products
        similarities = []
        for _, row in products_df.iterrows():
            # Use token_sort_ratio for better matching of product names
            score = fuzz.token_sort_ratio(
                product_name.lower(), str(row["name"]).lower()
            )
            normalized_score = score / 100.0  # Convert to 0-1 range

            if normalized_score >= threshold:
                similarities.append((row, normalized_score))

        if not similarities:
            return ProductNotFound(
                message=f"No products found matching '{product_name}' with similarity >= {threshold}",
                query_product_name=product_name,
            )

        # Sort by similarity score (highest first) and take top_n
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_matches = similarities[:top_n]

        # Convert to FuzzyMatchResult objects
        results = []
        for product_row, similarity_score in top_matches:
            metadata_str = create_metadata_string(
                resolution_confidence=similarity_score,
                resolution_method="fuzzy_name_match",
                search_query=product_name,
                similarity_score=similarity_score,
            )
            product = _create_product_from_row(product_row, metadata_str)
            results.append(
                FuzzyMatchResult(
                    matched_product=product, similarity_score=similarity_score
                )
            )
        return results
    except Exception as e:
        logger.error(
            f"Unexpected error during fuzzy name search for '{product_name}': {e}",
            exc_info=True,
        )
        raise  # Re-raise the caught exception to allow it to propagate


def search_products_by_description(
    query: str,
    top_k: int = 3,
    category_filter: str | None = None,
    season_filter: str | None = None,
) -> list[Product] | ProductNotFound:
    """Search products by description using vector similarity.

    Args:
        query: The search query/description
        top_k: Maximum number of results to return
        category_filter: Optional category to filter by
        season_filter: Optional season to filter by

    Returns:
        List of matching Product objects or ProductNotFound if no matches.
    Raises:
        ValueError: If the product catalog (via vector store) cannot be loaded.
        Exception: For other unexpected errors during the search process.
    """
    # _perform_vector_search can raise ValueError if catalog load fails, should propagate
    try:
        filters = {}
        if category_filter:
            filters["category"] = category_filter
        if season_filter:
            filters["season"] = season_filter

        results = _vector_store.similarity_search_with_score(
            query, top_k, filters if filters else None
        )

        if not results:
            return ProductNotFound(
                message=f"No products found matching description: '{query}'",
                query_product_name=query,
            )

        products = _convert_vector_results_to_products(
            results, "semantic_search", search_query=query
        )

        if not products:
            return ProductNotFound(
                message=f"No valid products found after processing search results for: '{query}'",
                query_product_name=query,
            )
        return products
    except ValueError:  # Specifically to allow catalog loading errors from _perform_vector_search to propagate
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during product description search for '{query}': {e}",
            exc_info=True,
        )
        raise  # Re-raise other unexpected exceptions


@tool(parse_docstring=True, name_or_callable="find_complementary_products")
def find_complementary_products(
    *, product_id: str, limit: int | None
) -> list[Product] | ProductNotFound:
    """Find products that complement or go well with the specified product.

    Args:
        product_id: The product ID to find complements for.
        limit: Maximum number of complementary products to return. If None, defaults to 3.

    Returns:
        List of complementary Product objects, or ProductNotFound if none found.
    Raises:
        ValueError: If the product catalog cannot be loaded.
        Exception: For other unexpected errors during the complement finding process.
    """
    if limit is None:
        limit = 3

    products_df = load_products_df()  # Can raise ValueError

    try:
        original_product_df_match = products_df[
            products_df["product_id"].str.upper() == product_id.upper()
        ]

        if original_product_df_match.empty:
            return ProductNotFound(
                message=f"Original product '{product_id}' not found",
                query_product_id=product_id,
            )

        original_row = original_product_df_match.iloc[0]
        original_category = str(original_row["category"])

        complementary_categories = {
            "Women's Clothing": ["Accessories", "Women's Shoes", "Bags"],
            "Men's Clothing": ["Men's Accessories", "Men's Shoes", "Bags"],
            "Women's Shoes": ["Women's Clothing", "Accessories", "Bags"],
            "Men's Shoes": ["Men's Clothing", "Men's Accessories", "Bags"],
            "Accessories": ["Women's Clothing", "Men's Clothing", "Bags"],
            "Bags": ["Women's Clothing", "Men's Clothing", "Accessories"],
            "Kid's Clothing": ["Accessories", "Bags"],
            "Loungewear": ["Accessories", "Bags"],
        }

        target_categories = complementary_categories.get(original_category, [])

        if not target_categories:
            return ProductNotFound(
                message=f"No complementary categories defined for '{original_category}'",
                query_product_id=product_id,
            )

        # Renamed from complementary_products_df to complementary_matches_df
        complementary_matches_df = products_df[
            (products_df["category"].isin(target_categories))
            & (products_df["stock"] > 0)
        ]

        if complementary_matches_df.empty:
            return ProductNotFound(
                message=f"No in-stock complementary products found for '{product_id}'",
                query_product_id=product_id,
            )

        # Renamed from sampled_products_df to sampled_matches_df
        sampled_matches_df = complementary_matches_df.nlargest(limit, "stock")

        result_products = []
        for _, row in sampled_matches_df.iterrows():
            metadata_str = create_metadata_string(
                resolution_confidence=0.8,
                resolution_method="complementary_category_match",
            )
            product = _create_product_from_row(row, metadata_str)
            result_products.append(product)

        if (
            not result_products
        ):  # This case should be rare if sampled_matches_df was not empty
            return ProductNotFound(
                message=f"Error processing complementary products for '{product_id}' (no products created)",  # pragma: no cover
                query_product_id=product_id,  # pragma: no cover
            )  # pragma: no cover

        return result_products
    except Exception as e:
        logger.error(
            f"Unexpected error while finding complementary products for '{product_id}': {e}",
            exc_info=True,
        )
        raise  # Re-raise the caught exception


@tool(parse_docstring=True)
def search_products_with_filters(
    *,
    query: str,
    category: str | None,
    season: str | None,
    min_price: float | None,
    max_price: float | None,
    min_stock: int | None,
    top_k: int | None,
) -> list[Product] | ProductNotFound:
    """Search products with multiple filters applied.

    Args:
        query: Search query for product names/descriptions.
        category: Filter by product category. If None, no category filter applied.
        season: Filter by season. If None, no season filter applied.
        min_price: Minimum price filter. If None, no minimum price filter applied.
        max_price: Maximum price filter. If None, no maximum price filter applied.
        min_stock: Minimum stock filter. If None, no stock filter applied.
        top_k: Maximum number of results. If None, defaults to 5.

    Returns:
        List of matching Product objects, or ProductNotFound if no matches.
    Raises:
        ValueError: If the product catalog (via vector store) cannot be loaded.
        Exception: For other unexpected errors during the search process.
    """
    if top_k is None:
        top_k = 5

    # _perform_vector_search can raise ValueError if catalog load fails, should propagate
    try:
        where_clause: dict[str, Any] = {}
        if category:
            where_clause["category"] = category
        if season:
            where_clause["season"] = season

        results = _vector_store.similarity_search_with_score(
            query, top_k * 2, where_clause if where_clause else None
        )

        if not results:
            return ProductNotFound(
                message=f"No products found matching query: '{query}' with initial filters",
                query_product_name=query,
            )

        filtered_products = []
        for doc, score_val in results:
            try:
                product = metadata_to_product(doc.metadata)
                if min_price is not None and product.price < min_price:
                    continue
                if max_price is not None and product.price > max_price:
                    continue
                if min_stock is not None and product.stock < min_stock:
                    continue

                product = _add_search_metadata_to_product(
                    product, score_val, "filtered_search", search_query=query
                )
                filtered_products.append(product)
                if len(filtered_products) >= top_k:
                    break
            except Exception as conversion_error:
                logger.error(
                    f"Error processing filtered product entry for query '{query}': {conversion_error}",
                    exc_info=True,
                )  # pragma: no cover
                continue  # pragma: no cover

        if not filtered_products:
            return ProductNotFound(
                message=f"No products found matching all specified filters for query: '{query}'",
                query_product_name=query,
            )
        return filtered_products
    except ValueError:  # Specifically to allow catalog loading errors from _perform_vector_search to propagate
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during filtered product search for '{query}': {e}",
            exc_info=True,
        )
        raise  # Re-raise other unexpected exceptions


@tool(parse_docstring=True)
def find_products_for_occasion(
    *, occasion: str, limit: int | None
) -> list[Product] | ProductNotFound:
    """Find products suitable for a specific occasion or event.

    Args:
        occasion: The occasion or event (e.g., "wedding", "business meeting", "casual outing").
        limit: Maximum number of products to return. If None, defaults to 5.

    Returns:
        List of suitable Product objects, or ProductNotFound if none found.
    Raises:
        ValueError: If the product catalog (via vector store) cannot be loaded.
        Exception: For other unexpected errors during the search process.
    """
    if limit is None:
        limit = 5

    # _perform_vector_search can raise ValueError if catalog load fails, should propagate
    try:
        search_query = f"{occasion} outfit clothing attire"
        results = _vector_store.similarity_search_with_score(search_query, limit * 2)

        if not results:
            return ProductNotFound(
                message=f"No products found for occasion: '{occasion}' via initial search",
                query_product_name=occasion,
            )

        suitable_products = []
        for doc, score_val in results:
            try:
                product = metadata_to_product(doc.metadata)
                if product.stock > 0:
                    product = _add_search_metadata_to_product(
                        product, score_val, "occasion_search", search_query=search_query
                    )
                    suitable_products.append(product)
                    if len(suitable_products) >= limit:
                        break
            except Exception as conversion_error:
                logger.error(
                    f"Error processing product for occasion '{occasion}': {conversion_error}",
                    exc_info=True,
                )  # pragma: no cover
                continue  # pragma: no cover

        if not suitable_products:
            return ProductNotFound(
                message=f"No in-stock products found suitable for occasion: '{occasion}'",
                query_product_name=occasion,
            )
        return suitable_products
    except ValueError:  # Specifically to allow catalog loading errors from _perform_vector_search to propagate
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error while finding products for occasion '{occasion}': {e}",
            exc_info=True,
        )
        raise  # Re-raise other unexpected exceptions


def find_alternatives(
    original_product_id: str, limit: int = 2
) -> list[AlternativeProduct] | ProductNotFound:
    """Find alternative products similar to the specified product.

    Args:
        original_product_id: The product ID to find alternatives for
        limit: Maximum number of alternatives to return

    Returns:
        List of AlternativeProduct objects or ProductNotFound if none found.
    Raises:
        ValueError: If the product catalog cannot be loaded.
        Exception: For other unexpected errors during the alternative finding process.
    """
    products_df = load_products_df()  # Can raise ValueError

    try:
        original_product_df_match = products_df[
            products_df["product_id"].str.upper() == original_product_id.upper()
        ]

        if original_product_df_match.empty:
            return ProductNotFound(
                message=f"Original product '{original_product_id}' not found",
                query_product_id=original_product_id,
            )

        original_row = original_product_df_match.iloc[0]
        original_category = str(original_row["category"])
        original_price = float(original_row["price"])

        alternatives_df_filtered = products_df[
            (products_df["category"] == original_category)
            & (products_df["product_id"].str.upper() != original_product_id.upper())
            & (products_df["stock"] > 0)
        ]

        if alternatives_df_filtered.empty:
            return ProductNotFound(
                message=f"No in-stock alternatives found for product '{original_product_id}'.",
                query_product_id=original_product_id,
            )

        alternatives_df_with_similarity = alternatives_df_filtered.copy()
        alternatives_df_with_similarity.loc[:, "price_similarity"] = (
            alternatives_df_with_similarity[
                "price"
            ].apply(
                lambda x: 1.0
                - abs(float(x) - original_price) / max(original_price, float(x))
            )
        )

        sorted_alternatives_df = alternatives_df_with_similarity.sort_values(
            "price_similarity", ascending=False
        )

        top_alternatives_df = sorted_alternatives_df.head(limit)

        result_alternatives = []
        for _, row in top_alternatives_df.iterrows():
            similarity_score = float(row["price_similarity"])
            metadata_str = create_metadata_string(
                resolution_confidence=similarity_score,
                resolution_method="price_similarity_match",
            )
            product = _create_product_from_row(row, metadata_str)

            if similarity_score > 0.9:
                reason = f"Very similar price (${float(row['price']):.2f} vs ${original_price:.2f}) and currently in stock"
            elif similarity_score > 0.7:
                reason = f"Similar price range and currently in stock ({int(row['stock'])} available)"
            else:
                reason = f"Same category alternative that's currently available ({int(row['stock'])} in stock)"

            alternative = AlternativeProduct(
                product=product, similarity_score=similarity_score, reason=reason
            )
            result_alternatives.append(alternative)

        if not result_alternatives:
            return ProductNotFound(
                message=f"Error processing alternatives for '{original_product_id}' (no alternatives created)",  # pragma: no cover
                query_product_id=original_product_id,  # pragma: no cover
            )  # pragma: no cover

        return result_alternatives
    except Exception as e:
        logger.error(
            f"Unexpected error while finding alternatives for '{original_product_id}': {e}",
            exc_info=True,
        )
        raise  # Re-raise other unexpected exceptions


async def resolve_product_mention(
    mention: ProductMention,
    top_k: int = 3,
) -> list[Product] | ProductNotFound:
    """Resolve a single ProductMention to top-K candidate products using ChromaDB's capabilities.

    This function leverages ChromaDB's metadata filtering and similarity search to find
    the most relevant product candidates. The results are intended to be used as context
    for LLM-based disambiguation.

    Args:
        mention: The product mention to resolve
        top_k: Maximum number of candidate products to return (default: 3)

    Returns:
        A list of candidate Product objects ranked by relevance, or ProductNotFound if no candidates found.
    Raises:
        ValueError: If the product catalog (via find_product_by_id or vector store) cannot be loaded.
        Exception: For other unexpected errors during the resolution process.
    """
    # find_product_by_id.ainvoke and _perform_vector_search can raise ValueError if catalog fails, should propagate.
    try:
        candidates = []

        if mention.product_id:
            # This call itself will propagate ValueError from load_products_df if catalog is unavailable
            id_result: Product | ProductNotFound = await find_product_by_id.ainvoke(
                {"product_id": mention.product_id}
            )
            if isinstance(id_result, Product):
                metadata_str = create_metadata_string(
                    resolution_confidence=1.0,
                    resolution_method="exact_id_match",
                    requested_quantity=mention.quantity,
                )
                id_result.metadata = metadata_str
                return [id_result]
            elif isinstance(id_result, ProductNotFound):
                logger.info(
                    f"Exact ID '{mention.product_id}' not found, proceeding with other attributes."
                )

        search_parts = []
        if mention.product_name:
            search_parts.append(mention.product_name)
        if mention.product_description:
            search_parts.append(mention.product_description)
        if mention.product_type:
            search_parts.append(mention.product_type)

        if not search_parts:
            return ProductNotFound(
                message=f"No searchable information in mention (after attempting ID match): {mention}",
                query_product_name=mention.product_name,
                query_product_id=mention.product_id,
            )

        search_query = " ".join(search_parts)

        filters = {}
        if mention.product_category:
            filters["category"] = str(mention.product_category.value)

        # This call can propagate ValueError from get_vector_store -> load_products_df
        results = _vector_store.similarity_search_with_score(
            search_query, top_k, filters if filters else None
        )

        if not results:
            return ProductNotFound(
                message=f"No products found matching vector search query: '{search_query}'",
                query_product_name=mention.product_name,
                query_product_id=mention.product_id,
            )

        for doc, score_val in results:
            confidence = max(0.0, min(1.0, 1.0 - (score_val / 2.0)))
            if confidence >= SIMILAR_MATCH_THRESHOLD:
                try:
                    product_candidate = metadata_to_product(doc.metadata)
                    product_candidate = _add_search_metadata_to_product(
                        product_candidate,
                        score_val,
                        "semantic_search",
                        search_query=search_query,
                        requested_quantity=mention.quantity,
                    )
                    candidates.append(product_candidate)
                except Exception as conversion_error:
                    logger.error(
                        f"Error converting document to product during mention resolution for query '{search_query}': {conversion_error}",
                        exc_info=True,
                    )  # pragma: no cover
                    continue  # pragma: no cover

        if not candidates:
            return ProductNotFound(
                message=f"No candidates above threshold {SIMILAR_MATCH_THRESHOLD} for query: '{search_query}'",
                query_product_name=mention.product_name,
                query_product_id=mention.product_id,
            )
        return candidates
    except ValueError:  # Specifically to allow catalog loading errors to propagate
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during product mention resolution for '{mention}': {e}",
            exc_info=True,
        )
        raise  # Re-raise other unexpected exceptions
