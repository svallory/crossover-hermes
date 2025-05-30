import logging
from typing import Any

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


class FuzzyMatchResult(BaseModel):
    """Result of a fuzzy name match."""

    matched_product: Product
    similarity_score: float = Field(description="Similarity score between 0.0 and 1.0")


def create_metadata_string(
    resolution_confidence: float | None = None,
    resolution_method: str | None = None,
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
        }.get(resolution_method, f"Resolution method: {resolution_method}")
        parts.append(method_desc)

    if requested_quantity is not None:
        parts.append(f"Requested quantity: {requested_quantity}")

    if search_query:
        parts.append(f"Search query: '{search_query}'")

    if similarity_score is not None:
        parts.append(f"Similarity score: {similarity_score:.3f}")

    return "; ".join(parts) if parts else None


@tool(parse_docstring=True)
def find_product_by_id(product_id: str) -> Product | ProductNotFound:
    """Find a product by its exact product ID.

    Args:
        product_id: The exact product ID to search for.

    Returns:
        The matching Product object, or ProductNotFound if no match exists.
    """
    try:
        products_df = load_products_df()
        if products_df is None:
            return ProductNotFound(
                message="Product catalog is not available",
                query_product_id=product_id,
            )

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

        # Process seasons with proper typing
        seasons_list: list[Season] = []
        seasons_str = str(product_row.get("seasons", None))
        if seasons_str:
            for s in seasons_str.split(","):
                s = s.strip()
                seasons_list.append(Season(s))

        # Create Product object with metadata
        metadata_str = create_metadata_string(
            resolution_confidence=1.0, resolution_method="exact_id_match"
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

    except Exception as e:
        logger.error(f"Error finding product by ID '{product_id}': {e}")
        return ProductNotFound(
            message=f"Error searching for product ID '{product_id}': {str(e)}",
            query_product_id=product_id,
        )


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
    """
    # Handle None values with defaults
    if threshold is None:
        threshold = 0.6
    if top_n is None:
        top_n = 5

    try:
        from rapidfuzz import fuzz

        products_df = load_products_df()
        if products_df is None:
            return ProductNotFound(
                message="Product catalog is not available",
                query_product_name=product_name,
            )

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
            # Process seasons with proper typing
            seasons_list: list[Season] = []
            seasons_str = str(product_row.get("seasons", None))
            if seasons_str:
                for s in seasons_str.split(","):
                    s = s.strip()
                    seasons_list.append(Season(s))

            # Create metadata string
            metadata_str = create_metadata_string(
                resolution_confidence=similarity_score,
                resolution_method="fuzzy_name_match",
                search_query=product_name,
                similarity_score=similarity_score,
            )

            product = Product(
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

            results.append(
                FuzzyMatchResult(
                    matched_product=product, similarity_score=similarity_score
                )
            )

        return results

    except Exception as e:
        logger.error(f"Error in fuzzy name search for '{product_name}': {e}")
        return ProductNotFound(
            message=f"Error searching for product name '{product_name}': {str(e)}",
            query_product_name=product_name,
        )


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
        List of matching Product objects or ProductNotFound if no matches
    """
    try:
        # Get vector store
        vector_store = get_vector_store()

        # Build metadata filters
        filters = {}
        if category_filter:
            filters["category"] = category_filter
        if season_filter:
            filters["season"] = season_filter

        # Perform similarity search
        if filters:
            results = vector_store.similarity_search_with_score(
                query=query, k=top_k, filter=filters
            )
        else:
            results = vector_store.similarity_search_with_score(query=query, k=top_k)

        if not results:
            return ProductNotFound(
                message=f"No products found matching description: '{query}'",
                query_product_name=query,
            )

        # Convert results to Product objects
        products = []
        for doc, score in results:
            try:
                product = metadata_to_product(doc.metadata)

                # Add search metadata
                confidence = max(0.0, min(1.0, 1.0 - (score / 2.0)))
                metadata_str = create_metadata_string(
                    resolution_confidence=confidence,
                    resolution_method="semantic_search",
                    search_query=query,
                    similarity_score=score,
                )
                product.metadata = metadata_str

                products.append(product)
            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        if not products:
            return ProductNotFound(
                message=f"Error processing search results for: '{query}'",
                query_product_name=query,
            )

        return products

    except Exception as e:
        logger.error(f"Error during product description search: {e}", exc_info=True)
        return ProductNotFound(
            message=f"Error searching products by description: {str(e)}",
            query_product_name=query,
        )


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
    """
    # Handle None value with default
    if limit is None:
        limit = 3

    try:
        products_df = load_products_df()
        if products_df is None:
            return ProductNotFound(
                message="Product catalog is not available",
                query_product_id=product_id,
            )

        # Find the original product
        original_product = products_df[
            products_df["product_id"].str.upper() == product_id.upper()
        ]

        if original_product.empty:
            return ProductNotFound(
                message=f"Original product '{product_id}' not found",
                query_product_id=product_id,
            )

        original_row = original_product.iloc[0]
        original_category = str(original_row["category"])

        # Define complementary relationships
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

        # Get complementary categories
        target_categories = complementary_categories.get(original_category, [])

        if not target_categories:
            return ProductNotFound(
                message=f"No complementary categories defined for '{original_category}'",
                query_product_id=product_id,
            )

        # Find products in complementary categories that are in stock
        complementary_products = products_df[
            (products_df["category"].isin(target_categories))
            & (products_df["stock"] > 0)
        ]

        if complementary_products.empty:
            return ProductNotFound(
                message=f"No in-stock complementary products found for '{product_id}'",
                query_product_id=product_id,
            )

        # Take a sample of products, prioritizing higher stock
        sampled_products = complementary_products.nlargest(limit, "stock")

        # Convert to Product objects
        result = []
        for _, row in sampled_products.iterrows():
            try:
                # Process seasons with proper typing
                seasons_list: list[Season] = []
                seasons_str = str(row.get("seasons", None))
                if seasons_str:
                    for s in seasons_str.split(","):
                        s = s.strip()
                        seasons_list.append(Season(s))

                # Create metadata string
                metadata_str = create_metadata_string(
                    resolution_confidence=0.8,  # Medium confidence for complementary matches
                    resolution_method="complementary_category_match",
                )

                product = Product(
                    product_id=str(row["product_id"]),
                    name=str(row["name"]),
                    description=str(row["description"]),
                    category=ProductCategory(str(row["category"])),
                    product_type=str(row.get("type", "")),
                    stock=int(row["stock"]),
                    price=float(row["price"]),
                    seasons=seasons_list,
                    metadata=metadata_str,
                )
                result.append(product)
            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        if not result:
            return ProductNotFound(
                message=f"Error processing complementary products for '{product_id}'",
                query_product_id=product_id,
            )

        return result

    except Exception as e:
        logger.error(f"Error finding complementary products: {e}", exc_info=True)
        return ProductNotFound(
            message=f"Error finding complementary products: {str(e)}",
            query_product_id=product_id,
        )


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
    """
    # Handle None values with defaults
    if top_k is None:
        top_k = 5

    try:
        # Get vector store
        vector_store = get_vector_store()

        # Build metadata filters for ChromaDB
        where_clause: dict[str, Any] = {}

        if category:
            where_clause["category"] = category

        if season:
            where_clause["season"] = season

        # Note: ChromaDB metadata filters work best with exact matches
        # Price and stock filtering will be done post-search

        # Perform similarity search with metadata filtering
        if where_clause:
            results = vector_store.similarity_search_with_score(
                query=query,
                k=top_k * 2,
                filter=where_clause,  # Get more to filter
            )
        else:
            results = vector_store.similarity_search_with_score(
                query=query, k=top_k * 2
            )

        if not results:
            return ProductNotFound(
                message=f"No products found matching query: '{query}'",
                query_product_name=query,
            )

        # Convert to Product objects and apply additional filters
        filtered_products = []
        for doc, score in results:
            try:
                product = metadata_to_product(doc.metadata)

                # Apply price filters
                if min_price is not None and product.price < min_price:
                    continue
                if max_price is not None and product.price > max_price:
                    continue

                # Apply stock filter
                if min_stock is not None and product.stock < min_stock:
                    continue

                # Add search metadata
                confidence = max(0.0, min(1.0, 1.0 - (score / 2.0)))
                metadata_str = create_metadata_string(
                    resolution_confidence=confidence,
                    resolution_method="filtered_search",
                    search_query=query,
                    similarity_score=score,
                )
                product.metadata = metadata_str

                filtered_products.append(product)

                # Stop when we have enough results
                if len(filtered_products) >= top_k:
                    break

            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        if not filtered_products:
            return ProductNotFound(
                message=f"No products found matching all specified filters for query: '{query}'",
                query_product_name=query,
            )

        return filtered_products

    except Exception as e:
        logger.error(f"Error during filtered search: {e}", exc_info=True)
        return ProductNotFound(
            message=f"Error during filtered product search: {str(e)}",
            query_product_name=query,
        )


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
    """
    # Handle None value with default
    if limit is None:
        limit = 5

    try:
        # Get vector store
        vector_store = get_vector_store()

        # Create a search query that includes occasion-related terms
        search_query = f"{occasion} outfit clothing attire"

        # Perform similarity search
        results = vector_store.similarity_search_with_score(
            query=search_query,
            k=limit * 2,  # Get more results to filter
        )

        if not results:
            return ProductNotFound(
                message=f"No products found for occasion: '{occasion}'",
                query_product_name=occasion,
            )

        # Convert to Product objects and filter for in-stock items
        suitable_products = []
        for doc, score in results:
            try:
                product = metadata_to_product(doc.metadata)

                # Only include products that are in stock
                if product.stock > 0:
                    # Add search metadata
                    confidence = max(0.0, min(1.0, 1.0 - (score / 2.0)))
                    metadata_str = create_metadata_string(
                        resolution_confidence=confidence,
                        resolution_method="occasion_search",
                        search_query=search_query,
                        similarity_score=score,
                    )
                    product.metadata = metadata_str

                    suitable_products.append(product)

                    # Stop when we have enough results
                    if len(suitable_products) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        if not suitable_products:
            return ProductNotFound(
                message=f"No in-stock products found suitable for occasion: '{occasion}'",
                query_product_name=occasion,
            )

        return suitable_products

    except Exception as e:
        logger.error(f"Error finding products for occasion: {e}", exc_info=True)
        return ProductNotFound(
            message=f"Error finding products for occasion: {str(e)}",
            query_product_name=occasion,
        )


def find_alternatives(
    original_product_id: str, limit: int = 2
) -> list[AlternativeProduct] | ProductNotFound:
    """Find alternative products similar to the specified product.

    Args:
        original_product_id: The product ID to find alternatives for
        limit: Maximum number of alternatives to return

    Returns:
        List of AlternativeProduct objects or ProductNotFound if none found
    """
    try:
        products_df = load_products_df()
        if products_df is None:
            return ProductNotFound(
                message="Product catalog is not available",
                query_product_id=original_product_id,
            )

        # Find the original product
        original_product = products_df[
            products_df["product_id"].str.upper() == original_product_id.upper()
        ]

        if original_product.empty:
            return ProductNotFound(
                message=f"Original product '{original_product_id}' not found",
                query_product_id=original_product_id,
            )

        original_row = original_product.iloc[0]
        original_category = str(original_row["category"])

        # Find products in the same category, excluding the original product
        category_products = products_df[
            (products_df["category"] == original_category)
            & (products_df["product_id"].str.upper() != original_product_id.upper())
            & (products_df["stock"] > 0)
        ]

        if category_products.empty:
            return ProductNotFound(
                message=f"No in-stock alternatives found for product '{original_product_id}'.",
                query_product_id=original_product_id,
            )

        # Calculate price similarity
        original_price = float(original_row["price"])

        # Add price similarity as a column using .copy() to avoid warning
        category_products = category_products.copy()
        category_products.loc[:, "price_similarity"] = category_products["price"].apply(
            lambda x: 1.0
            - abs(float(x) - original_price) / max(original_price, float(x))
        )

        # Sort by price similarity, descending
        sorted_products = category_products.sort_values(
            "price_similarity", ascending=False
        )

        # Take top alternatives
        top_alternatives = sorted_products.head(limit)

        # Convert to AlternativeProduct objects
        result = []
        for _, row in top_alternatives.iterrows():
            # Process seasons with proper typing
            seasons_list: list[Season] = []
            seasons_str = str(row.get("seasons", None))
            if seasons_str:
                for s in seasons_str.split(","):
                    s = s.strip()
                    seasons_list.append(Season(s))

            # Create metadata string
            similarity_score = float(row["price_similarity"])
            metadata_str = create_metadata_string(
                resolution_confidence=similarity_score,
                resolution_method="price_similarity_match",
            )

            product = Product(
                product_id=str(row["product_id"]),
                name=str(row["name"]),
                description=str(row["description"]),
                category=ProductCategory(str(row["category"])),
                product_type=str(row.get("type", "")),
                stock=int(row["stock"]),
                price=float(row["price"]),
                seasons=seasons_list,
                metadata=metadata_str,
            )

            # Generate a reason based on price and availability
            if similarity_score > 0.9:
                reason = f"Very similar price (${float(row['price']):.2f} vs ${original_price:.2f}) and currently in stock"
            elif similarity_score > 0.7:
                reason = f"Similar price range and currently in stock ({int(row['stock'])} available)"
            else:
                reason = f"Same category alternative that's currently available ({int(row['stock'])} in stock)"

            # Create and add the AlternativeProduct
            alternative = AlternativeProduct(
                product=product, similarity_score=similarity_score, reason=reason
            )
            result.append(alternative)

        return result

    except Exception as e:
        logger.error(f"Error finding alternatives for '{original_product_id}': {e}")
        return ProductNotFound(
            message=f"Error finding alternatives: {str(e)}",
            query_product_id=original_product_id,
        )


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
        A list of candidate Product objects ranked by relevance, or ProductNotFound if no candidates found
    """
    try:
        candidates = []

        # 1. Try exact product ID match first (highest priority)
        if mention.product_id:
            id_result: Product | ProductNotFound = await find_product_by_id.ainvoke(
                {"product_id": mention.product_id}
            )
            if isinstance(id_result, Product):
                # Add resolution metadata
                metadata_str = create_metadata_string(
                    resolution_confidence=1.0,
                    resolution_method="exact_id_match",
                    requested_quantity=mention.quantity,
                )
                id_result.metadata = metadata_str

                # For exact ID matches, return immediately with just this result
                return [id_result]

        # 2. Build a search query from available information
        search_parts = []
        if mention.product_name:
            search_parts.append(mention.product_name)
        if mention.product_description:
            search_parts.append(mention.product_description)
        if mention.product_type:
            search_parts.append(mention.product_type)

        if not search_parts:
            return ProductNotFound(
                message=f"No searchable information in mention: {mention}",
                query_product_name=mention.product_name,
                query_product_id=mention.product_id,
            )

        search_query = " ".join(search_parts)

        # 3. Build metadata filters for ChromaDB
        filters = {}
        if mention.product_category:
            filters["category"] = str(mention.product_category.value)

        # 4. Use ChromaDB's similarity search with metadata filtering
        try:
            # Get vector store
            vector_store = get_vector_store()

            # Perform similarity search with metadata filtering
            if filters:
                results = vector_store.similarity_search_with_score(
                    query=search_query,
                    k=top_k,  # Get top-K candidates for LLM disambiguation
                    filter=filters,
                )
            else:
                results = vector_store.similarity_search_with_score(
                    query=search_query, k=top_k
                )

            if not results:
                return ProductNotFound(
                    message=f"No products found matching search query: '{search_query}'",
                    query_product_name=mention.product_name,
                    query_product_id=mention.product_id,
                )

            # 5. Process all results and return as candidates
            for doc, score in results:
                # ChromaDB similarity_search_with_score returns distance scores (lower = more similar)
                # Convert distance to similarity/confidence
                confidence = max(0.0, min(1.0, 1.0 - (score / 2.0)))

                # Only include candidates above minimum threshold
                if confidence >= SIMILAR_MATCH_THRESHOLD:
                    try:
                        product = metadata_to_product(doc.metadata)

                        # Add resolution metadata
                        metadata_str = create_metadata_string(
                            resolution_confidence=confidence,
                            resolution_method="semantic_search",
                            requested_quantity=mention.quantity,
                            search_query=search_query,
                            similarity_score=score,
                        )
                        product.metadata = metadata_str

                        candidates.append(product)
                    except Exception as e:
                        logger.error(f"Error converting document to product: {e}")
                        continue

            if not candidates:
                return ProductNotFound(
                    message=f"No candidates above threshold {SIMILAR_MATCH_THRESHOLD} for query: '{search_query}'",
                    query_product_name=mention.product_name,
                    query_product_id=mention.product_id,
                )

            return candidates

        except Exception as e:
            logger.error(f"Error during vector search: {e}", exc_info=True)
            return ProductNotFound(
                message=f"Error during vector search: {str(e)}",
                query_product_name=mention.product_name,
                query_product_id=mention.product_id,
            )

    except Exception as e:
        logger.error(f"Error during product mention resolution: {e}", exc_info=True)
        return ProductNotFound(
            message=f"Error during product mention resolution: {str(e)}",
            query_product_name=mention.product_name,
            query_product_id=mention.product_id,
        )
