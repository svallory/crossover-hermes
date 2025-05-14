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
from typing import List, Dict, Any, Optional, Annotated # Removed TypedDict, Union, Sequence, Enum, auto, BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator # operator might not be used anymore directly in this file
import pandas as pd
# Removed Pydantic model imports as they are now in common_model.py or agent files
# from pydantic import BaseModel, Field
# Removed Enum import as enums are now in common_model.py
# from enum import Enum, auto

# All Enums (EmailType, OrderStatus, OverallOrderStatus, ReferenceType, SignalCategory)
# and Pydantic Models (ProductBase, Product, ProductReference, CustomerSignal, ToneAnalysis,
# EmailAnalysis, OrderItem, AlternativeProduct, OrderProcessingResult, ProductInformation,
# QuestionAnswer, InquiryResponse) have been moved to src/common_model.py or respective agent files.

# Now define the main state dataclass for LangGraph
@dataclass
class HermesState:
    """State for the Hermes email processing pipeline."""
    # Input email data
    email_id: str
    email_subject: Optional[str] = None
    email_body: str = ""
    
    # Agent outputs at each stage (stored as dictionaries)
    # The actual Pydantic models are defined in src/common_model.py or agent-specific files.
    email_analysis: Optional[Dict[str, Any]] = None  # Corresponds to EmailAnalysis model
    order_result: Optional[Dict[str, Any]] = None    # Corresponds to OrderProcessingResult model
    inquiry_result: Optional[Dict[str, Any]] = None  # Corresponds to InquiryResponse model
    final_response: Optional[str] = None             # The final generated response string
    
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

1. **Structured Data Models**: Pydantic models define strongly-typed structures.
   These models are now located in `src/common_model.py` for shared models/enums,
   or at the beginning of the respective agent files for agent-specific output structures
   (e.g., `EmailAnalysis` in `email_classifier.py`).

2. **State Propagation**: 
   - The `HermesState` class stores agent outputs as dictionaries (e.g., `email_analysis: Optional[Dict[str, Any]]`).
   - Agents produce these dictionaries using `.model_dump()` on their Pydantic output models.
   - Subsequent agents reconstruct the Pydantic models from these dictionaries (e.g., `EmailAnalysis(**state.email_analysis)`).
     They import the necessary Pydantic model definitions from `src/common_model.py` or the relevant agent file.

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

6. **Enum Usage**:
   - String Enums for constants like email types, order statuses, etc., are now defined in `src/common_model.py`.
   - This provides type safety and autocompletion support while maintaining string compatibility.

This state schema balances structured typing (for reliability) with flexibility (for ease of serialization and extension).
Models are now more modular, residing either in a common module or with the agent that produces them.
""" 