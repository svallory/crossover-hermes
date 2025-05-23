from dataclasses import dataclass, field
from typing import Annotated, Any

import pandas as pd  # type: ignore
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages  # type: ignore

# Import AlternativeProduct from model




@dataclass
class HermesState:
    """State for the Hermes email processing pipeline."""

    # Input email data
    email_id: str
    email_subject: str | None = None
    email_message: str = ""

    # Agent outputs at each stage (stored as dictionaries for LangGraph state)
    # The actual Pydantic models for these are defined elsewhere (e.g., agents or common_models)
    # and would be instantiated from these dicts by the agents consuming them.
    email_analysis: dict[str, Any] | None = None
    final_response: str | None = None  # Placeholder for final email response

    # LangGraph message history for agent interactions
    messages: Annotated[list[BaseMessage], add_messages] = field(default_factory=list)

    # Error tracking
    errors: list[str] = field(default_factory=list)

    # Optional metadata that might be useful for tracking or debugging
    metadata: dict[str, Any] = field(default_factory=dict)

    # Resources available to agents through state
    # repr=False to avoid large dataframes in state representation if printed
    product_catalog_df: pd.DataFrame | None = field(default=None, repr=False)
    vector_store: Any | None = field(default=None, repr=False)  # ChromaDB client or similar

    # Added from the email analyzer agent in the notebook
    first_pass: dict[str, Any] | None = None
