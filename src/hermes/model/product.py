from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from src.hermes.model.enums import ProductCategory, Season


class Product(BaseModel):
    """A product from the catalog."""

    product_id: str = Field(description="The unique identifier for the product")
    name: str = Field(description="The name of the product")
    description: str = Field(description="The description of the product")
    category: ProductCategory = Field(description="The category of the product")
    product_type: str = Field(description="The fundamental product type in the general category")
    stock: int = Field(description="The number of items in stock")
    seasons: List[Season] = Field(description="The seasons the product is ideal for")
    price: float = Field(description="The price of the product")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the product")


class AlternativeProduct(BaseModel):
    """A recommended alternative product."""

    product: Product = Field(description="The product being recommended as an alternative")
    similarity_score: float = Field(description="Similarity score to the requested product")
    reason: str = Field(description="Reason this product is recommended as an alternative")
