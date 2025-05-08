""" {cell}
## Product Catalog Tools

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
"""
from langchain_core.tools import tool
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import pandas as pd

# --- Input/Output Models for Tools ---

class Product(BaseModel):
    """Represents a product from the catalog."""
    product_id: str = Field(description="Unique identifier for the product.")
    name: str = Field(description="Name of the product.")
    category: str = Field(description="Category the product belongs to.")
    stock_amount: int = Field(description="Current stock level.")
    description: str = Field(description="Detailed description of the product.")
    season: Optional[str] = Field(default=None, description="Recommended season for the product.")
    price: Optional[float] = Field(default=None, description="Price of the product.")

class ProductNotFound(BaseModel):
    """Indicates that a product was not found."""
    message: str
    query_product_id: Optional[str] = None
    query_product_name: Optional[str] = None

class FuzzyMatchResult(BaseModel):
    """Result of a fuzzy name match."""
    matched_product: Product
    similarity_score: float = Field(description="Similarity score between 0.0 and 1.0")

# --- Tool Definitions ---

@tool
def find_product_by_id(product_id: str, product_catalog_df: pd.DataFrame) -> Union[Product, ProductNotFound]:
    """    Retrieve detailed product information by its exact Product ID.
    You should use this tool when you have a precise Product ID (e.g., 'LTH0976', 'CSH1098').
    
    Args:
        product_id: The exact Product ID to search for (case-sensitive).
        product_catalog_df: The pandas DataFrame containing the product catalog.
        
    Returns:
        A Product object if found, or a ProductNotFound object if no product matches the ID.
    """
    # Standardize the product ID format (remove spaces and convert to uppercase)
    product_id = product_id.replace(" ", "").upper()
    
    # Search for the product in the DataFrame
    product_data = product_catalog_df[product_catalog_df['product_id'] == product_id]
    
    if product_data.empty:
        return ProductNotFound(
            message=f"Product with ID '{product_id}' not found in catalog.",
            query_product_id=product_id
        )
    
    # Map DataFrame columns to our Product model fields
    product_row = product_data.iloc[0]
    
    # Handle potential missing columns
    product_dict = {
        "product_id": product_row['product_id'],
        "name": product_row['name'],
        "category": product_row['category'],
        "stock_amount": int(product_row['stock']),
        "description": product_row['description']
    }
    
    # Add optional fields if present
    if 'season' in product_row and pd.notna(product_row['season']):
        product_dict["season"] = product_row['season']
    if 'price' in product_row and pd.notna(product_row['price']):
        product_dict["price"] = float(product_row['price'])
        
    return Product(**product_dict)

@tool(infer_schema=False)
def find_product_by_name(product_name: str, product_catalog_df: pd.DataFrame, threshold: float = 0.8, top_n: int = 3) -> Union[List[FuzzyMatchResult], ProductNotFound]:
    """    Find products by name using fuzzy matching.
    Use this when the customer provides a product name that might have typos, be incomplete, or slightly different from the catalog.
    
    Args:
        product_name: The product name to search for.
        product_catalog_df: The pandas DataFrame containing the product catalog.
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
    all_product_names = product_catalog_df['name'].tolist()
    
    # Find the best matches using fuzzy string matching
    # Returns list of tuples: (matched_name, score)
    matches = process.extractBests(
        query=product_name,
        choices=all_product_names,
        score_cutoff=threshold * 100,  # thefuzz uses 0-100 scale
        limit=top_n
    )
    
    if not matches:
        return ProductNotFound(
            message=f"No products found similar to '{product_name}' with threshold {threshold}.",
            query_product_name=product_name
        )
    
    results = []
    for matched_name, score in matches:
        # Get full product data for this match
        product_data = product_catalog_df[product_catalog_df['name'] == matched_name]
        if not product_data.empty:
            product_row = product_data.iloc[0]
            
            # Build product dict
            product_dict = {
                "product_id": product_row['product_id'],
                "name": product_row['name'],
                "category": product_row['category'],
                "stock_amount": int(product_row['stock']),
                "description": product_row['description']
            }
            
            # Add optional fields if present
            if 'season' in product_row and pd.notna(product_row['season']):
                product_dict["season"] = product_row['season']
            if 'price' in product_row and pd.notna(product_row['price']):
                product_dict["price"] = float(product_row['price'])
            
            product = Product(**product_dict)
            results.append(FuzzyMatchResult(
                matched_product=product,
                similarity_score=score / 100  # Convert score back to 0-1 scale
            ))
    
    # Return results sorted by similarity score (highest first)
    return sorted(results, key=lambda x: x.similarity_score, reverse=True)

@tool
def search_products_by_description(query: str, vector_store: Any, product_catalog_df: pd.DataFrame, top_k: int = 3, category_filter: Optional[str] = None) -> Union[List[Product], ProductNotFound]:
    """    Search for products based on a natural language description of their features, use case, or style (semantic search using RAG).
    Use this for inquiries like "looking for a warm scarf for winter" or "a dress for a summer wedding".
    
    Args:
        query: The natural language query describing the desired product.
        vector_store: The vector store instance for performing similarity search. This will be injected automatically.
        product_catalog_df: The pandas DataFrame containing the product catalog, used to retrieve full product details.
        top_k: The number of top matching products to return. Defaults to 3.
        category_filter: Optional category to filter the search. If provided, only products from this category will be searched.
        
    Returns:
        A list of Product objects that are semantically similar to the query, or a ProductNotFound object if no relevant products are found.
    """
    # Define metadata filter for category if provided
    metadata_filter = None
    if category_filter:
        metadata_filter = {"category": category_filter}
    
    # Perform vector similarity search
    try:
        # Invoke similarity search on the vector store
        # This will return tuples of (Document, score) where Document has page_content and metadata
        search_results = vector_store.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=metadata_filter
        )
        
        if not search_results:
            return ProductNotFound(message=f"No products found matching the description: '{query}'.")
        
        # Extract product information from search results
        products = []
        for doc, score in search_results:
            # Extract product_id from document metadata
            product_id = doc.metadata.get('product_id')
            if not product_id:
                continue
                
            # Lookup full product details from the DataFrame
            product_data = product_catalog_df[product_catalog_df['product_id'] == product_id]
            if product_data.empty:
                continue
                
            product_row = product_data.iloc[0]
            
            # Build product dict
            product_dict = {
                "product_id": product_row['product_id'],
                "name": product_row['name'],
                "category": product_row['category'],
                "stock_amount": int(product_row['stock']),
                "description": product_row['description']
            }
            
            # Add optional fields if present
            if 'season' in product_row and pd.notna(product_row['season']):
                product_dict["season"] = product_row['season']
            if 'price' in product_row and pd.notna(product_row['price']):
                product_dict["price"] = float(product_row['price'])
            
            products.append(Product(**product_dict))
        
        if not products:
            return ProductNotFound(message=f"No products found matching the description: '{query}'.")
            
        return products
        
    except Exception as e:
        # Handle errors in vector search
        return ProductNotFound(message=f"Error during product search: {str(e)}")

@tool
def find_related_products(product_id: str, product_catalog_df: pd.DataFrame, relationship_type: str = "complementary", limit: int = 2) -> Union[List[Product], ProductNotFound]:
    """    Find products related to a given product ID, such as complementary items or alternatives from the same category.
    For example, suggesting matching accessories for a dress or similar style products.
    
    Args:
        product_id: The Product ID of the main product to find relations for.
        product_catalog_df: The pandas DataFrame containing the product catalog.
        relationship_type: Type of relationship. Options: "complementary", "alternative", "same_category". Defaults to "complementary".
        limit: Maximum number of related products to return. Defaults to 2.
        
    Returns:
        A list of related Product objects, or a ProductNotFound object if no related products are found or the main product doesn't exist.
    """
    # First verify that the main product exists
    main_product_result = find_product_by_id.invoke({
        "product_id": product_id, 
        "product_catalog_df": product_catalog_df
    })
    if isinstance(main_product_result, ProductNotFound):
        return main_product_result
    
    main_product = main_product_result
    related_products = []
    
    # Handle different relationship types
    if relationship_type == "same_category":
        # Find products in the same category
        category_matches = product_catalog_df[
            (product_catalog_df['category'] == main_product.category) & 
            (product_catalog_df['product_id'] != main_product.product_id)
        ]
        
        # Sort by stock amount (prefer products with stock)
        category_matches = category_matches.sort_values(by='stock', ascending=False)
        
        # Take top matches up to limit
        for _, product_row in category_matches.head(limit).iterrows():
            product_dict = {
                "product_id": product_row['product_id'],
                "name": product_row['name'],
                "category": product_row['category'],
                "stock_amount": int(product_row['stock']),
                "description": product_row['description']
            }
            
            # Add optional fields if present
            if 'season' in product_row and pd.notna(product_row['season']):
                product_dict["season"] = product_row['season']
            if 'price' in product_row and pd.notna(product_row['price']):
                product_dict["price"] = float(product_row['price'])
            
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
            "Accessories": ["Bags", "Shoes", "Tops"]
        }
        
        target_categories = complementary_categories.get(main_product.category, [])
        if not target_categories:
            return ProductNotFound(
                message=f"No complementary categories defined for '{main_product.category}'.",
                query_product_id=product_id
            )
        
        # Find products in complementary categories
        complementary_matches = product_catalog_df[
            product_catalog_df['category'].isin(target_categories)
        ]
        
        # Sort by stock amount (prefer products with stock)
        complementary_matches = complementary_matches.sort_values(by='stock', ascending=False)
        
        # Take top matches up to limit
        for _, product_row in complementary_matches.head(limit).iterrows():
            product_dict = {
                "product_id": product_row['product_id'],
                "name": product_row['name'],
                "category": product_row['category'],
                "stock_amount": int(product_row['stock']),
                "description": product_row['description']
            }
            
            # Add optional fields if present
            if 'season' in product_row and pd.notna(product_row['season']):
                product_dict["season"] = product_row['season']
            if 'price' in product_row and pd.notna(product_row['price']):
                product_dict["price"] = float(product_row['price'])
            
            related_products.append(Product(**product_dict))
            
    elif relationship_type == "alternative":
        # Find alternative products (similar to main product but different)
        # They should be in the same category but have different features
        
        # Filter for same category but different product
        alternatives = product_catalog_df[
            (product_catalog_df['category'] == main_product.category) & 
            (product_catalog_df['product_id'] != main_product.product_id)
        ]
        
        # If there's a season, prefer matching the same season
        if main_product.season and 'season' in product_catalog_df.columns:
            # First try exact season match
            season_matches = alternatives[alternatives['season'] == main_product.season]
            if not season_matches.empty:
                alternatives = season_matches
        
        # Sort by stock amount (prefer products with stock)
        alternatives = alternatives.sort_values(by='stock', ascending=False)
        
        # Take top matches up to limit
        for _, product_row in alternatives.head(limit).iterrows():
            product_dict = {
                "product_id": product_row['product_id'],
                "name": product_row['name'],
                "category": product_row['category'],
                "stock_amount": int(product_row['stock']),
                "description": product_row['description']
            }
            
            # Add optional fields if present
            if 'season' in product_row and pd.notna(product_row['season']):
                product_dict["season"] = product_row['season']
            if 'price' in product_row and pd.notna(product_row['price']):
                product_dict["price"] = float(product_row['price'])
            
            related_products.append(Product(**product_dict))
    
    else:
        return ProductNotFound(
            message=f"Unknown relationship type: '{relationship_type}'. Valid options are 'complementary', 'alternative', 'same_category'.",
            query_product_id=product_id
        )
    
    if not related_products:
        return ProductNotFound(
            message=f"No '{relationship_type}' products found related to '{main_product.name}'.",
            query_product_id=product_id
        )
    
    return related_products
""" {cell}
### Catalog Tools Implementation Notes

The catalog tools provide a comprehensive interface for interacting with product data. Key aspects:

1. **Flexible Product Lookup**: The tools cover multiple ways to find products:
   - `find_product_by_id`: Direct lookup with exact ID matching
   - `find_product_by_name`: Fuzzy matching for imprecise product names
   - `search_products_by_description`: Vector-based semantic search using RAG
   - `find_related_products`: Discovering related/alternative products

2. **Robust Error Handling**: Each tool returns a `ProductNotFound` model with helpful error messages and the original query, rather than raising exceptions.

3. **Fuzzy Matching**: The `find_product_by_name` tool uses `thefuzz` library for approximate string matching, making it robust against typos and slight naming variations.

4. **Category-Based Pre-filtering**: The RAG search supports optional category filtering, improving the relevance of results and optimizing performance for large catalogs.

5. **Related Product Logic**: The `find_related_products` tool implements multiple relationship types:
   - `same_category`: Products in the same category
   - `complementary`: Products that pair well with the original item
   - `alternative`: Similar products that could substitute for the original

These tools form the foundation for both the Order Processor and Inquiry Responder agents, enabling accurate product resolution and relevant recommendations.
""" 