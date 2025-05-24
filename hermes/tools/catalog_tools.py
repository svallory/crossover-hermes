"""Product Catalog Tools.

This module provides tools for interacting with the product catalog.
These tools enable agents to retrieve product information based on various criteria,
supporting tasks like answering product inquiries, resolving product references in orders,
and suggesting alternatives.

Key functionalities include:
- Looking up products by their unique ID.
- Searching for products by name, with fuzzy matching capabilities.
- Performing semantic searches on product descriptions to find items based on
  more abstract queries (core to the RAG pattern for inquiries).
- Identifying related or complementary products.
- Filtering products by category, season, and other attributes.
"""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Dict
import json

import pandas as pd  # type: ignore

# Import tool from langchain_core
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# For fuzzy matching
from thefuzz import process  # type: ignore

# Import the load_products_df function
from hermes.data.load_data import load_products_df

# Import VectorStore
from hermes.data.vector_store import VectorStore

# Import our new vector store models
from hermes.model.vector import (
    ProductSearchQuery,
    ProductSearchResult,
    SimilarProductQuery,
)

# Explicitly ignore import not found errors
from hermes.model import ProductCategory, Season
from hermes.model.product import Product
from hermes.model.errors import ProductNotFound

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a variable to store vector_store collection
vs_collection = None


class FuzzyMatchResult(BaseModel):
    """Result of a fuzzy name match."""

    matched_product: Product
    similarity_score: float = Field(description="Similarity score between 0.0 and 1.0")


@tool  # type: ignore[call-overload]
def find_product_by_id(tool_input: str) -> Product | ProductNotFound:
    """Find a product by its ID.

    Retrieve detailed product information by its exact Product ID.
    Use this when you have a precise Product ID (e.g., 'LTH0976', 'CSH1098').

    Args:
        tool_input: JSON string with product_id field.

    Returns:
        A Product object if found, or a ProductNotFound object if no product matches the ID.

    """
    try:
        input_data = json.loads(tool_input)
        product_id = input_data.get("product_id", "")
    except (json.JSONDecodeError, AttributeError):
        return ProductNotFound(message=f"Invalid input format: {tool_input}")

    # Standardize the product ID format (remove spaces and convert to uppercase)
    product_id = product_id.replace(" ", "").upper()

    # Get products_df using the memoized function
    products_df = load_products_df()

    # Ensure products_df is not None before trying to index it
    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_id=product_id,
        )

    # Search for the product in the DataFrame
    product_data = products_df[products_df["product_id"] == product_id]

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
        "product_type": str(product_row.get("type", "")),  # Ensure type is included, default to empty string if missing
        "price": float(product_row["price"]) if pd.notna(product_row["price"]) else 0.0,
        "seasons": [],
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

    try:
        return Product(**product_dict)
    except Exception as e:
        return ProductNotFound(message=f"Error during product retrieval: {str(e)}")


@tool  # type: ignore[call-overload]
def find_product_by_name(
    product_name: str, *, threshold: float = 0.8, top_n: int = 3
) -> list[FuzzyMatchResult] | ProductNotFound:
    """Find products by name using fuzzy matching.

    Use this when the customer provides a product name that might have typos, be incomplete,
    or slightly different from the catalog.

    Args:
        product_name: The product name to search for.
        threshold: Minimum similarity score (0.0 to 1.0) for a match to be considered. Defaults to 0.8.
        top_n: Maximum number of top matching products to return. Defaults to 3.

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
                "price": float(product_row["price"]) if pd.notna(product_row["price"]) else 0.0,
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


def create_filter_dict(
    category: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Helper function to create a filter dictionary for vector store searches."""
    filters: dict[str, Any] = {}
    if category:
        filters["category"] = category
    if season:
        filters["season"] = season
    return filters


@tool  # type: ignore[call-overload]
def search_products_by_description(tool_input: str) -> list[Product] | ProductNotFound:
    """Search for products by description.

    Search for products using semantic description matching.
    This tool is great for answering open-ended inquiries about products with specific features or characteristics.

    Args:
        tool_input: JSON string with query, top_k (optional), category_filter (optional),
                   and season_filter (optional) fields.

    Returns:
        A list of matching Product objects or a ProductNotFound object if no products match.

    """
    try:
        input_data = json.loads(tool_input)
        query = input_data.get("query", "")
        top_k = input_data.get("top_k", 3)
        category_filter = input_data.get("category_filter")
        season_filter = input_data.get("season_filter")
    except (json.JSONDecodeError, AttributeError):
        return ProductNotFound(message=f"Invalid input format: {tool_input}")

    try:
        # Get products_df using the memoized function
        products_df = load_products_df()

        # First check if we have a DataFrame for direct searching
        if products_df is not None and not products_df.empty:
            # Initialize VectorStore (it's a singleton, so config is optional if already initialized)
            vector_store = VectorStore()

            # Prepare filters
            filter_criteria = {}
            if category_filter:
                filter_criteria["category"] = category_filter
            if season_filter:
                filter_criteria["season"] = season_filter

            # Create a ProductSearchQuery
            search_query = ProductSearchQuery(
                query_text=query,
                n_results=top_k,
                filter_criteria=filter_criteria if filter_criteria else None
            )

            # Use the updated method with our new query model
            products = vector_store.search_products_by_description(search_query)

            if not products:
                return ProductNotFound(
                    message=(
                        f"No products found matching description query: '{query}' "
                        f"with category '{category_filter}' and season '{season_filter}'."
                    )
                )
            return products
        else:
            return ProductNotFound(message="Product catalog data is not loaded.")

    except Exception as e:
        logger.error(f"Error during product description search: {e}", exc_info=True)
        return ProductNotFound(message=f"Error during product search: {str(e)}")


@tool  # type: ignore[call-overload]
def find_related_products(tool_input: str) -> list[Product] | ProductNotFound:
    """Find products related to a given product ID.

    Find products related to a given product ID, such as complementary items or alternatives from the same category.

    Args:
        tool_input: JSON string with product_id, relationship_type (optional), and limit (optional) fields.

    Returns:
        Union[List[Product], ProductNotFound]: List of related Product objects, or ProductNotFound if none found.

    """
    try:
        input_data = json.loads(tool_input)
        product_id = input_data.get("product_id", "")
        relationship_type = input_data.get("relationship_type", "complementary")
        limit = input_data.get("limit", 2)
    except (json.JSONDecodeError, AttributeError):
        return ProductNotFound(message=f"Invalid input format: {tool_input}")

    # Get products_df using the memoized function
    products_df = load_products_df()

    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_id=product_id,
        )
    try:
        # First verify that the main product exists
        main_product_result = find_product_by_id(
            json.dumps({"product_id": product_id})
        )
        if isinstance(main_product_result, ProductNotFound):
            return main_product_result

        # Ensure main_product is a Product object
        if not isinstance(main_product_result, Product):
            return ProductNotFound(
                message=f"Product with ID '{product_id}' has invalid type.",
                query_product_id=product_id,
            )

        main_product = main_product_result

        # Use the VectorStore for finding similar products
        if relationship_type == "similar":
            try:
                vector_store = VectorStore()

                # Create query for similar products
                similar_query = SimilarProductQuery(
                    product_id=product_id,
                    n_results=limit,
                    exclude_reference=True,
                    filter_criteria={"category": str(main_product.category)} if relationship_type == "similar" else None
                )

                # Find similar products
                similar_products = vector_store.find_similar_products(similar_query)

                if similar_products:
                    return similar_products
            except Exception as e:
                logger.error(f"Error finding similar products: {e}")
                # Fall back to category-based filtering

        # Get all products in the same category
        category_products = products_df[products_df["category"] == main_product.category]

        if category_products.empty:
            return ProductNotFound(
                message=f"No products found in category '{main_product.category}'.",
                query_product_id=product_id,
            )

        # Filter out the main product itself
        category_products = category_products[category_products["product_id"] != product_id]

        related_products = []
        if relationship_type == "complementary":
            # For complementary products, we'll look for items that are commonly bought together
            # or items that complement each other well (this is a simplified example)
            for _, row in category_products.iterrows():
                related_dict: dict[str, Any] = {
                    "product_id": str(row["product_id"]),
                    "name": str(row["name"]),
                    "category": ProductCategory(row["category"]),
                    "stock": int(row["stock"]),
                    "description": str(row["description"]),
                    "product_type": str(row.get("type", "")),
                    "price": float(row["price"]),
                    "seasons": [],
                    "metadata": None,
                }

                # Process seasons correctly to handle 'Fall' vs 'Autumn'
                seasons_str = str(row.get("season", "Spring"))
                if seasons_str:
                    for s in seasons_str.split(","):
                        s = s.strip()
                        if s:
                            # Map 'Fall' to 'Autumn' if needed
                            if s == "Fall":
                                related_dict["seasons"].append(Season.AUTUMN)
                            else:
                                try:
                                    related_dict["seasons"].append(Season(s))
                                except ValueError:
                                    # If not a valid season, use a default
                                    related_dict["seasons"].append(Season.SPRING)

                # If no seasons were added, default to Spring
                if not related_dict["seasons"]:
                    related_dict["seasons"] = [Season.SPRING]

                try:
                    related_products.append(Product(**related_dict))
                except Exception as e:
                    logger.error(f"Error creating related product: {e}")

        elif relationship_type == "alternative":
            # For alternative products, we'll look for any items in the same category
            # Don't apply price filter initially to ensure we find results
            for _, row in category_products.iterrows():
                alt_dict: dict[str, Any] = {
                    "product_id": str(row["product_id"]),
                    "name": str(row["name"]),
                    "category": ProductCategory(row["category"]),
                    "stock": int(row["stock"]),
                    "description": str(row["description"]),
                    "product_type": str(row.get("type", "")),
                    "price": float(row["price"]),
                    "seasons": [],
                    "metadata": None,
                }

                # Process seasons correctly to handle 'Fall' vs 'Autumn'
                seasons_str = str(row.get("season", "Spring"))
                if seasons_str:
                    for s in seasons_str.split(","):
                        s = s.strip()
                        if s:
                            # Map 'Fall' to 'Autumn' if needed
                            if s == "Fall":
                                alt_dict["seasons"].append(Season.AUTUMN)
                            else:
                                try:
                                    alt_dict["seasons"].append(Season(s))
                                except ValueError:
                                    # If not a valid season, use a default
                                    alt_dict["seasons"].append(Season.SPRING)

                # If no seasons were added, default to Spring
                if not alt_dict["seasons"]:
                    alt_dict["seasons"] = [Season.SPRING]

                try:
                    related_products.append(Product(**alt_dict))
                except Exception as e:
                    logger.error(f"Error creating alternative product: {e}")

        else:
            return ProductNotFound(
                message=f"Invalid relationship type: {relationship_type}. Must be 'complementary', 'similar', or 'alternative'.",
                query_product_id=product_id,
            )

        # Sort by price similarity and take top N
        related_products.sort(key=lambda x: abs(float(x.price) - float(main_product.price)))
        related_products = related_products[:limit]

        if not related_products:
            return ProductNotFound(
                message=f"No {relationship_type} products found for product '{product_id}'.",
                query_product_id=product_id,
            )

        return related_products

    except Exception as e:
        return ProductNotFound(
            message=f"Error finding related products: {str(e)}",
            query_product_id=product_id,
        )


@tool  # type: ignore[call-overload]
def resolve_product_reference(tool_input: str) -> Product | ProductNotFound:
    """Resolve a product reference from a natural language query.

    Resolves a product reference dictionary to a specific product using a series of lookup strategies.
    It tries to find a product by ID, then by name, then by semantic description search.

    Args:
        tool_input: JSON string with query field for product reference.

    Returns:
        A Product object if a match is found, otherwise a ProductNotFound object.

    """
    try:
        input_data = json.loads(tool_input)
        query = input_data.get("query", "")
    except (json.JSONDecodeError, AttributeError):
        return ProductNotFound(message=f"Invalid input format: {tool_input}")

    # Check that query is not None before accessing it
    if not query:
        return ProductNotFound(message="Product reference query is empty")

    # Create a ProductSearchQuery
    search_query = ProductSearchQuery(
        query_text=query,
        n_results=1
    )

    try:
        # Initialize VectorStore
        vector_store = VectorStore()

        # Search for products using the new models
        search_results = vector_store.search_products_by_description(search_query)

        if search_results:
            return search_results[0]

        return ProductNotFound(message=f"Could not resolve product reference: {query}")
    except Exception as e:
        logger.error(f"Error resolving product reference: {e}")
        return ProductNotFound(message=f"Error during product reference resolution: {str(e)}")


@tool  # type: ignore[call-overload]
def filtered_product_search(
    input: str,  # This parameter name needs to match what the test is using
    *,
    search_type: str = "description",
    top_k: int = 3,
    category: str | None = None,
    season: str | None = None,
    min_stock: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[Product] | ProductNotFound:
    """Search products with multiple filter options.

    Supports searching by name or description, with additional filters
    like category, season, stock level, and price range.

    Args:
        input: The search query text
        search_type: "name" or "description" (default: "description")
        top_k: Number of results to return (default: 3)
        category: Filter by product category (optional)
        season: Filter by season (optional)
        min_stock: Minimum stock level (optional)
        min_price: Minimum price (optional)
        max_price: Maximum price (optional)

    Returns:
        List of matching Product objects or ProductNotFound

    """
    try:
        # Parameter validation
        query = input  # Use input parameter as query
        if not query:
            return ProductNotFound(message="Search query cannot be empty.")

        if search_type not in ["name", "description"]:
            return ProductNotFound(
                message=f"Invalid search_type: '{search_type}'. Must be 'name' or 'description'."
            )

        # Get the dataframe
        products_df = load_products_df()
        if products_df is None or products_df.empty:
            return ProductNotFound(message="Product catalog data is not loaded.")

        results = []

        # Different search methods based on search_type
        if search_type == "name":
            # Name-based search directly from the dataframe
            try:
                # Filter products where name contains the query (case-insensitive)
                name_filter = products_df["name"].str.lower().str.contains(query.lower())
                matching_products = products_df[name_filter]

                # Convert matching rows to Product objects
                for _, row in matching_products.iterrows():
                    try:
                        product_dict = {
                            "product_id": str(row["product_id"]),
                            "name": str(row["name"]),
                            "description": str(row["description"]),
                            "category": ProductCategory(str(row["category"])),
                            "product_type": str(row.get("type", "")),
                            "stock": int(row["stock"]),
                            "seasons": [],
                            "price": float(row["price"]) if pd.notna(row["price"]) else 0.0,
                            "metadata": None,
                        }

                        # Process seasons correctly to handle 'Fall' vs 'Autumn'
                        seasons_str = str(row.get("season", "Spring"))
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
                        results.append(product)
                    except Exception as e:
                        logger.error(f"Error creating product: {e}", exc_info=True)

                if not results:
                    return ProductNotFound(message=f"No products found with name matching '{query}'")
            except Exception as e:
                logger.error(f"Error during name-based product search: {e}", exc_info=True)
                return ProductNotFound(message=f"Error during name-based product search: {str(e)}")

        elif search_type == "description":
            # Semantic search using vector store
            try:
                vector_store = VectorStore()

                # Attempt to initialize the vector store if needed
                if vector_store._collection is None:
                    # This will trigger vector store initialization with the products dataframe
                    from hermes.config import HermesConfig
                    vector_store._get_vector_store(HermesConfig())

                # If still not initialized, handle the error
                if vector_store._collection is None:
                    raise ValueError("Unable to initialize vector store")

                # Create a ProductSearchQuery for the vector store
                search_query = ProductSearchQuery(
                    query_text=query,
                    n_results=top_k * 2,  # Request more than needed to allow for post-filtering
                    filter_criteria=create_filter_dict(category, season),
                )

                # Get initial results from vector store
                results = vector_store.search_products_by_description(search_query)

                if not results:
                    return ProductNotFound(message=f"No products found matching description '{query}'")
            except Exception as e:
                logger.error(f"Error during semantic product search: {e}", exc_info=True)
                return ProductNotFound(message=f"Error during semantic product search: {str(e)}")

        # Apply additional filters that apply to both search types
        filtered_results = []
        for product in results:
            # Apply stock filter
            if min_stock is not None and product.stock < min_stock:
                continue

            # Apply price filters
            if min_price is not None and product.price < min_price:
                continue
            if max_price is not None and product.price > max_price:
                continue

            # Apply category filter if provided
            if category is not None:
                # Try to match category name case-insensitively
                product_category_str = str(product.category).lower()
                filter_category = category.lower()
                if filter_category not in product_category_str:
                    continue

            # Apply season filter if provided
            if season is not None:
                # Check if the product is available in the specified season
                has_season = False
                for product_season in product.seasons:
                    if season.lower() in str(product_season).lower():
                        has_season = True
                        break
                if not has_season:
                    continue

            filtered_results.append(product)

            # Stop once we have enough results
            if len(filtered_results) >= top_k:
                break

        if not filtered_results:
            return ProductNotFound(
                message=(
                    f"No products found matching query '{query}' with the specified filters. "
                    f"Try broadening your search criteria."
                )
            )

        return filtered_results

    except Exception as e:
        logger.error(f"Error during filtered product search: {e}", exc_info=True)
        return ProductNotFound(message=f"Error during filtered product search: {str(e)}")
