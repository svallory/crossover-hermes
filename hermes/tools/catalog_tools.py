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
from hermes.data.vector_store import (
    get_vector_store,
    metadata_to_product,
)
from hermes.utils.logger import logger


# Configure resolution thresholds
SIMILAR_MATCH_THRESHOLD = 0.65  # Threshold for potential matches to consider - CURRENTLY UNUSED FOR VECTOR SEARCH
MAX_VECTOR_SEARCH_L2_DISTANCE = (
    1.2  # New threshold for filtering raw vector search results
)


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


def _create_metadata_string(
    resolution_method: ResolutionMethod | None = None,
    requested_quantity: int | None = None,
    search_query: str | None = None,
    similarity_score: float | None = None,
) -> str | None:
    """Create a natural language metadata string from resolution information.

    The reason we are using a string is due to LLMs failing to comply with complex schemas.
    """
    parts = []

    if resolution_method == "exact_id_match":
        parts.append("Resolution confidence: 1.000")

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
        parts.append(f"Resolution confidence: {similarity_score:.3f}")

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
    metadata_str = _create_metadata_string(
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

    # Filter results by MAX_VECTOR_SEARCH_L2_DISTANCE first
    filtered_results = [
        (doc, score_val)
        for doc, score_val in results
        if score_val <= MAX_VECTOR_SEARCH_L2_DISTANCE
    ]

    for doc, score_val in filtered_results:  # Use filtered_results
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
    metadata_str = _create_metadata_string(resolution_method="exact_id_match")

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
            metadata_str = _create_metadata_string(
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


@tool(parse_docstring=True)
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

        results = get_vector_store().similarity_search_with_score(
            query, top_k, filters if filters else None
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
            metadata_str = _create_metadata_string(
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

        results = get_vector_store().similarity_search_with_score(
            query, top_k * 2, where_clause if where_clause else None
        )

        # _convert_vector_results_to_products will handle the L2 distance filtering.
        # The raw results are passed, and it filters internally.

        # if not results: # This check is on raw results, not post-L2-filter results
        #     return ProductNotFound(
        #         message=f"No products found matching query: '{query}' with initial filters",
        #         query_product_name=query,
        #     )

        filtered_products_from_convert = _convert_vector_results_to_products(
            results, "filtered_search", search_query=query
        )

        # Now apply other filters (price, stock) to the L2-distance-filtered list
        further_filtered_products = []
        for product in filtered_products_from_convert:
            if min_price is not None and product.price < min_price:
                continue
            if max_price is not None and product.price > max_price:
                continue
            if min_stock is not None and product.stock < min_stock:
                continue
            further_filtered_products.append(product)
            if len(further_filtered_products) >= top_k:
                break

        if not further_filtered_products:
            return ProductNotFound(
                message=f"No products found matching all specified filters for query: '{query}' (after L2 distance filter max_dist={MAX_VECTOR_SEARCH_L2_DISTANCE})",
                query_product_name=query,
            )
        return further_filtered_products
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
        results = get_vector_store().similarity_search_with_score(
            search_query, limit * 2
        )

        # _convert_vector_results_to_products will handle the L2 distance filtering.

        # if not results: # Check on raw results
        #     return ProductNotFound(
        #         message=f"No products found for occasion: '{occasion}' via initial search",
        #         query_product_name=occasion,
        #     )

        converted_products = _convert_vector_results_to_products(
            results, "occasion_search", search_query=search_query
        )

        suitable_products = []
        for product in converted_products:
            if product.stock > 0:
                suitable_products.append(product)
                if len(suitable_products) >= limit:
                    break

        if not suitable_products:
            return ProductNotFound(
                message=f"No in-stock products found suitable for occasion: '{occasion}' (after L2 distance filter max_dist={MAX_VECTOR_SEARCH_L2_DISTANCE})",
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


@tool(parse_docstring=True)
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
            metadata_str = _create_metadata_string(
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
) -> list[tuple[Product, float]] | ProductNotFound:
    """Resolve a single ProductMention to top-K candidate products.

    Returns:
        A list of (Product, l2_distance) tuples ranked by relevance (lower L2 distance is better),
        or ProductNotFound if no candidates found.
    Raises:
        ValueError: If the product catalog cannot be loaded.
        Exception: For other unexpected errors.
    """
    try:
        candidates_with_scores: list[tuple[Product, float]] = []
        explicit_id_missed = False  # Initialize
        original_provided_id: str | None = None
        id_miss_message_prefix: str = ""  # Initialize

        if mention.product_id:
            original_provided_id = mention.product_id
            id_result: Product | ProductNotFound = await find_product_by_id.ainvoke(
                {"product_id": mention.product_id}
            )
            if isinstance(id_result, Product):
                # Exact match found
                metadata_str = _create_metadata_string(
                    resolution_method="exact_id_match",
                    requested_quantity=mention.quantity,
                )
                id_result.metadata = metadata_str
                logger.info(
                    f"[RESOLVE_PRODUCT_MENTION] Returning 1 candidate from EXACT ID MATCH for '{mention.product_id}'. Candidate: {id_result.product_id}"
                )
                return [(id_result, 0.0)]
            elif isinstance(id_result, ProductNotFound):
                logger.warning(
                    f"[RESOLVE_PRODUCT_MENTION] Explicit Product ID '{mention.product_id}' not found by exact match. Returning ProductNotFound as per strict ID policy."
                )
                # If an explicit ID was provided and not found, return ProductNotFound immediately.
                return id_result  # This is the ProductNotFound object from find_product_by_id

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

        logger.debug(
            f"Stockkeeper: constructed search_query: '{search_query}' with filters: {filters}"
        )

        # Perform vector search
        raw_results_with_scores: list[tuple[Any, float]] = (
            get_vector_store().similarity_search_with_score(search_query, top_k, filters if filters else None)
        )
        logger.debug(
            f"Stockkeeper: raw vector search results for '{search_query}': {raw_results_with_scores}"
        )

        temp_semantic_candidates: list[tuple[Product, float]] = []
        filtered_raw_results = [
            (doc, score_val)
            for doc, score_val in raw_results_with_scores
            if score_val <= MAX_VECTOR_SEARCH_L2_DISTANCE
        ]

        for doc, score_val in filtered_raw_results:
            try:
                product = metadata_to_product(doc.metadata)

                # Get standard search metadata from _add_search_metadata_to_product
                product = _add_search_metadata_to_product(
                    product,
                    score_val,
                    "semantic_search",
                    search_query,
                    mention.quantity,
                )

                # Augment with ID miss info if applicable
                if explicit_id_missed:  # Use the flag directly
                    if product.metadata:
                        product.metadata = f"{id_miss_message_prefix}{product.metadata}"
                    else:
                        product.metadata = (
                            id_miss_message_prefix.strip()
                        )  # Remove trailing space if it's the only metadata

                temp_semantic_candidates.append(
                    (product, score_val)
                )  # Store product and its L2 distance
            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        candidates_with_scores = temp_semantic_candidates

        # Fallback to fuzzy search if semantic search yields no results (after L2 filtering)
        if not candidates_with_scores:
            # Use mention.mention_text for fuzzy search if product_name is empty but mention_text exists
            fuzzy_search_term = mention.product_name or mention.mention_text
            if fuzzy_search_term:
                logger.info(
                    f"[RESOLVE_PRODUCT_MENTION] Semantic results empty (or all > L2_dist {MAX_VECTOR_SEARCH_L2_DISTANCE}), trying fuzzy for '{fuzzy_search_term}'."
                )
                fuzzy_results_list: (
                    list[FuzzyMatchResult] | ProductNotFound
                ) = await find_product_by_name.ainvoke(
                    {
                        "product_name": fuzzy_search_term,
                        "threshold": 0.40,  # Default was 0.6, consider if this is too low or fine for fallback
                        "top_n": top_k,
                    }
                )
                if isinstance(fuzzy_results_list, list) and fuzzy_results_list:
                    logger.info(
                        f"[RESOLVE_PRODUCT_MENTION] Fuzzy search found {len(fuzzy_results_list)} candidates for '{fuzzy_search_term}'."
                    )
                    temp_fuzzy_candidates_with_scores: list[tuple[Product, float]] = []
                    for fuzzy_match in fuzzy_results_list:
                        product_candidate = fuzzy_match.matched_product
                        l2_like_distance = 1.0 - fuzzy_match.similarity_score

                        # Create fuzzy match metadata string
                        fuzzy_metadata_str = _create_metadata_string(
                            resolution_method="fuzzy_name_match",
                            search_query=fuzzy_search_term,
                            similarity_score=fuzzy_match.similarity_score,
                            requested_quantity=mention.quantity,
                        )

                        # Augment with ID miss info if applicable
                        if explicit_id_missed:  # Use the flag directly
                            if fuzzy_metadata_str:
                                product_candidate.metadata = (
                                    f"{id_miss_message_prefix}{fuzzy_metadata_str}"
                                )
                            else:
                                product_candidate.metadata = (
                                    id_miss_message_prefix.strip()
                                )
                        else:
                            product_candidate.metadata = fuzzy_metadata_str

                        temp_fuzzy_candidates_with_scores.append(
                            (product_candidate, l2_like_distance)
                        )

                    if temp_fuzzy_candidates_with_scores:
                        # Sort fuzzy candidates by L2-like distance (ascending)
                        temp_fuzzy_candidates_with_scores.sort(key=lambda x: x[1])
                        candidates_with_scores = temp_fuzzy_candidates_with_scores
                        logger.info(
                            f"[RESOLVE_PRODUCT_MENTION] Path A2: Returning {len(candidates_with_scores)} candidates from FUZZY block for '{fuzzy_search_term}'. L2 distances: {[s for _, s in candidates_with_scores]}"
                        )
                        # Do not return here yet, let the final block handle it to ensure consistent logging/return point

            if not candidates_with_scores:  # If still no candidates after fuzzy attempt
                logger.info(
                    f"[RESOLVE_PRODUCT_MENTION] Path A3: Semantic results empty AND fuzzy attempt failed/not triggered for '{search_query}' / '{fuzzy_search_term}'. Returning ProductNotFound."
                )
                return ProductNotFound(
                    message=f"[RESOLVE_PRODUCT_MENTION] No products found matching vector search query: '{search_query}' or fuzzy: '{fuzzy_search_term}'",
                    query_product_name=mention.product_name or mention.mention_text,
                    query_product_id=mention.product_id,
                )

        if not candidates_with_scores:  # Final check if list is empty
            logger.info(
                f"[RESOLVE_PRODUCT_MENTION] Path C1: No candidates after all attempts (including L2 filter {MAX_VECTOR_SEARCH_L2_DISTANCE}) for query '{search_query}'. Returning ProductNotFound."
            )
            return ProductNotFound(
                message=f"[RESOLVE_PRODUCT_MENTION] No candidates found (L2 filter {MAX_VECTOR_SEARCH_L2_DISTANCE}) for query: '{search_query}' (and fuzzy fallback if applicable)",
                query_product_name=mention.product_name,
                query_product_id=mention.product_id,
            )

        # Results from vector search are already sorted by L2. Fuzzy results were sorted.
        logger.info(
            f"[RESOLVE_PRODUCT_MENTION] Returning {len(candidates_with_scores)} candidates at END of function for mention targeting '{search_query}'. L2 distances: {[s for _, s in candidates_with_scores]}"
        )
        return candidates_with_scores
    except ValueError:
        raise
    except Exception as e:
        logger.error(
            f"[RESOLVE_PRODUCT_MENTION] Unexpected error during product mention resolution for '{mention}': {e}",
            exc_info=True,
        )
        raise
