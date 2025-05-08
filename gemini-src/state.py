""" {cell}
## State Management

This module defines the state schema for the Hermes LangGraph pipeline. Effective state management
is crucial for passing data between different nodes (agents) in the graph.

**Key Design Choices:**

- **TypedDict for State**: We use `TypedDict` to define the structure of our application state.
  This provides type hinting and improves code readability and maintainability compared to
  using plain dictionaries.

- **Annotated Fields with Reducers**: For fields that need to accumulate data across multiple
  agent calls (like a list of messages), we use `typing.Annotated`. This allows us to associate
  a reducer function (e.g., `add_messages`) with a field. LangGraph uses these reducers to
  correctly update the state.

- **Comprehensive State Fields**: The `HermesState` includes fields for all critical pieces of
  information that need to be passed through the workflow. This includes:
    - Original email data.
    - Outputs from the `Email Analyzer Agent` (classification, tone, signals, product references).
    - Outputs from the `Order Processor Agent` (order status, updated inventory summary).
    - Outputs from the `Inquiry Responder Agent` (answers, retrieved product information).
    - The final composed response.
    - A list of messages to track the conversation history with LLMs, which is vital for context and debugging.

- **Modularity and Clarity**: Separating state definition into its own module (`state.py`)
  keeps the main pipeline logic cleaner and makes the data flow easier to understand.
  The `reference-solution-spec.md` recommends `dataclass` with `Annotated` fields, but also mentions that `TypedDict` with `Annotated` fields is used in `agent-flow.md` and that the decision was to use `TypedDict`. We will adhere to the `TypedDict` approach as per the Q&A decision.

This structured approach to state management is a best practice in LangGraph and ensures that the pipeline is robust and easy to debug.
"""

from typing import List, Optional, TypedDict, Sequence, Annotated, Union
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage, SystemMessage
from operator import add

# Placeholder Pydantic models for agent outputs - these would ideally be imported
# from the respective agent modules once they are fully defined with Pydantic.
# For now, using simple TypedDicts or Any as placeholders in HermesState.
# The reference-agent-flow.md provides detailed Pydantic models for these.

class EmailAnalysisOutput(TypedDict):
    """Placeholder for the output of the Email Analyzer Agent."""
    classification: str
    classification_confidence: float
    classification_evidence: str
    language: str
    # tone_analysis: ToneAnalysis # Placeholder for ToneAnalysis Pydantic model
    # product_references: List[ProductReference] # Placeholder for List[ProductReference Pydantic model]
    # customer_signals: List[CustomerSignal] # Placeholder for List[CustomerSignal Pydantic model]
    tone_analysis: dict # Simplified for now
    product_references: list # Simplified for now
    customer_signals: list # Simplified for now
    reasoning: str

class OrderProcessingOutput(TypedDict):
    """Placeholder for the output of the Order Processor Agent."""
    email_id: str
    # order_items: List[OrderItem] # Placeholder for List[OrderItem Pydantic model]
    order_items: list # Simplified for now
    fulfilled_items: int
    out_of_stock_items: int
    total_price: float
    # recommended_alternatives: List[dict] # Placeholder for List[AlternativeProduct Pydantic model]
    recommended_alternatives: list # Simplified for now
    # This might also include an inventory_update_summary or similar field

class InquiryResponseOutput(TypedDict):
    """Placeholder for the output of the Inquiry Responder Agent."""
    email_id: str
    # primary_products: List[ProductInformation] # Placeholder for List[ProductInformation Pydantic model]
    # answered_questions: List[QuestionAnswer] # Placeholder for List[QuestionAnswer Pydantic model]
    # related_products: List[ProductInformation] # Placeholder for List[ProductInformation Pydantic model]
    primary_products: list # Simplified for now
    answered_questions: list # Simplified for now
    related_products: list # Simplified for now
    response_points: List[str]

def add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """Adds messages to the state. Helper for Annotated field."""
    return list(left) + list(right)

class HermesState(TypedDict):
    """
    Represents the state of the Hermes email processing pipeline.
    This TypedDict will be passed between nodes in the LangGraph.
    """
    # Input email data
    email_id: str
    email_subject: Optional[str]
    email_body: str

    # Agent outputs - using more specific types once Pydantic models are defined
    email_analysis_output: Optional[EmailAnalysisOutput]
    order_processing_output: Optional[OrderProcessingOutput]
    inquiry_response_output: Optional[InquiryResponseOutput]

    # Final composed response
    final_response_text: Optional[str]

    # List of messages for interaction with LLMs (e.g., for an agent's internal thought process or history)
    # The `add_messages` function will be used by LangGraph to update this field.
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Configuration (can be passed via RunnableConfig if needed, but often useful to have a snapshot in state)
    # For this reference, we assume config is accessible elsewhere or passed directly to agents.
    # config: Optional[HermesConfig] # Example: from src.config import HermesConfig

    # Error handling / status
    error_message: Optional[str]
    current_agent_name: Optional[str] # To track which agent is currently processing

""" {cell}
### Explanation of State Fields

-   `email_id`, `email_subject`, `email_body`: Store the raw input email data.
-   `email_analysis_output`: Stores the structured output from the `Email Analyzer Agent`. This includes classification, language, tone, extracted product references, and customer signals.
-   `order_processing_output`: Stores the results from the `Order Processor Agent`, such as order items, status (created/out of stock), and any suggested alternatives.
-   `inquiry_response_output`: Stores the information compiled by the `Inquiry Responder Agent`, including answers to questions and relevant product details retrieved via RAG.
-   `final_response_text`: Holds the final, customer-facing email response generated by the `Response Composer Agent`.
-   `messages`: A crucial field for LangGraph, especially when using LLMs in agents. It accumulates the sequence of `BaseMessage` objects (System, Human, AI, Tool messages). The `Annotated[Sequence[BaseMessage], add_messages]` syntax tells LangGraph to use the `add_messages` function to append new messages to this list rather than overwriting it. This is essential for maintaining conversational context for LLMs.
-   `error_message`: A field to store any error messages if a step in the pipeline fails, allowing for graceful error handling or reporting.
-   `current_agent_name`: Useful for logging and debugging, indicating which agent is currently active or was last active.

### Reducer Function (`add_messages`)

The `add_messages` function is a simple reducer that concatenates sequences of messages. LangGraph uses this function when a node returns a dictionary with a `messages` key. Instead of replacing the existing `messages` in the state, it appends the new messages. This pattern is standard for managing conversational history in LangGraph.

### Evolution of Agent Output Types

The `EmailAnalysisOutput`, `OrderProcessingOutput`, and `InquiryResponseOutput` are currently defined as `TypedDict` placeholders. As the Pydantic models for these outputs are fully implemented in their respective agent files (based on `reference-agent-flow.md`), these type hints in `HermesState` should be updated to use those specific Pydantic models for better type safety and clarity. This iterative refinement is a natural part of developing complex data workflows.
""" 