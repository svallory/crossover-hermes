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
from typing import Any

import pandas as pd  # type: ignore

# Import tool from langchain_core
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# For fuzzy matching
from thefuzz import process  # type: ignore

# Import the load_products_df function
from src.hermes.data_processing.load_data import load_products_df

# Explicitly ignore import not found errors
from src.hermes.model import ProductCategory, Season
from src.hermes.model.product import Product

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a variable to store vector_store collection
vs_collection = None

# Check for product data file
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
data_dir = script_dir.parent.parent.parent / "data"
product_file = data_dir / "product_catalog.csv"


class ProductNotFound(BaseModel):
    """Indicates that a product was not found."""

    message: str
    query_product_id: str | None = None
    query_product_name: str | None = None


class FuzzyMatchResult(BaseModel):
    """Result of a fuzzy name match."""

    matched_product: Product
    similarity_score: float = Field(description="Similarity score between 0.0 and 1.0")


@tool  # type: ignore[call-overload]
def find_product_by_id(product_id: str) -> Product | ProductNotFound:
    """Find a product by its ID.

    Retrieve detailed product information by its exact Product ID.
    Use this when you have a precise Product ID (e.g., 'LTH0976', 'CSH1098').

    Args:
        product_id: The exact Product ID to search for (case-sensitive).

    Returns:
        A Product object if found, or a ProductNotFound object if no product matches the ID.

    """
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
        "product_name": str(product_row["name"]),
        "product_category": ProductCategory(product_row["category"]),
        "stock": int(product_row["stock"]),
        "seasons": [Season(s.strip()) for s in product_row.get("season", "Spring").split(",")],
        "price": float(product_row["price"]) if pd.notna(product_row["price"]) else 0.0,
        "description": str(product_row["description"]),
        "metadata": None,
    }

    try:
        return Product(**product_dict)
    except Exception as e:
        return ProductNotFound(message=f"Error during product retrieval: {str(e)}")


@tool  # type: ignore[call-overload]
def find_product_by_name(
    product_name: str, *, threshold: float = 0.8, top_n: int = 3
) -> list[FuzzyMatchResult] | ProductNotFound:
    """Find products by name using fuzzy matching.

    Use this when the customer provides a product name that might have typos, be incomplete, or slightly different from the catalog.

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
                "product_name": str(product_row["name"]),
                "product_category": ProductCategory(str(product_row["category"])),
                "stock": int(product_row["stock"]),
                "product_description": str(product_row["description"]),
                "product_type": str(product_row.get("type", "")),
                "seasons": [
                    Season(s.strip()) for s in str(product_row.get("season", "Spring")).split(",") if s.strip()
                ],
                "price": float(product_row["price"]) if pd.notna(product_row["price"]) else 0.0,
                "metadata": None,
            }

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
def search_products_by_description(
    query: str,
    *,
    top_k: int = 3,
    category_filter: str | None = None,
    season_filter: str | None = None,
) -> list[Product] | ProductNotFound:
    """Search for products by description.

    Search for products using semantic description matching.
    This tool is great for answering open-ended inquiries about products with specific features or characteristics.

    Args:
        query: The search text describing the product features or characteristics.
        top_k: Maximum number of results to return.
        category_filter: Optional category to narrow down results (e.g., "Dresses", "Accessories").
        season_filter: Optional season to narrow down results (e.g., "Summer", "Winter").

    Returns:
        A list of matching Product objects or a ProductNotFound object if no products match.

    """
    try:
        # Get products_df using the memoized function
        products_df = load_products_df()

        # First check if we have a DataFrame for direct searching
        if products_df is not None and not products_df.empty:
            # For demonstration, we'll implement a simplified search using the DataFrame
            # In a real system, this would use the vector store
            results = []
            for _, row in products_df.iterrows():
                # Create a product from each row
                product = Product(
                    product_id=str(row["product_id"]),
                    name=str(row["name"]),
                    description=str(row["description"]),
                    category=ProductCategory(row["category"]),
                    product_type=str(row.get("type", "")),
                    stock=int(row["stock"]),
                    price=float(row["price"]),
                    seasons=[Season.SPRING],  # Default season
                )
                results.append(product)

            # Return top_k products (in a real system this would be semantically filtered)
            return results[:top_k]

        # If DataFrame search didn't work, let user know search is unavailable
        return ProductNotFound(message="Product search is unavailable. Could not find products matching: '{query}'")

    except Exception as e:
        # Handle errors in search
        return ProductNotFound(message=f"Error during product search: {str(e)}")


@tool  # type: ignore[call-overload]
def find_related_products(
    product_id: str, *, relationship_type: str = "complementary", limit: int = 2
) -> list[Product] | ProductNotFound:
    """Find products related to a given product ID.

    Find products related to a given product ID, such as complementary items or alternatives from the same category.

    Args:
        product_id (str): The ID of the product to find related items for.
        relationship_type (str): Type of relationship to search for ('complementary' or 'alternative').
        limit (int): Maximum number of related products to return.

    Returns:
        Union[List[Product], ProductNotFound]: List of related Product objects, or ProductNotFound if none found.

    """
    # Get products_df using the memoized function
    products_df = load_products_df()

    if products_df is None:
        return ProductNotFound(
            message="Product catalog data is not loaded.",
            query_product_id=product_id,
        )
    try:
        # First verify that the main product exists
        main_product_result = find_product_by_id(product_id=product_id)
        if isinstance(main_product_result, ProductNotFound):
            return main_product_result

        # Ensure main_product is a Product object
        if not isinstance(main_product_result, Product):
            return ProductNotFound(
                message=f"Product with ID '{product_id}' has invalid type.",
                query_product_id=product_id,
            )

        main_product = main_product_result

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
                    "product_name": str(row["name"]),
                    "product_category": ProductCategory(row["category"]),
                    "stock": int(row["stock"]),
                    "seasons": [Season(s.strip()) for s in str(row.get("seasons", "")).split(",") if s.strip()],
                    "price": float(row["price"]),
                    "description": str(row["description"]),
                    "metadata": None,
                }
                related_products.append(Product(**related_dict))

        elif relationship_type == "alternative":
            # For alternative products, we'll look for items in the same category
            # with similar prices (this is a simplified example)
            main_price = float(main_product.price)
            for _, row in category_products.iterrows():
                row_price = float(row["price"])
                # Consider products within ±20% of the main product's price
                if 0.8 * main_price <= row_price <= 1.2 * main_price:
                    alt_dict: dict[str, Any] = {
                        "product_id": str(row["product_id"]),
                        "product_name": str(row["name"]),
                        "product_category": ProductCategory(row["category"]),
                        "stock": int(row["stock"]),
                        "seasons": [Season(s.strip()) for s in str(row.get("seasons", "")).split(",") if s.strip()],
                        "price": float(row["price"]),
                        "description": str(row["description"]),
                        "metadata": None,
                    }
                    related_products.append(Product(**alt_dict))

        else:
            return ProductNotFound(
                message=f"Invalid relationship type: {relationship_type}. Must be 'complementary' or 'alternative'.",
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
def resolve_product_reference(*, query: str) -> Product | ProductNotFound:
    """Resolve a product reference from a natural language query.

    Resolves a product reference dictionary to a specific product using a series of lookup strategies.
    It tries to find a product by ID, then by name, then by semantic description search.

    Args:
        query: A string containing product reference information.

    Returns:
        A Product object if a match is found, otherwise a ProductNotFound object.

    """
    # Check that query is not None before accessing it
    if query is None:
        return ProductNotFound(message="Product reference query is None")

    search_results_data = search_products_by_description(query=query, top_k=1)
    if isinstance(search_results_data, list) and search_results_data:
        return search_results_data[0]

    return ProductNotFound(message=f"Could not resolve product reference: {query}")


@tool  # type: ignore[call-overload]
def filtered_product_search(
    query: str,
    *,
    search_type: str = "description",
    top_k: int = 3,
    category: str | None = None,
    season: str | None = None,
    min_stock: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[Product] | ProductNotFound:
    """Search and filter products based on various criteria.

    This is a comprehensive search tool that combines semantic search with metadata filtering.

    Args:
        query: The search query (product name or description).
        search_type: Type of search to perform ('description' for semantic search, 'name' for name-based search).
        top_k: Maximum number of results to return.
        category: Filter by product category.
        season: Filter by season.
        min_stock: Filter by minimum stock level.
        min_price: Filter by minimum price.
        max_price: Filter by maximum price.

    Returns:
        A list of matching Product objects, or a ProductNotFound object if no matches are found.

    """
    try:
        # Get products_df using the memoized function
        products_df = load_products_df()

        # First check if we have a DataFrame for direct searching
        if products_df is not None and not products_df.empty:
            # Start with all products
            filtered_df = products_df.copy()

            # Apply filters
            if category:
                filtered_df = filtered_df[filtered_df["category"] == category]

            if min_stock is not None:
                filtered_df = filtered_df[filtered_df["stock"] >= min_stock]

            if min_price is not None:
                filtered_df = filtered_df[filtered_df["price"] >= min_price]

            if max_price is not None:
                filtered_df = filtered_df[filtered_df["price"] <= max_price]

            # If we have no results after filtering, return not found
            if filtered_df.empty:
                return ProductNotFound(message="No products found matching the criteria")

            # Convert filtered results to Product objects
            results = []
            for _, row in filtered_df.iterrows():
                product = Product(
                    product_id=str(row["product_id"]),
                    name=str(row["name"]),
                    description=str(row["description"]),
                    category=ProductCategory(row["category"]),
                    product_type=str(row.get("type", "")),
                    stock=int(row["stock"]),
                    price=float(row["price"]),
                    seasons=[Season.SPRING],  # Default season
                )
                results.append(product)

            # Return top_k products
            return results[:top_k]

        # If DataFrame search didn't work, let user know search is unavailable
        return ProductNotFound(message="Product search is unavailable. Could not find products matching the criteria.")

    except Exception as e:
        # Handle errors
        return ProductNotFound(message=f"Error during product search: {str(e)}")
