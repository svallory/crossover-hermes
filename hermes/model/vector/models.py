"""Models for vector store operations and RAG functionality.

This module defines standardized models for vector store operations, including
search queries and results. These models provide a consistent interface for
working with vector embeddings and semantic search functionality.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class ProductQueryBase(BaseModel):
    """Base class for product search queries."""
    
    n_results: int = Field(default=5, description="Maximum number of products to return")
    filter_criteria: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Optional metadata filters to apply (e.g., category, season)"
    )
    include_attributes: List[str] = Field(
        default_factory=lambda: ["product_id", "name", "description", "category", "stock", "price"],
        description="Product attributes to include in results"
    )


class ProductSearchQuery(ProductQueryBase):
    """Query for semantic search of products by natural language description."""
    
    query_text: str = Field(description="Natural language description of the product(s) to search for")


class SimilarProductQuery(ProductQueryBase):
    """Query for finding products similar to a reference product."""
    
    product_id: str = Field(description="ID of the reference product to find similar items for")
    exclude_reference: bool = Field(default=True, description="Whether to exclude the reference product from results")


class ProductSearchResult(BaseModel):
    """Result of a product search with relevance information."""
    
    product_id: str = Field(description="ID of the matched product")
    product_name: str = Field(description="Name of the product")
    product_metadata: Dict[str, Any] = Field(description="Product metadata (category, season, etc.)")
    similarity_score: float = Field(
        ge=0.0, le=1.0, 
        description="Similarity score between query and product (0.0 to 1.0)"
    )


class ProductRecommendationResponse(BaseModel):
    """Structured response containing product recommendations."""
    
    recommended_products: List[Dict[str, Any]] = Field(
        description="List of recommended products with their details"
    )
    explanation: str = Field(
        description="Explanation of why these products match the customer's query"
    )
    follow_up_questions: Optional[List[str]] = Field(
        default=None,
        description="Suggested follow-up questions to clarify customer needs if needed"
    ) 