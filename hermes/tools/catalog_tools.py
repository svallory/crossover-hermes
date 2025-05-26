import logging
from typing import Any

from langchain_core.tools import tool
import pandas as pd  # type: ignore

# Import tool from langchain_core
from pydantic import BaseModel, Field

# For fuzzy matching
from thefuzz import process  # type: ignore

# Import the load_products_df function
from hermes.data.load_data import load_products_df

# LangChain Chroma integration

# Explicitly ignore import not found errors
from hermes.model import ProductCategory, Season
from hermes.model.product import AlternativeProduct, Product, Season
from hermes.model.errors import ProductNotFound
from hermes.agents.classifier.models import ProductMention

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


def find_product_by_id(product_id: str) -> Product | ProductNotFound:
    """Find a product by its ID.

    Retrieve detailed product information by its exact Product ID.
    Use this when you have a precise Product ID (e.g., 'LTH0976', 'CSH1098').
    Also handles typos and formatting issues in product IDs.

    Args:
        product_id: The product ID to search for.

    Returns:
        A Product object if found, or a ProductNotFound object if no product matches the ID.

    """
    # Standardize the product ID format (remove spaces and convert to uppercase)
    product_id = product_id.replace(" ", "").upper()
    # Remove common formatting characters
    product_id = (
        product_id.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
    )

    # Get products_df using the memoized function
    products_df = load_products_df()

    # Ensure products_df is not None before trying to index it
    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_id=product_id,
        )

    # First try exact match
    product_data = products_df[products_df["product_id"] == product_id]

    # If no exact match, try fuzzy matching on product IDs
    if product_data.empty:
        all_product_ids = products_df["product_id"].tolist()

        # Use fuzzy matching to find similar product IDs
        matches = process.extractBests(
            query=product_id,
            choices=all_product_ids,
            score_cutoff=70,  # Lower threshold for product IDs
            limit=1,
        )

        if matches:
            matched_id = matches[0][0]
            similarity_score = matches[0][1]

            # If we found a close match, use it
            if similarity_score >= 70:
                product_data = products_df[products_df["product_id"] == matched_id]
                if not product_data.empty:
                    logger.info(
                        f"Fuzzy matched product ID '{product_id}' to '{matched_id}' (score: {similarity_score})"
                    )

    if product_data.empty:
        return ProductNotFound(
            message=f"Product with ID '{product_id}' not found in catalog.",
            query_product_id=product_id,
        )

    # Map DataFrame columns to our Product model fields
    product_row = product_data.iloc[0]

    # Handle potential missing columns
    product_dict: dict[str, Any] = {
        "product_id": str(product_row["product_id"]),
        "name": str(product_row["name"]),
        "category": ProductCategory(product_row["category"]),
        "stock": int(product_row["stock"]),
        "description": str(product_row["description"]),
        "product_type": str(
            product_row.get("type", "")
        ),  # Ensure type is included, default to empty string if missing
        "price": float(product_row["price"]) if pd.notna(product_row["price"]) else 0.0,
        "seasons": [],
        "metadata": None,
    }

    # Process seasons correctly to handle 'Fall' vs 'Autumn'
    seasons_str = str(product_row.get("seasons", "Spring"))
    if seasons_str:
        for s in seasons_str.split(","):
            s = s.strip()
            if s:
                # Map 'Fall' to 'Autumn' if needed
                if s == "Fall":
                    product_dict["seasons"].append(Season.AUTUMN)
                else:
                    try:
                        product_dict["seasons"].append(Season(s))
                    except ValueError:
                        # If not a valid season, use a default
                        product_dict["seasons"].append(Season.SPRING)

    # If no seasons were added, default to Spring
    if not product_dict["seasons"]:
        product_dict["seasons"] = [Season.SPRING]

    try:
        return Product(**product_dict)
    except Exception as e:
        return ProductNotFound(message=f"Error during product retrieval: {str(e)}")


def find_product_by_name(
    *, product_name: str, threshold: float = 0.6, top_n: int = 5
) -> list[FuzzyMatchResult] | ProductNotFound:
    """Find products by name using fuzzy matching.

    Use this when the customer provides a product name that might have typos, be incomplete,
    or slightly different from the catalog.

    Args:
        product_name: The product name to search for.
        threshold: Minimum similarity score (0.0 to 1.0) for a match to be considered. Defaults to 0.6.
        top_n: Maximum number of top matching products to return. Defaults to 5.

    Returns:
        A list of FuzzyMatchResult objects for products matching the name above the threshold, sorted by similarity,
        or a ProductNotFound object if no sufficiently similar products are found.

    """
    # Make sure the input is a string
    product_name = str(product_name).strip()

    # Get products_df using the memoized function
    products_df = load_products_df()

    # Check if product catalog is available
    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_name=product_name,
        )

    # All product names from the catalog
    # Assuming column name is 'name' based on the assignment spreadsheet
    all_product_names = products_df["name"].tolist()

    # Find the best matches using fuzzy string matching
    # Returns list of tuples: (matched_name, score)
    matches = process.extractBests(
        query=product_name,
        choices=all_product_names,
        score_cutoff=int(threshold * 100),  # thefuzz uses 0-100 scale
        limit=top_n,
    )

    if not matches:
        return ProductNotFound(
            message=f"No products found similar to '{product_name}' with threshold {threshold}.",
            query_product_name=product_name,
        )

    results = []
    for matched_name, score in matches:
        # Get full product data for this match
        product_data = products_df[products_df["name"] == matched_name]
        if not product_data.empty:
            product_row = product_data.iloc[0]

            # Build product dict with all required fields
            product_dict = {
                "product_id": str(product_row["product_id"]),
                "name": str(product_row["name"]),
                "category": ProductCategory(str(product_row["category"])),
                "stock": int(product_row["stock"]),
                "description": str(product_row["description"]),
                "product_type": str(product_row.get("type", "")),
                "seasons": [],
                "price": float(product_row["price"])
                if pd.notna(product_row["price"])
                else 0.0,
                "metadata": None,
            }

            # Process seasons correctly to handle 'Fall' vs 'Autumn'
            seasons_str = str(product_row.get("season", "Spring"))
            if seasons_str:
                for s in seasons_str.split(","):
                    s = s.strip()
                    if s:
                        # Map 'Fall' to 'Autumn' if needed
                        if s == "Fall":
                            product_dict["seasons"].append(Season.AUTUMN)
                        else:
                            try:
                                product_dict["seasons"].append(Season(s))
                            except ValueError:
                                # If not a valid season, use a default
                                product_dict["seasons"].append(Season.SPRING)

            # If no seasons were added, default to Spring
            if not product_dict["seasons"]:
                product_dict["seasons"] = [Season.SPRING]

            product = Product(**product_dict)  # type: ignore[arg-type]
            results.append(
                FuzzyMatchResult(
                    matched_product=product,
                    similarity_score=score / 100,  # Convert score back to 0-1 scale
                )
            )

    # Return results sorted by similarity score (highest first)
    return sorted(results, key=lambda x: x.similarity_score, reverse=True)


def search_products_by_description(
    query: str,
    top_k: int = 3,
    category_filter: str | None = None,
    season_filter: str | None = None,
) -> list[Product] | ProductNotFound:
    """Search for products by description.

    Search for products using semantic description matching.
    This tool is great for answering open-ended inquiries about products with specific features or characteristics.

    Args:
        query: The search query to find products.
        top_k: Maximum number of products to return (default: 3).
        category_filter: Optional category filter.
        season_filter: Optional season filter.

    Returns:
        A list of matching Product objects or a ProductNotFound object if no products match.

    """
    if not query:
        return ProductNotFound(message="Query cannot be empty.")

    try:
        # Get vector store
        vector_store = get_vector_store()

        # Prepare filters
        where_clause = {}
        if category_filter:
            where_clause["category"] = category_filter
        if season_filter:
            where_clause["season"] = {"$contains": season_filter}

        # Perform similarity search
        if where_clause:
            results = vector_store.similarity_search(
                query=query, k=top_k, filter=where_clause
            )
        else:
            results = vector_store.similarity_search(query=query, k=top_k)

        if not results:
            return ProductNotFound(
                message=(
                    f"No products found matching description query: '{query}' "
                    f"with category '{category_filter}' and season '{season_filter}'."
                )
            )

        # Convert results to Product objects
        products = []
        for doc in results:
            try:
                product = metadata_to_product(doc.metadata)
                products.append(product)
            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        return (
            products
            if products
            else ProductNotFound(
                message=f"Error converting search results to products for query: '{query}'"
            )
        )

    except Exception as e:
        logger.error(f"Error during product description search: {e}", exc_info=True)
        return ProductNotFound(message=f"Error during product search: {str(e)}")


@tool(parse_docstring=True)
def find_complementary_products(
    product_id: str, limit: int = 2
) -> list[Product] | ProductNotFound:
    """Find products that complement a given product for LLM-driven recommendations.

    Use this when the LLM determines that suggesting complementary items would enhance
    the customer experience, such as for occasions, gifts, or complete outfits.

    Args:
        product_id: The product ID to find complementary products for.
        limit: Maximum number of complementary products to return (default: 2).

    Returns:
        A list of complementary Product objects, or ProductNotFound if none found.

    """
    try:
        # First verify that the main product exists
        main_product_result = find_product_by_id(product_id)
        if isinstance(main_product_result, ProductNotFound):
            return main_product_result

        main_product = main_product_result
        assert isinstance(main_product, Product)

        # Get vector store
        vector_store = get_vector_store()

        # Search for complementary products based on the main product's characteristics
        search_query = (
            f"products that go well with {main_product.name} {main_product.description}"
        )

        # Search within the same category first, then expand if needed
        results = vector_store.similarity_search(
            query=search_query,
            k=limit + 1,  # Get one extra to exclude the main product
            filter={"category": str(main_product.category)},
        )

        # Convert to products and exclude the main product
        products = []
        for doc in results:
            if doc.metadata["product_id"] != product_id:
                try:
                    product = metadata_to_product(doc.metadata)
                    products.append(product)
                    if len(products) >= limit:
                        break
                except Exception as e:
                    logger.error(f"Error converting document to product: {e}")
                    continue

        # If we don't have enough results from the same category, search across categories
        if len(products) < limit:
            broader_results = vector_store.similarity_search(
                query=search_query,
                k=(limit - len(products)) + 1,
            )

            for doc in broader_results:
                if doc.metadata["product_id"] != product_id and len(products) < limit:
                    # Avoid duplicates
                    if not any(
                        p.product_id == doc.metadata["product_id"] for p in products
                    ):
                        try:
                            product = metadata_to_product(doc.metadata)
                            products.append(product)
                        except Exception as e:
                            logger.error(f"Error converting document to product: {e}")
                            continue

        return (
            products
            if products
            else ProductNotFound(
                message=f"No complementary products found for product '{product_id}'."
            )
        )

    except Exception as e:
        logger.error(f"Error finding complementary products: {e}", exc_info=True)
        return ProductNotFound(
            message=f"Error finding complementary products: {str(e)}",
            query_product_id=product_id,
        )


@tool(parse_docstring=True)
def search_products_with_filters(
    query: str,
    category: str | None = None,
    season: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_stock: int | None = None,
    top_k: int = 3,
) -> list[Product] | ProductNotFound:
    """Search products with advanced filtering for complex customer requirements.

    Use this when the LLM determines that the customer has specific filtering needs
    that go beyond basic description search, such as price ranges, availability, etc.

    Args:
        query: The search query text.
        category: Filter by product category (optional).
        season: Filter by season (optional).
        min_price: Minimum price filter (optional).
        max_price: Maximum price filter (optional).
        min_stock: Minimum stock level filter (optional).
        top_k: Number of results to return (default: 3).

    Returns:
        A list of matching Product objects or ProductNotFound if no products match.

    """
    if not query:
        return ProductNotFound(message="Search query cannot be empty.")

    try:
        # Get vector store
        vector_store = get_vector_store()

        # Prepare filters for vector store
        where_clause = {}
        if category:
            where_clause["category"] = category
        if season:
            where_clause["season"] = {"$contains": season}

        # Perform semantic search
        docs = vector_store.similarity_search(
            query=query,
            k=top_k * 2,  # Get more than needed for post-filtering
            filter=where_clause if where_clause else None,
        )

        # Convert to Product objects and apply additional filters
        filtered_results = []
        for doc in docs:
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

                filtered_results.append(product)

                # Stop once we have enough results
                if len(filtered_results) >= top_k:
                    break

            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        if not filtered_results:
            return ProductNotFound(
                message=(
                    f"No products found matching query '{query}' with the specified filters. "
                    f"Try broadening your search criteria."
                )
            )

        return filtered_results

    except Exception as e:
        logger.error(f"Error during filtered search: {e}", exc_info=True)
        return ProductNotFound(message=f"Error during filtered search: {str(e)}")


@tool(parse_docstring=True)
def find_products_for_occasion(
    occasion: str, limit: int = 3
) -> list[Product] | ProductNotFound:
    """Find products suitable for a specific occasion or context.

    Use this when the LLM identifies that the customer is shopping for a specific
    occasion, event, or context that would benefit from curated product suggestions.

    Args:
        occasion: The occasion or context (e.g., "wedding", "winter hiking", "office wear").
        limit: Maximum number of products to return (default: 3).

    Returns:
        A list of occasion-appropriate Product objects, or ProductNotFound if none found.

    """
    if not occasion:
        return ProductNotFound(message="Occasion cannot be empty.")

    try:
        # Get vector store
        vector_store = get_vector_store()

        # Create a search query optimized for occasion-based discovery
        search_query = f"products suitable for {occasion} occasion event"

        # Perform semantic search
        results = vector_store.similarity_search(
            query=search_query,
            k=limit,
        )

        if not results:
            return ProductNotFound(
                message=f"No products found suitable for occasion: '{occasion}'."
            )

        # Convert results to Product objects
        products = []
        for doc in results:
            try:
                product = metadata_to_product(doc.metadata)
                products.append(product)
            except Exception as e:
                logger.error(f"Error converting document to product: {e}")
                continue

        return (
            products
            if products
            else ProductNotFound(
                message=f"Error converting search results for occasion: '{occasion}'"
            )
        )

    except Exception as e:
        logger.error(f"Error finding products for occasion: {e}", exc_info=True)
        return ProductNotFound(message=f"Error finding products for occasion: {str(e)}")


def find_alternatives(
    original_product_id: str, limit: int = 2
) -> list[AlternativeProduct] | ProductNotFound:
    """Find and suggest in-stock alternative products if a requested item is out of stock.
    This helps provide customers with options when their desired item isn't available.

    Args:
        original_product_id: The product ID that is out of stock.
        limit: Maximum number of alternatives to return (default: 2).

    Returns:
        A list of AlternativeProduct objects with suggested alternatives,
        or ProductNotFound if the original product ID is invalid.

    """
    # First, check if the original product exists
    products_df = load_products_df()
    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_id=original_product_id,
        )
    original_product_data = products_df[
        products_df["product_id"] == original_product_id
    ]
    if original_product_data.empty:
        return ProductNotFound(
            message=f"Original product with ID '{original_product_id}' not found in catalog.",
            query_product_id=original_product_id,
        )

    # Get details of the original product
    original_product = original_product_data.iloc[0]
    # Get the category for filtering
    original_category = original_product["category"]

    # Get all products in the same category
    category_products = products_df[products_df["category"] == original_category]

    # Filter out the original product and items that are out of stock
    filtered_products = category_products[
        (category_products["product_id"] != original_product_id)
        & (category_products["stock"] > 0)
    ]

    if filtered_products.empty:
        return ProductNotFound(
            message=f"No in-stock alternatives found for product '{original_product_id}'.",
            query_product_id=original_product_id,
        )

    # Calculate price similarity
    original_price = float(original_product["price"])

    # Add price similarity as a column using .copy() to avoid warning
    filtered_products = filtered_products.copy()
    filtered_products.loc[:, "price_similarity"] = filtered_products["price"].apply(
        lambda x: 1.0 - abs(float(x) - original_price) / max(original_price, float(x))
    )

    # Sort by price similarity, descending
    sorted_products = filtered_products.sort_values("price_similarity", ascending=False)

    # Take top alternatives
    top_alternatives = sorted_products.head(limit)

    # Convert to AlternativeProduct objects
    result = []
    for _, row in top_alternatives.iterrows():
        # Create the product object
        product_dict = {
            "product_id": str(row["product_id"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "category": str(row["category"]),
            "product_type": str(row.get("type", "")),
            "stock": int(row["stock"]),
            "price": float(row["price"]),
            "seasons": [],
        }

        # Process seasons correctly to handle 'Fall' vs 'Autumn'
        seasons_str = str(row.get("season", ""))
        if seasons_str:
            for s in seasons_str.split(","):
                s = s.strip()
                if s:
                    # Map 'Fall' to 'Autumn' if needed
                    if s == "Fall":
                        product_dict["seasons"].append(Season.AUTUMN)
                    else:
                        try:
                            product_dict["seasons"].append(Season(s))
                        except ValueError:
                            # If not a valid season, use a default
                            product_dict["seasons"].append(Season.SPRING)

        # If no seasons were added, default to Spring
        if not product_dict["seasons"]:
            product_dict["seasons"] = [Season.SPRING]

        product = Product(**product_dict)

        # Calculate similarity score (normalized between 0-1)
        similarity_score = float(row["price_similarity"])

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
            id_result = find_product_by_id(product_id=mention.product_id)
            if isinstance(id_result, Product):
                # Add resolution metadata
                if not id_result.metadata:
                    id_result.metadata = {}
                id_result.metadata["resolution_confidence"] = 1.0
                id_result.metadata["resolution_method"] = "exact_id_match"
                id_result.metadata["requested_quantity"] = mention.quantity

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
                        if not product.metadata:
                            product.metadata = {}
                        product.metadata["resolution_confidence"] = confidence
                        product.metadata["resolution_method"] = "semantic_search"
                        product.metadata["requested_quantity"] = mention.quantity
                        product.metadata["search_query"] = search_query
                        product.metadata["similarity_score"] = score

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
