from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages  # type: ignore
import pandas as pd  # type: ignore

# Import AlternativeProduct from model

# Forward declaration for type hints if models are in different files and imported later
# from .common_models import EmailAnalysis, OrderProcessingResult, InquiryResolution


@dataclass
class HermesState:
    """State for the Hermes email processing pipeline."""

    # Input email data
    email_id: str
    email_subject: Optional[str] = None
    email_message: str = ""

    # Agent outputs at each stage (stored as dictionaries for LangGraph state)
    # The actual Pydantic models for these are defined elsewhere (e.g., agents or common_models)
    # and would be instantiated from these dicts by the agents consuming them.
    email_analysis: Optional[Dict[str, Any]] = None
    # order_result: Optional[Dict[str, Any]] = None # Placeholder if order processing is added
    # inquiry_result: Optional[Dict[str, Any]] = None # Placeholder if inquiry resolution is added
    final_response: Optional[str] = None  # Placeholder for final email response

    # LangGraph message history for agent interactions
    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)

    # Error tracking
    errors: List[str] = field(default_factory=list)

    # Optional metadata that might be useful for tracking or debugging
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Resources available to agents through state
    # repr=False to avoid large dataframes in state representation if printed
    product_catalog_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    vector_store: Optional[Any] = field(default=None, repr=False)  # ChromaDB client or similar

    # Added from the email analyzer agent in the notebook
    first_pass: Optional[Dict[str, Any]] = None
