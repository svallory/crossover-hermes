from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from enum import Enum
from typing import TypedDict, TypeVar, Generic


class ProductCategory(str, Enum):
    """Categories of products available in the store."""

    ACCESSORIES = "Accessories"
    BAGS = "Bags"
    KIDS_CLOTHING = "Kid's Clothing"
    LOUNGEWEAR = "Loungewear"
    MENS_ACCESSORIES = "Men's Accessories"
    MENS_CLOTHING = "Men's Clothing"
    MENS_SHOES = "Men's Shoes"
    WOMENS_CLOTHING = "Women's Clothing"
    WOMENS_SHOES = "Women's Shoes"


class Season(str, Enum):
    """Seasons in which a product is available."""

    SPRING = "Spring"
    SUMMER = "Summer"
    AUTUMN = "Autumn"
    WINTER = "Winter"


class Product(BaseModel):
    """A product from the catalog."""

    product_id: str = Field(description="The unique identifier for the product")
    product_name: str = Field(description="The name of the product")
    product_description: str = Field(description="The description of the product")
    product_category: ProductCategory = Field(description="The category of the product")
    product_type: str = Field(description="The fundamental product type in the general category")
    stock: int = Field(description="The number of items in stock")
    seasons: List[Season] = Field(description="The seasons the product is ideal for")
    price: float = Field(description="The price of the product")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the product")
