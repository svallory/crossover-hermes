""" {cell}
### Hermes Processing Pipeline Definition

This module defines the core processing pipeline for the Hermes email system using LangGraph.
It orchestrates the flow of execution between the different specialized agents:

1.  **Email Analyzer**: Analyzes the incoming email.
2.  **Conditional Routing**: Directs the flow based on the classification ("order_request" or "product_inquiry").
3.  **Order Processor**: Handles order requests.
4.  **Inquiry Responder**: Handles product inquiries.
5.  **Response Composer**: Generates the final response after either the order or inquiry path is complete.

**Implementation Details:**

-   Uses `langgraph.graph.StateGraph` to define the workflow.
-   The state schema is imported from `src.state.HermesState`.
-   Agent node functions (`analyze_email_node`, `order_processor_agent_node`, etc.) are imported from `src.agents`.
-   A conditional routing function (`route_by_classification`) determines the path after the initial analysis.
-   The final compiled graph (`hermes_workflow`) represents the complete, executable pipeline.
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any, Optional

# Import the state definition and agent node functions
# These imports assume the files exist and functions are correctly defined
# In a real project structure, relative imports might be used, e.g., from .state import HermesState
# For notebook concatenation, direct imports might work if cells are ordered correctly.
# Using placeholders for now to indicate dependencies:
# from src.state import HermesState # This is the TypedDict state definition
# from src.agents.email_classifier import analyze_email_node
# from src.agents.order_processor import order_processor_agent_node
# from src.agents.inquiry_responder import inquiry_responder_agent_node
# from src.agents.response_composer import response_composer_agent_node

# --- Placeholder Imports (Replace with actual imports) ---
# Define dummy functions and state for structure validation
class PlaceholderHermesState(dict): pass # LangGraph uses dict-like state
async def analyze_email_node(state: Dict[str, Any], config: Any, llm: Any) -> Dict[str, Any]:
    print("Executing analyze_email_node (placeholder)")
    # Mock output based on input, needed for routing
    body = state.get('email_body','').lower()
    classification = "product_inquiry"
    if "order" in body or "buy" in body:
        classification = "order_request"
    mock_analysis = {
        "classification": classification,
        "classification_confidence": 0.9,
        "classification_evidence": "mock evidence",
        "language": "en",
        "tone_analysis": {"tone": "neutral", "formality_level": 3, "key_phrases": []},
        "product_references": [],
        "customer_signals": [],
        "reasoning": "mock reasoning"
    }
    return {"email_analysis_output": mock_analysis}

async def order_processor_agent_node(state: Dict[str, Any], config: Any, tools: Dict[str, Any]) -> Dict[str, Any]:
    print("Executing order_processor_agent_node (placeholder)")
    mock_order_result = {
        "email_id": state.get("email_id"),
        "order_items": [],
        "overall_order_status": "mock_processed",
        "total_price_fulfilled": 0.0,
        "out_of_stock_items_count": 0,
        "suggested_alternatives": [],
        "processing_notes": ["mock order processing notes"]
    }
    return {"order_processing_output": mock_order_result}

async def inquiry_responder_agent_node(state: Dict[str, Any], config: Any, llm: Any, vector_store: Any, tools: Dict[str, Any]) -> Dict[str, Any]:
    print("Executing inquiry_responder_agent_node (placeholder)")
    mock_inquiry_result = {
        "email_id": state.get("email_id"),
        "primary_products_discussed": [],
        "answered_questions": [],
        "suggested_related_products": [],
        "response_points": ["mock inquiry response points"],
        "unanswered_question_topics": []
    }
    return {"inquiry_response_output": mock_inquiry_result}

async def response_composer_agent_node(state: Dict[str, Any], config: Any, llm: Any, compose_response_prompt: Any) -> Dict[str, Any]:
    print("Executing response_composer_agent_node (placeholder)")
    return {"final_response_text": "This is a mock final response."}
# --- End Placeholder Imports ---

# Define node names for clarity
NODE_EMAIL_ANALYZER = "analyze_email"
NODE_ORDER_PROCESSOR = "process_order"
NODE_INQUIRY_RESPONDER = "process_inquiry"
NODE_RESPONSE_COMPOSER = "compose_response"

# --- Conditional Routing Function ---
def route_by_classification(state: Dict[str, Any]) -> str:
    """
    Determines the next node based on the email classification.

    Args:
        state: The current HermesState dictionary.

    Returns:
        The name of the next node to execute ("process_order" or "process_inquiry").
    """
    print("--- Routing by Classification --- ")
    email_analysis = state.get("email_analysis_output")
    
    if email_analysis and isinstance(email_analysis, dict):
        classification = email_analysis.get("classification")
        print(f"Classification found: {classification}")
        if classification == "order_request":
            return NODE_ORDER_PROCESSOR
        elif classification == "product_inquiry":
            return NODE_INQUIRY_RESPONDER
        else:
            # Handle unexpected classification - maybe route to a clarification step or end
            print(f"Warning: Unexpected classification '{classification}'. Routing to response composer as default fallback.")
            # Or raise an error, or route to a specific error handling node
            return NODE_RESPONSE_COMPOSER # Fallback: go directly to composer if classification is weird
    else:
        print("Warning: Email analysis output not found or invalid in state. Cannot route by classification. Routing to response composer as fallback.")
        # Fallback if analysis failed
        return NODE_RESPONSE_COMPOSER 

# --- Build the StateGraph --- 

def create_hermes_workflow() -> StateGraph:
    """
    Creates and configures the LangGraph StateGraph for the Hermes pipeline.
    """
    # Use the actual HermesState TypedDict when imports are resolved
    # workflow = StateGraph(HermesState)
    workflow = StateGraph(PlaceholderHermesState) 

    # Add nodes: Map node names to agent functions
    # These functions will be partial-ed with their specific dependencies (llm, tools, prompts) 
    # when the graph is actually invoked or compiled with context.
    workflow.add_node(NODE_EMAIL_ANALYZER, analyze_email_node) # Needs llm, config
    workflow.add_node(NODE_ORDER_PROCESSOR, order_processor_agent_node) # Needs tools, config
    workflow.add_node(NODE_INQUIRY_RESPONDER, inquiry_responder_agent_node) # Needs llm, vector_store, tools, config
    workflow.add_node(NODE_RESPONSE_COMPOSER, response_composer_agent_node) # Needs llm, prompt, config

    # Define edges and entry point
    workflow.set_entry_point(NODE_EMAIL_ANALYZER)

    # Conditional edge from Email Analyzer based on classification
    workflow.add_conditional_edges(
        NODE_EMAIL_ANALYZER,
        route_by_classification,
        {
            NODE_ORDER_PROCESSOR: NODE_ORDER_PROCESSOR,
            NODE_INQUIRY_RESPONDER: NODE_INQUIRY_RESPONDER,
            NODE_RESPONSE_COMPOSER: NODE_RESPONSE_COMPOSER # Add fallback route directly to composer
        }
    )

    # Edges from Order Processor and Inquiry Responder to Response Composer
    workflow.add_edge(NODE_ORDER_PROCESSOR, NODE_RESPONSE_COMPOSER)
    workflow.add_edge(NODE_INQUIRY_RESPONDER, NODE_RESPONSE_COMPOSER)

    # Final edge from Response Composer to the end state
    workflow.add_edge(NODE_RESPONSE_COMPOSER, END)
    
    return workflow

# Compile the graph (compilation happens when you call .compile()) 
# hermes_workflow_graph = create_hermes_workflow()
# # You need a checkpointer for memory/persistence, e.g., MemorySaver
# # from langgraph.checkpoint.memory import MemorySaver
# # memory = MemorySaver()
# # compiled_hermes_workflow = hermes_workflow_graph.compile(checkpointer=memory)
# print("Hermes workflow graph created.")

""" {cell}
### Notes on Pipeline Implementation:

-   **StateGraph**: The core is `langgraph.graph.StateGraph`, initialized with the `HermesState` TypedDict.
-   **Nodes**: Each primary agent function (`analyze_email_node`, `order_processor_agent_node`, `inquiry_responder_agent_node`, `response_composer_agent_node`) is added as a node to the graph using `workflow.add_node()`.
    -   **Dependency Injection**: Note that the node functions require dependencies like `llm`, `config`, `tools`, `vector_store`, `prompts`. These dependencies are *not* passed during graph definition (`add_node`). They need to be injected when the graph is *executed* or compiled with context. This is often done using `functools.partial` or by passing them via the `RunnableConfig` when invoking the compiled graph.
-   **Entry Point**: `workflow.set_entry_point(NODE_EMAIL_ANALYZER)` defines where the execution begins.
-   **Conditional Routing**: `workflow.add_conditional_edges(...)` is used after the `Email Analyzer`. It calls the `route_by_classification` function, which inspects the state (`email_analysis_output.classification`) and returns the name of the next node (`NODE_ORDER_PROCESSOR` or `NODE_INQUIRY_RESPONDER`). The dictionary maps the return value of the routing function to the target node name. Includes a fallback route directly to the composer for unexpected classifications or errors.
-   **Linear Edges**: `workflow.add_edge(...)` defines the standard flow after the order/inquiry processing branches – both lead to the `Response Composer`.
-   **End**: The final edge connects the `Response Composer` to the special `END` node, signifying the completion of the workflow for that input.
-   **Compilation**: The graph definition (`StateGraph`) is compiled into an executable `CompiledGraph` using `workflow.compile()`. This step often includes setting up a `checkpointer` (like `MemorySaver`) if state persistence or resumption is needed.
-   **Placeholders**: This file currently uses placeholder imports and dummy agent node functions. **These must be replaced with the actual imports from `src.state` and `src.agents` once those modules are correctly placed and structured within the project.**

This structure defines the complete control flow for processing an email through the Hermes multi-agent system.
""" 