"""
Product Catalog Tools

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

from typing import List, Optional, Dict, Any, Union, Tuple
from pydantic import BaseModel, Field
import pandas as pd
import chromadb
from langchain_core.tools import tool

from src.hermes.model import Product
from src.hermes.data_processing.vector_store import (
    search_products_by_description as vs_search_products,
    search_products_by_name as vs_search_products_by_name,
    filtered_search_products as vs_filtered_search,
    create_filter_dict,
)
from src.hermes.data_processing.load_data import products_df, vector_store


class ProductNotFound(BaseModel):
    """Indicates that a product was not found."""

    message: str
    query_product_id: Optional[str] = None
    query_product_name: Optional[str] = None


class FuzzyMatchResult(BaseModel):
    """Result of a fuzzy name match."""

    matched_product: Product
    similarity_score: float = Field(description="Similarity score between 0.0 and 1.0")


@tool
def find_product_by_id(product_id: str) -> Union[Product, ProductNotFound]:
    """
    Retrieve detailed product information by its exact Product ID.
    Use this when you have a precise Product ID (e.g., 'LTH0976', 'CSH1098').

    Args:
        product_id: The exact Product ID to search for (case-sensitive).

    Returns:
        A Product object if found, or a ProductNotFound object if no product matches the ID.
    """
    # Standardize the product ID format (remove spaces and convert to uppercase)
    product_id = product_id.replace(" ", "").upper()

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
    product_dict = {
        "product_id": product_row["product_id"],
        "name": product_row["name"],
        "category": product_row["category"],
        "stock_amount": int(product_row["stock"]),
        "description": product_row["description"],
    }

    # Add optional fields if present
    if "season" in product_row and pd.notna(product_row["season"]):
        product_dict["season"] = product_row["season"]
    if "price" in product_row and pd.notna(product_row["price"]):
        product_dict["price"] = float(product_row["price"])

    return Product(**product_dict)


@tool
def find_product_by_name(
    product_name: str, threshold: float = 0.8, top_n: int = 3
) -> Union[List[FuzzyMatchResult], ProductNotFound]:
    """
    Find products by name using fuzzy matching.
    Use this when the customer provides a product name that might have typos, be incomplete, or slightly different from the catalog.

    Args:
        product_name: The product name to search for.
        threshold: Minimum similarity score (0.0 to 1.0) for a match to be considered. Defaults to 0.8.
        top_n: Maximum number of top matching products to return. Defaults to 3.

    Returns:
        A list of FuzzyMatchResult objects for products matching the name above the threshold, sorted by similarity,
        or a ProductNotFound object if no sufficiently similar products are found.
    """
    from thefuzz import process

    # Make sure the input is a string
    product_name = str(product_name).strip()

    # All product names from the catalog
    # Assuming column name is 'name' based on the assignment spreadsheet
    all_product_names = products_df["name"].tolist()

    # Find the best matches using fuzzy string matching
    # Returns list of tuples: (matched_name, score)
    matches = process.extractBests(
        query=product_name,
        choices=all_product_names,
        score_cutoff=threshold * 100,  # thefuzz uses 0-100 scale
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

            # Build product dict
            product_dict = {
                "product_id": product_row["product_id"],
                "name": product_row["name"],
                "category": product_row["category"],
                "stock_amount": int(product_row["stock"]),
                "description": product_row["description"],
            }

            # Add optional fields if present
            if "season" in product_row and pd.notna(product_row["season"]):
                product_dict["season"] = product_row["season"]
            if "price" in product_row and pd.notna(product_row["price"]):
                product_dict["price"] = float(product_row["price"])

            product = Product(**product_dict)
            results.append(
                FuzzyMatchResult(
                    matched_product=product,
                    similarity_score=score / 100,  # Convert score back to 0-1 scale
                )
            )

    # Return results sorted by similarity score (highest first)
    return sorted(results, key=lambda x: x.similarity_score, reverse=True)


@tool
def search_products_by_description(
    query: str,
    top_k: int = 3,
    category_filter: Optional[str] = None,
    season_filter: Optional[str] = None,
) -> Union[List[Product], ProductNotFound]:
    """
    Search for products based on a natural language description of their features, use case, or style (semantic search using RAG).
    Use this for inquiries like "looking for a warm scarf for winter" or "a dress for a summer wedding".

    Args:
        query: The natural language query describing the desired product.
        top_k: The number of top matching products to return. Defaults to 3.
        category_filter: Optional category to filter the search. If provided, only products from this category will be searched.
        season_filter: Optional season to filter the search. If provided, only products for this season will be searched.

    Returns:
        A list of Product objects that are semantically similar to the query, or a ProductNotFound object if no relevant products are found.
    """
    try:
        # Create filters dictionary if any filters are specified
        filters = None
        if category_filter or season_filter:
            filters = create_filter_dict(category=category_filter, season=season_filter)

        # Use the vector store search function with enhanced filtering
        products = vs_search_products(
            collection=vector_store,
            query=query,
            top_k=top_k,
            category_filter=category_filter,  # For backward compatibility
            filters=filters,
        )

        if not products:
            message = f"No products found matching the description: '{query}'"
            if category_filter:
                message += f" in category '{category_filter}'"
            if season_filter:
                message += f" for season '{season_filter}'"
            return ProductNotFound(message=message)

        return products

    except Exception as e:
        # Handle errors in vector search
        return ProductNotFound(message=f"Error during product search: {str(e)}")


@tool
def find_related_products(
    product_id: str, relationship_type: str = "complementary", limit: int = 2
) -> Union[List[Product], ProductNotFound]:
    """
    Find products related to a given product ID, such as complementary items or alternatives from the same category.
    For example, suggesting matching accessories for a dress or similar style products.

    Args:
        product_id: The Product ID of the main product to find relations for.
        relationship_type: Type of relationship. Options: "complementary", "alternative", "same_category". Defaults to "complementary".
        limit: Maximum number of related products to return. Defaults to 2.

    Returns:
        A list of related Product objects, or a ProductNotFound object if no related products are found or the main product doesn't exist.
    """
    # First verify that the main product exists
    main_product_result = find_product_by_id(product_id=product_id)
    if isinstance(main_product_result, ProductNotFound):
        return main_product_result

    main_product = main_product_result
    related_products = []

    # Handle different relationship types
    if relationship_type == "same_category":
        # Find products in the same category
        category_matches = products_df[
            (products_df["category"] == main_product.category)
            & (products_df["product_id"] != main_product.product_id)
        ]

        # Sort by stock amount (prefer products with stock)
        category_matches = category_matches.sort_values(by="stock", ascending=False)

        # Take top matches up to limit
        for _, product_row in category_matches.head(limit).iterrows():
            product_dict = {
                "product_id": product_row["product_id"],
                "name": product_row["name"],
                "category": product_row["category"],
                "stock_amount": int(product_row["stock"]),
                "description": product_row["description"],
            }

            # Add optional fields if present
            if "season" in product_row and pd.notna(product_row["season"]):
                product_dict["season"] = product_row["season"]
            if "price" in product_row and pd.notna(product_row["price"]):
                product_dict["price"] = float(product_row["price"])

            related_products.append(Product(**product_dict))

    elif relationship_type == "complementary":
        # For complementary items, use category relationships
        # This is a simplified approach; a real system might have a more sophisticated
        # product relationship graph or recommendation system

        complementary_categories = {
            "Dresses": ["Accessories", "Shoes", "Bags"],
            "Tops": ["Bottoms", "Accessories"],
            "Bottoms": ["Tops", "Shoes"],
            "Suits": ["Shoes", "Accessories"],
            "Shoes": ["Accessories", "Bags"],
            "Bags": ["Accessories", "Shoes"],
            "Accessories": ["Bags", "Shoes", "Tops"],
        }

        target_categories = complementary_categories.get(main_product.category, [])
        if not target_categories:
            return ProductNotFound(
                message=f"No complementary categories defined for '{main_product.category}'.",
                query_product_id=product_id,
            )

        # Find products in complementary categories
        complementary_matches = products_df[
            products_df["category"].isin(target_categories)
        ]

        # Sort by stock amount (prefer products with stock)
        complementary_matches = complementary_matches.sort_values(
            by="stock", ascending=False
        )

        # Take top matches up to limit
        for _, product_row in complementary_matches.head(limit).iterrows():
            product_dict = {
                "product_id": product_row["product_id"],
                "name": product_row["name"],
                "category": product_row["category"],
                "stock_amount": int(product_row["stock"]),
                "description": product_row["description"],
            }

            # Add optional fields if present
            if "season" in product_row and pd.notna(product_row["season"]):
                product_dict["season"] = product_row["season"]
            if "price" in product_row and pd.notna(product_row["price"]):
                product_dict["price"] = float(product_row["price"])

            related_products.append(Product(**product_dict))

    elif relationship_type == "alternative":
        # Find alternative products (similar to main product but different)
        # They should be in the same category but have different features

        # Filter for same category but different product
        alternatives = products_df[
            (products_df["category"] == main_product.category)
            & (products_df["product_id"] != main_product.product_id)
        ]

        # If there's a season, prefer matching the same season
        if main_product.season and "season" in products_df.columns:
            # First try exact season match
            season_matches = alternatives[alternatives["season"] == main_product.season]
            if not season_matches.empty:
                alternatives = season_matches

        # Sort by stock amount (prefer products with stock)
        alternatives = alternatives.sort_values(by="stock", ascending=False)

        # Take top matches up to limit
        for _, product_row in alternatives.head(limit).iterrows():
            product_dict = {
                "product_id": product_row["product_id"],
                "name": product_row["name"],
                "category": product_row["category"],
                "stock_amount": int(product_row["stock"]),
                "description": product_row["description"],
            }

            # Add optional fields if present
            if "season" in product_row and pd.notna(product_row["season"]):
                product_dict["season"] = product_row["season"]
            if "price" in product_row and pd.notna(product_row["price"]):
                product_dict["price"] = float(product_row["price"])

            related_products.append(Product(**product_dict))

    else:
        return ProductNotFound(
            message=f"Unknown relationship type: '{relationship_type}'. Valid options are 'complementary', 'alternative', 'same_category'.",
            query_product_id=product_id,
        )

    if not related_products:
        return ProductNotFound(
            message=f"No '{relationship_type}' products found related to '{main_product.name}'.",
            query_product_id=product_id,
        )

    return related_products


@tool
def resolve_product_reference(
    product_ref_dict: Dict[str, Any],
) -> Union[Product, ProductNotFound]:
    """
    Resolves a product reference dictionary to a specific product using a series of lookup strategies.
    It tries to find a product by ID, then by name, then by semantic description search.

    Args:
        product_ref_dict: A dictionary containing product reference information.
                          Expected keys: 'product_id' (Optional[str]), 'product_name' (Optional[str]), 'reference_text' (Optional[str]).

    Returns:
        A Product object if a match is found, otherwise a ProductNotFound object.
    """
    product_id = product_ref_dict.get("product_id")
    product_name = product_ref_dict.get("product_name")
    reference_text = product_ref_dict.get("reference_text", "")

    if product_id:
        product_result = find_product_by_id(product_id=product_id)
        if not isinstance(product_result, ProductNotFound):
            return product_result

    if product_name:
        name_results = find_product_by_name(
            product_name=product_name, threshold=0.8, top_n=1
        )
        if isinstance(name_results, list) and name_results:
            if isinstance(name_results[0], FuzzyMatchResult):
                return name_results[0].matched_product
        elif isinstance(name_results, FuzzyMatchResult):
            return name_results.matched_product

    if reference_text:
        search_results_data = search_products_by_description(
            query=reference_text, top_k=1
        )
        if isinstance(search_results_data, list) and search_results_data:
            return search_results_data[0]

    return ProductNotFound(
        message=f"Could not resolve product reference: {product_ref_dict}"
    )


@tool
def filtered_product_search(
    query: str,
    search_type: str = "description",
    top_k: int = 3,
    category: Optional[str] = None,
    season: Optional[str] = None,
    min_stock: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> Union[List[Product], ProductNotFound]:
    """
    Search for products with customizable filters using semantic search.
    This is a flexible search tool that combines name or description search with multiple filtering options.

    Args:
        query: The search text (product description or name depending on search_type)
        search_type: Either "description" for semantic search or "name" for product name search
        top_k: Maximum number of results to return
        category: Optional category to filter by (e.g., "Dresses", "Accessories")
        season: Optional season to filter by (e.g., "Summer", "Winter")
        min_stock: Optional minimum stock level to filter by
        min_price: Optional minimum price for filtered products
        max_price: Optional maximum price for filtered products

    Returns:
        A list of matching Product objects or ProductNotFound if no matches
    """
    try:
        # Create price range tuple if either price filter is specified
        price_range = None
        if min_price is not None or max_price is not None:
            price_range = (min_price, max_price)

        # Use the enhanced filtered search function
        products = vs_filtered_search(
            collection=vector_store,
            query=query,
            top_k=top_k,
            category=category,
            season=season,
            min_stock=min_stock,
            price_range=price_range,
            search_type=search_type,
        )

        if not products:
            message = f"No products found matching '{query}'"
            if category:
                message += f" in category '{category}'"
            if season:
                message += f" for season '{season}'"
            if min_stock is not None:
                message += f" with at least {min_stock} in stock"
            if price_range:
                if min_price is not None:
                    message += f" with minimum price ${min_price}"
                if max_price is not None:
                    message += f" with maximum price ${max_price}"
            return ProductNotFound(message=message)

        return products

    except Exception as e:
        # Handle errors
        return ProductNotFound(
            message=f"Error during filtered product search: {str(e)}"
        )
