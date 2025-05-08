""" {cell}
## State Schema

This module defines the state schema for the Hermes LangGraph pipeline.
Managing state effectively is crucial in a multi-agent system, as it dictates
how information flows between different processing nodes (agents).

We're using Python's `dataclasses` with `typing.Annotated` fields to define our state.
This approach provides type safety, clear structure, and compatibility with LangGraph's 
state management mechanisms through reducer functions (e.g., `add_messages`).

The state structure includes:
- Input email data (ID, subject, body)
- Agent outputs at each stage (analysis, order result, inquiry result, final response)
- Message history for conversational context in LangGraph
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Union, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator
import pandas as pd

# Define the Pydantic models that will be used as structured data types within the state
from pydantic import BaseModel, Field

class ProductReference(BaseModel):
    """A single product reference extracted from an email."""
    reference_text: str = Field(description="Original text from email referencing the product")
    reference_type: str = Field(description="Type: 'product_id', 'product_name', 'description', or 'category'")
    product_id: Optional[str] = Field(default=None, description="Extracted or inferred product ID if available")
    product_name: Optional[str] = Field(default=None, description="Extracted or inferred product name if available")
    quantity: int = Field(default=1, description="Requested quantity, defaults to 1 if not specified")
    confidence: float = Field(description="Confidence in the extraction/match (0.0-1.0)")
    excerpt: str = Field(description="The exact text phrase from the email that contains this reference")

class CustomerSignal(BaseModel):
    """A customer signal detected in the email, based on the sales intelligence framework."""
    signal_type: str = Field(description="Type of customer signal detected")
    signal_category: str = Field(description="Category from sales intelligence framework") 
    signal_text: str = Field(description="The specific text in the email that indicates this signal")
    signal_strength: float = Field(description="Perceived strength or confidence in this signal (0.0-1.0)")
    excerpt: str = Field(description="The exact text phrase from the email that triggered this signal detection")

class ToneAnalysis(BaseModel):
    """Analysis of the customer's tone and writing style."""
    tone: str = Field(description="Overall detected tone")
    formality_level: int = Field(description="Formality level from 1 (very casual) to 5 (very formal)")
    key_phrases: List[str] = Field(description="Key phrases from the email that informed the tone analysis")

class EmailAnalysis(BaseModel):
    """Comprehensive structured analysis of a customer email."""
    classification: str = Field(description="Primary classification: 'product_inquiry' or 'order_request'")
    classification_confidence: float = Field(description="Confidence in the classification (0.0-1.0)")
    classification_evidence: str = Field(description="Key text that determined the classification")
    language: str = Field(description="Detected language of the email")
    tone_analysis: ToneAnalysis = Field(description="Analysis of customer's tone and writing style")
    product_references: List[ProductReference] = Field(default_factory=list, description="List of all detected product references")
    customer_signals: List[CustomerSignal] = Field(default_factory=list, description="List of all detected customer signals")
    reasoning: str = Field(description="Reasoning behind the classification")

class OrderItem(BaseModel):
    """Represents a single item within an order."""
    product_id: str = Field(description="Product ID")
    product_name: str = Field(description="Product name")
    quantity_requested: int = Field(description="Quantity requested by the customer")
    quantity_fulfilled: int = Field(default=0, description="Quantity that can be fulfilled from stock")
    status: str = Field(description="Status: 'created', 'out_of_stock', 'partially_fulfilled', etc.")
    unit_price: Optional[float] = Field(default=None, description="Unit price of the product")
    promotion_details: Optional[str] = Field(default=None, description="Applicable promotion if any")
    original_reference_text: Optional[str] = Field(default=None, description="Original text from the email")

class AlternativeProduct(BaseModel):
    """Details of an alternative product suggested for an out-of-stock item."""
    original_product_id: str = Field(description="The out-of-stock product ID")
    original_product_name: str = Field(description="The out-of-stock product name")
    suggested_product_id: str = Field(description="The suggested alternative product ID") 
    suggested_product_name: str = Field(description="The suggested alternative product name")
    stock_available: int = Field(description="Current stock of the alternative product")
    price: Optional[float] = Field(default=None, description="Price of the alternative product")
    reason: str = Field(description="Reason for suggesting this alternative")

class OrderProcessingResult(BaseModel):
    """Complete result of processing an order request."""
    email_id: str = Field(description="Email ID")
    order_items: List[OrderItem] = Field(description="Processed order items")
    overall_status: str = Field(description="Overall order status")
    fulfilled_items_count: int = Field(default=0, description="Number of fully fulfilled items")
    out_of_stock_items_count: int = Field(default=0, description="Number of out-of-stock items")
    total_price: float = Field(default=0.0, description="Total price of fulfilled items")
    suggested_alternatives: List[AlternativeProduct] = Field(default_factory=list, description="Suggested alternatives for out-of-stock items")
    processing_notes: List[str] = Field(default_factory=list, description="Notes or issues encountered during processing")

class ProductInformation(BaseModel):
    """Detailed product information relevant to a customer inquiry."""
    product_id: str = Field(description="Product ID")
    product_name: str = Field(description="Product name")
    details: Dict[str, Any] = Field(description="Key product details relevant to the inquiry")
    availability: str = Field(description="Availability status")
    price: Optional[float] = Field(default=None, description="Product price")
    promotions: Optional[str] = Field(default=None, description="Any promotions for this product")

class QuestionAnswer(BaseModel):
    """A customer's question paired with its answer from product information."""
    question: str = Field(description="The customer's question")
    question_excerpt: Optional[str] = Field(default=None, description="Text from the email containing this question")
    answer: str = Field(description="The answer based on product information")
    confidence: float = Field(description="Confidence in the answer (0.0-1.0)")
    relevant_product_ids: List[str] = Field(default_factory=list, description="Product IDs relevant to this answer")

class InquiryResponse(BaseModel):
    """Complete response to a product inquiry."""
    email_id: str = Field(description="Email ID")
    primary_products: List[ProductInformation] = Field(default_factory=list, description="Main products inquired about")
    answered_questions: List[QuestionAnswer] = Field(default_factory=list, description="Questions answered with information")
    related_products: List[ProductInformation] = Field(default_factory=list, description="Related or complementary products")
    response_points: List[str] = Field(description="Key points to include in response")
    unanswered_questions: List[str] = Field(default_factory=list, description="Questions that couldn't be answered")

# Now define the main state dataclass for LangGraph
@dataclass
class HermesState:
    """State for the Hermes email processing pipeline."""
    # Input email data
    email_id: str
    email_subject: Optional[str] = None
    email_body: str = ""
    
    # Agent outputs at each stage
    email_analysis: Optional[Dict[str, Any]] = None  # EmailAnalysis as dict
    order_result: Optional[Dict[str, Any]] = None    # OrderProcessingResult as dict
    inquiry_result: Optional[Dict[str, Any]] = None  # InquiryResponse as dict
    final_response: Optional[str] = None             # The final generated response
    
    # LangGraph message history for agent interactions
    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    
    # Optional metadata that might be useful for tracking or debugging
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Resources (added)
    product_catalog_df: Optional[pd.DataFrame] = field(default=None, repr=False) # Don't show in repr
    vector_store: Optional[Any] = field(default=None, repr=False) # Don't show in repr

""" {cell}
### State Schema Implementation Notes

The Hermes state schema is organized hierarchically:

1. **Structured Data Models**: We use Pydantic models to define strongly-typed structures for:
   - Email analysis (classification, tone, product references, customer signals)
   - Order processing (items, status, alternatives)
   - Inquiry handling (product information, questions/answers)

2. **State Propagation**: 
   - We store agent outputs as dictionaries in the state to facilitate serialization/deserialization.
   - When an agent generates a structured output (e.g., `EmailAnalysis`), it's converted to a dict with `model_dump()` before being stored in state.
   - Subsequent agents can deserialize this data by reconstructing the model (e.g., `EmailAnalysis(**state.email_analysis)`).

3. **Message History**:
   - The `messages` field uses the `Annotated` type with the `add_messages` reducer.
   - The reducer tells LangGraph how to combine message lists when multiple nodes update this field.
   - The `field(default_factory=list)` ensures each state instance gets its own empty list.

4. **Error Handling**:
   - We include an `errors` field to track issues that might occur during processing.
   - This allows for graceful degradation rather than complete failure.

5. **Metadata**:
   - The `metadata` field provides a flexible place for additional context information.
   - This could include timing information, debug flags, or other useful execution context.

This state schema balances structured typing (for reliability) with flexibility (for ease of serialization and extension).
""" 