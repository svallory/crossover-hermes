"""
Common data models and Enums used across the Hermes email processing pipeline.
"""
from enum import Enum
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field

# --- Enums ---
class EmailType(str, Enum):
    """Email classification types"""
    PRODUCT_INQUIRY = "product_inquiry"
    ORDER_REQUEST = "order_request"

class OrderStatus(str, Enum):
    """Order statuses for individual items"""
    CREATED = "created"
    OUT_OF_STOCK = "out_of_stock"
    PARTIALLY_FULFILLED = "partially_fulfilled"

class OverallOrderStatus(str, Enum):
    """Overall order statuses for OrderProcessingResult"""
    CREATED = "created"
    OUT_OF_STOCK = "out_of_stock"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    NO_VALID_PRODUCTS = "no_valid_products"
    ERROR = "error"
    NO_ITEMS_FOUND = "no_items_found"

class ReferenceType(str, Enum):
    """Product reference types"""
    PRODUCT_ID = "product_id"
    PRODUCT_NAME = "product_name"
    DESCRIPTION = "description"
    CATEGORY = "category"

class SignalCategory(str, Enum):
    """Customer signal categories"""
    PURCHASE_INTENT = "Purchase Intent"
    CUSTOMER_CONTEXT = "Customer Context"
    COMMUNICATION_STYLE = "Communication Style"
    EMOTION_AND_TONE = "Emotion and Tone"
    OBJECTION = "Objection"

# --- Pydantic Models ---
class ProductBase(BaseModel):
    """Base class with common product fields"""
    product_id: str = Field(description="Unique identifier for the product.")
    product_name: str = Field(description="Name of the product.")
    price: Optional[float] = Field(default=None, ge=0.0, description="Price of the product. Must be non-negative.")

class Product(ProductBase):
    """Represents a product from the catalog."""
    category: str = Field(description="Category the product belongs to.")
    stock_amount: Annotated[int, Field(ge=0, description="Current stock level. Must be non-negative.")]
    description: str = Field(description="Detailed description of the product.")
    season: Optional[str] = Field(default=None, description="Recommended season for the product.")
    
    @property
    def name(self):
        return self.product_name
    
    @name.setter
    def name(self, value):
        self.product_name = value

class ProductReference(BaseModel):
    """A single product reference extracted from an email."""
    reference_text: str = Field(description="Original text from email referencing the product")
    reference_type: ReferenceType = Field(description="Type: 'product_id', 'product_name', 'description', or 'category'")
    product_id: Optional[str] = Field(default=None, description="Extracted or inferred product ID if available")
    product_name: Optional[str] = Field(default=None, description="Extracted or inferred product name if available")
    quantity: Annotated[int, Field(default=1, ge=1, description="Requested quantity, defaults to 1 if not specified. Must be at least 1.")]
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Confidence in the extraction/match (0.0-1.0)")]
    excerpt: str = Field(description="The exact text phrase from the email that contains this reference")

class CustomerSignal(BaseModel):
    """A customer signal detected in the email, based on the sales intelligence framework."""
    signal_type: str = Field(description="Type of customer signal detected")
    signal_category: SignalCategory = Field(description="Category from sales intelligence framework") 
    signal_text: str = Field(description="The specific text in the email that indicates this signal")
    signal_strength: Annotated[float, Field(ge=0.0, le=1.0, description="Perceived strength or confidence in this signal (0.0-1.0)")]
    excerpt: str = Field(description="The exact text phrase from the email that triggered this signal detection")

class ToneAnalysis(BaseModel):
    """Analysis of the customer's tone and writing style."""
    tone: str = Field(description="Overall detected tone")
    formality_level: Annotated[int, Field(ge=1, le=5, description="Formality level from 1 (very casual) to 5 (very formal)")]
    key_phrases: List[str] = Field(description="Key phrases from the email that informed the tone analysis") 