from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal, TypeVar, Union
from enum import Enum

# Enum of nodes
class Agents(str, Enum):
    """Names of our Agents (also nodes in the workflow graph)."""

    EMAIL_ANALYZER = "email_analyzer"
    ORDER_PROCESSOR = "order_processor"
    INQUIRY_RESPONDER = "inquiry_responder"
    RESPONSE_COMPOSER = "response_composer"

class Nodes(str, Enum):
    """Names of our Nodes (also nodes in the workflow graph)."""

    ANALYZE = "analyze"
    PROCESS = "process"
    ANSWER = "answer"
    COMPOSE = "compose"

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


class Error(BaseModel):
    """Error information for agent responses."""
    
    message: str = Field(description="Error message describing what went wrong")
    source: Optional[str] = Field(default=None, description="Source of the error (e.g., agent name)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details if available")


# Type for standardized agent return values
SpecificAgent = TypeVar('SpecificAgent', bound=Agents)
OutputType = TypeVar('OutputType')

# Define common error return type
ErrorReturn = Dict[Literal["errors"], Dict[SpecificAgent, Error]]

# Generic agent output type that combines success and error cases
WorkflowNodeOutput = Union[Dict[SpecificAgent, OutputType], ErrorReturn[SpecificAgent]]
