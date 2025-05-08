""" {cell}
## Product Catalog Tools

This module provides tools for interacting with the product catalog. These tools enable functionalities such
as finding products by ID or name, searching products based on their descriptions (semantic search),
and discovering related products. These are essential for agents that need to retrieve product information
to answer inquiries or process orders.

The tools are designed to be used within a LangChain agent framework and will require access to product data
(e.g., a product database or DataFrame) and a vector store for semantic search capabilities.
The specific data access mechanisms will be implemented in the full versions of these tools.
"""
from langchain_core.tools import tool
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ValidationError
import pandas as pd # For mock data interaction
from fuzzywuzzy import process as fuzzy_process # For fuzzy name matching

# Assuming VectorStoreInterface or Chroma instance type hint is needed
# from src.vectorstore import search_vector_store, Chroma # Use actual import
# For now use Any as type hint for vector store instance
VectorStoreInstanceType = Any 

# --- Input/Output Models for Tools ---

class Product(BaseModel):
    """Represents a product from the catalog."""
    product_id: str = Field(..., description="Unique identifier for the product.")
    name: str = Field(..., description="Name of the product.")
    category: str = Field(..., description="Category the product belongs to.")
    stock_amount: int = Field(..., description="Current stock quantity.")
    description: str = Field(..., description="Detailed description of the product.")
    season: Optional[str] = Field(default=None, description="Applicable season for the product (e.g., 'Summer', 'Winter').")
    price: Optional[float] = Field(default=None, description="Price of the product.")
    
    # Ensure stock is non-negative
    @field_validator('stock_amount')
    def check_stock_non_negative(cls, v):
        if v < 0:
            # In reality, stock shouldn't be negative, but data might be imperfect.
            # Log a warning, perhaps? For now, allow but maybe clamp at 0?
            print(f"Warning: Product stock amount is negative ({v}). Clamping to 0 for model.")
            return 0
        return v

    # Ensure price is non-negative if present
    @field_validator('price')
    def check_price_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('price must be non-negative')
        return v

class ProductNotFound(BaseModel):
    """Indicates that a product was not found."""
    error: str = Field(description="Error message indicating the product was not found.")
    query_type: str = Field(description="The type of query that failed (e.g., 'id', 'name').")
    query_value: str = Field(description="The value used for the query.")

class FuzzyMatchResult(BaseModel):
    """Result of a fuzzy name match."""
    matched_product: Product
    similarity_score: float = Field(description="Similarity score between 0.0 and 1.0")

class ProductMatch(Product):
    """Represents a product found via search, with a similarity score."""
    similarity_score: Optional[float] = Field(default=None, description="Similarity score for the match (0.0 to 1.0 or 0-100 for fuzzywuzzy).")

# --- Mock Data Setup (Simulating DataFrame and Vector Store Access) ---
# In a real implementation, this would interact with actual data sources passed via config or context.

# Global mock product DataFrame (load this properly in a real scenario)
MOCK_PRODUCTS_DF = pd.DataFrame({
    'product ID': ['P001', 'P002', 'P003', 'P004', 'P005'],
    'name': ['Classic T-Shirt', 'Slim Fit Jeans', 'Classic Tee', 'Leather Wallet', 'Summer Dress'],
    'category': ['Apparel', 'Apparel', 'Apparel', 'Accessories', 'Apparel'],
    'stock amount': [100, 50, 120, 200, 30],
    'description': [
        'A comfortable and stylish classic t-shirt made from 100% cotton.',
        'Modern slim fit jeans, perfect for any casual occasion. Stretch denim for comfort.',
        'Another great tee for your collection.',
        'A high-quality leather wallet with multiple card slots and a coin pocket. Special promotion: 10% off!',
        'A light and airy summer dress, ideal for warm weather. Available in vibrant colors.'
    ],
    'season': ['All', 'All', 'All', 'All', 'Summer'],
    'price': [25.00, 60.00, 22.00, 45.00, 75.00]
})
MOCK_PRODUCTS_DF.rename(columns={
    'product ID': 'product_id',
    'stock amount': 'stock_amount'
}, inplace=True)

# Mock Vector Store (this would be an actual VectorStore instance, e.g., Chroma)
MOCK_VECTOR_STORE = None # Will be initialized if needed by search_products_by_description

# --- Tool Definitions ---

@tool
def find_product_by_id(product_id: str, products_df: pd.DataFrame) -> Union[Product, ProductNotFound]:
    """
    Retrieves product information by its exact product ID from the provided product catalog DataFrame.
    Use this tool when you have a specific product ID from the customer or a previous step.

    Args:
        product_id: The exact product ID to look up (e.g., 'P001', 'LTH0976').
        products_df: The pandas DataFrame containing the product catalog data.

    Returns:
        A Product object if found, or a ProductNotFound object if the ID does not exist in the DataFrame.
    """
    if not isinstance(products_df, pd.DataFrame):
         return ProductNotFound(error="Invalid product catalog data provided to tool.", query_type="id", query_value=product_id)
    if 'product_id' not in products_df.columns:
         return ProductNotFound(error="Product catalog data is missing 'product_id' column.", query_type="id", query_value=product_id)
         
    result_df = products_df[products_df['product_id'] == product_id]
    if not result_df.empty:
        try:
            # Convert row to dict, handle potential NaN for optional fields
            product_data = result_df.iloc[0].where(pd.notna(result_df.iloc[0]), None).to_dict()
            # Ensure required fields are present
            required_fields = Product.model_fields.keys()
            product_data_filtered = {k: v for k, v in product_data.items() if k in required_fields}
            return Product(**product_data_filtered)
        except ValidationError as e:
             return ProductNotFound(error=f"Data validation error for product ID '{product_id}': {e}", query_type="id", query_value=product_id)
        except Exception as e:
            return ProductNotFound(error=f"Unexpected error retrieving data for product ID '{product_id}': {e}", query_type="id", query_value=product_id)
            
    return ProductNotFound(error=f"Product with ID '{product_id}' not found.", query_type="id", query_value=product_id)

@tool
def find_product_by_name(product_name: str, products_df: pd.DataFrame, min_similarity_threshold: float = 80.0, limit: int = 3) -> Union[List[ProductMatch], ProductNotFound]:
    """
    Finds products matching a given name using fuzzy string matching against the provided product catalog DataFrame.
    Useful when the customer provides a product name that might have variations or misspellings.
    Returns a list of possible matches, ordered by similarity.

    Args:
        product_name: The product name to search for (e.g., 'Classic T-Shirt', 'Leather Wallet').
        products_df: The pandas DataFrame containing the product catalog data.
        min_similarity_threshold: The minimum similarity score (0-100) for a product to be considered a match. Defaults to 80.0.
        limit: The maximum number of matches to return. Defaults to 3.

    Returns:
        A list of ProductMatch objects (product details + similarity score), sorted by score,
        or a ProductNotFound object if no products meet the similarity threshold.
    """
    if not isinstance(products_df, pd.DataFrame):
         return ProductNotFound(error="Invalid product catalog data provided to tool.", query_type="name", query_value=product_name)
    if 'name' not in products_df.columns:
         return ProductNotFound(error="Product catalog data is missing 'name' column.", query_type="name", query_value=product_name)
         
    choices = products_df['name'].dropna().tolist()
    if not choices:
        return ProductNotFound(error="No product names available in the catalog to search.", query_type="name", query_value=product_name)
        
    matches = fuzzy_process.extract(product_name, choices, limit=limit * 2) # Get more initially to filter by score
    
    found_products: List[ProductMatch] = []
    matched_names = set() # Avoid duplicate products if names are identical

    for name_match, score in matches:
        if score >= min_similarity_threshold and name_match not in matched_names:
            # Find the first row matching this name
            product_series = products_df[products_df['name'] == name_match].iloc[0]
            try:
                product_data = product_series.where(pd.notna(product_series), None).to_dict()
                required_fields = Product.model_fields.keys()
                product_data_filtered = {k: v for k, v in product_data.items() if k in required_fields}
                found_products.append(ProductMatch(**product_data_filtered, similarity_score=float(score)))
                matched_names.add(name_match)
                if len(found_products) >= limit:
                     break # Stop once we have enough matches meeting threshold
            except ValidationError as e:
                print(f"Warning: Skipping product '{name_match}' due to data validation error: {e}")
            except Exception as e:
                 print(f"Warning: Skipping product '{name_match}' due to unexpected error: {e}")

    if not found_products:
        return ProductNotFound(error=f"No products found sufficiently matching name '{product_name}' (threshold {min_similarity_threshold}).", query_type="name", query_value=product_name)
    
    # Sort by score just in case the limit wasn't hit exactly on threshold boundary
    return sorted(found_products, key=lambda p: p.similarity_score, reverse=True)

@tool
async def search_products_by_description(query: str, vector_store: VectorStoreInstanceType, top_k: int = 3, category_filter: Optional[str] = None) -> Union[List[Dict[str, Any]], ProductNotFound]:
    """
    Searches for products using semantic similarity via the provided vector store instance.
    Useful for vague customer queries (e.g., 'a warm jacket for winter').
    Optionally filters by category.

    Args:
        query: The natural language search query.
        vector_store: The initialized vector store instance (e.g., Chroma) capable of search.
        top_k: Maximum number of relevant products to return. Defaults to 3.
        category_filter: Optional category to filter results by (case-insensitive).

    Returns:
        A list of dictionaries, each containing product metadata (like product_id, name, category, price, stock_amount)
        and a similarity score, sorted by score. Returns ProductNotFound if the search fails or yields no results.
    """
    if vector_store is None:
        return ProductNotFound(error="Vector store instance is not available for search.", query_type="description", query_value=query)
        
    # Import the actual search function dynamically or assume it's passed correctly.
    # Using a placeholder name here, replace with actual import/call structure.
    # search_function = getattr(vector_store_module, "search_vector_store", None)
    # For now, assume vector_store object has the search method directly (like Chroma)
    search_function = getattr(vector_store, 'similarity_search_with_score', None) # Standard LangChain interface
    embedding_function = getattr(vector_store, 'embedding_function', None)
    
    if not callable(search_function) or not embedding_function:
         return ProductNotFound(error="Vector store instance does not support similarity search or embedding function missing.", query_type="description", query_value=query)

    # Construct the filter for ChromaDB (or other vector store) - as done in vectorstore.py
    filters = []
    if category_filter:
        filters.append({"category": {"$eq": category_filter.lower()}})
    # Add other filters (price, stock) here if needed, based on vectorstore.py implementation
    # Example: filters.append({"price": {"$gte": 50, "$lte": 100}})

    chroma_where_filter = None
    if len(filters) == 1:
        chroma_where_filter = filters[0]
    elif len(filters) > 1:
        chroma_where_filter = {"$and": filters}

    try:
        print(f"Performing vector search for: '{query}', k={top_k}, filter={chroma_where_filter}")
        # Use the vector store's search method directly
        results_with_scores = await asyncio.to_thread( # Run sync search in thread pool if store is sync
            vector_store.similarity_search_with_score, 
            query=query, 
            k=top_k, 
            where=chroma_where_filter
        )
        # If the vector store is natively async, use: 
        # results_with_scores = await vector_store.asimilarity_search_with_score(...)

        formatted_results = []
        for doc, score in results_with_scores:
            res = doc.metadata.copy()
            res['similarity_score'] = score
            formatted_results.append(res)
            
        if not formatted_results:
             return ProductNotFound(error=f"No products found matching description query '{query}' with specified filters.", query_type="description", query_value=query)
             
        return formatted_results # Already sorted by score by the search method

    except Exception as e:
        print(f"ERROR during vector search: {e}")
        return ProductNotFound(error=f"Vector search failed: {e}", query_type="description", query_value=query)

@tool
def find_related_products(
    product_id: str,
    products_df: pd.DataFrame,
    relationship_type: str = "complementary", 
    limit: int = 3,
    exclude_product_ids: Optional[List[str]] = None
) -> Union[List[Product], ProductNotFound]:
    """
    Finds products related to a given product ID from the catalog DataFrame.
    Relationships: 'complementary' (items often bought together, e.g., different categories), 
    'alternative' (items that could substitute, e.g., same category, similar price/features, in stock),
    or 'same_category' (other items in the same category).
    Helps in making suggestions or providing alternatives.

    Args:
        product_id: The ID of the reference product.
        products_df: The pandas DataFrame containing the product catalog data.
        relationship_type: Type of relationship: 'complementary', 'alternative', 'same_category'. Defaults to 'complementary'.
        limit: Maximum number of related products to return. Defaults to 3.
        exclude_product_ids: Optional list of product IDs to exclude from the results.

    Returns:
        A list of Product objects that are related, or ProductNotFound if none found or reference product invalid.
    """
    if not isinstance(products_df, pd.DataFrame):
         return ProductNotFound(error="Invalid product catalog data provided.", query_type="related", query_value=product_id)
         
    # Find the target product first
    target_product_result = find_product_by_id(product_id, products_df)
    if isinstance(target_product_result, ProductNotFound):
        # Propagate the error message from find_product_by_id
        target_product_result.query_type = "related_items_ref_not_found" # Overwrite type
        return target_product_result

    related_products: List[Product] = []
    # Create a copy to avoid modifying the original DataFrame passed in
    current_df = products_df[products_df['product_id'] != product_id].copy()

    if exclude_product_ids:
        current_df = current_df[~current_df['product_id'].isin(exclude_product_ids)]

    target_category = target_product_result.category

    if relationship_type == "same_category":
        related_df = current_df[current_df['category'] == target_category]
        
    elif relationship_type == "alternative":
        # Find in-stock items in the same category (simplistic approach)
        related_df = current_df[
            (current_df['category'] == target_category) & 
            (current_df['stock_amount'] > 0)
        ]
        # Could add price similarity or semantic similarity checks here if needed
        
    elif relationship_type == "complementary":
        # Simple mock logic: suggest Accessories for Apparel and vice-versa
        if target_category == "Apparel":
            related_df = current_df[current_df['category'] == "Accessories"]
        elif target_category == "Accessories":
            related_df = current_df[current_df['category'] == "Apparel"]
        else:
            # Fallback: suggest items from any *different* category
            related_df = current_df[current_df['category'] != target_category]
    else:
        return ProductNotFound(error=f"Unsupported relationship type: '{relationship_type}'. Supported: 'complementary', 'alternative', 'same_category'.", query_type="related_items_invalid_type", query_value=relationship_type)

    # Convert results to Product models
    for _, row in related_df.head(limit).iterrows():
        try:
            product_data = row.where(pd.notna(row), None).to_dict()
            required_fields = Product.model_fields.keys()
            product_data_filtered = {k: v for k, v in product_data.items() if k in required_fields}
            related_products.append(Product(**product_data_filtered))
        except ValidationError as e:
            print(f"Warning: Skipping related product {row.get('product_id')} due to validation error: {e}")
        except Exception as e:
            print(f"Warning: Skipping related product {row.get('product_id')} due to unexpected error: {e}")

    if not related_products:
        return ProductNotFound(error=f"No '{relationship_type}' products found for product ID '{product_id}'.", query_type="related_items_none_found", query_value=product_id)
        
    return related_products

""" {cell}
### Tool Implementation Notes:

- **Dependency Injection**: The `product_catalog_df` and `vector_store` arguments are intended to be supplied by the agent execution environment. In LangGraph, this can be managed by passing these resources as part of the `RunnableConfig` or by making them accessible via a shared context that tools can access.
- **Error Handling**: Each tool returns a `ProductNotFound` model if it cannot find relevant data. This structured error allows the calling agent to understand the failure and potentially try a different approach or inform the user.
- **Fuzzy Matching and Semantic Search**: `find_product_by_name` would use a library like `thefuzz` for efficient fuzzy string matching. `search_products_by_description` is the core RAG tool, relying on a pre-populated vector store (e.g., ChromaDB with OpenAI embeddings) for semantic similarity searches.
- **Actual Data Interaction**: The current implementations are placeholders using `print` statements and returning mock data. In a real deployment, they would interact with a live pandas DataFrame (loaded from the Google Sheet) and a configured vector store instance.
- **Pydantic Models**: The `Product`, `ProductNotFound`, and `FuzzyMatchResult` models ensure that the data passed to and from the tools is well-structured and validated.
""" 