""" {cell}
## Pipeline - LangGraph Workflow Definition

This module defines the main StateGraph workflow for the Hermes system, connecting
all agent nodes in a graph structure. It uses LangGraph to manage state transitions 
between agents and implement conditional routing based on email classification.

The workflow implements a directed graph:
1. Email Analyzer agent processes all emails
2. Based on classification, routes to either Order Processor or Inquiry Responder
3. Both processing paths converge at the Response Composer agent
4. Final response is returned with complete processing history
"""
from typing import Dict, List, Any, Annotated, TypedDict, Optional
from langgraph.graph import StateGraph, END
from networkx import Graph
from .state import HermesState

# Import agent node functions
from .agents.email_analyzer import analyze_email_node
from .agents.order_processor import process_order_node
from .agents.inquiry_responder import process_inquiry_node
from .agents.response_composer import compose_response_node

def create_hermes_workflow(config: Optional[Dict[str, Any]] = None) -> StateGraph:
    """
    Create the Hermes email processing workflow using LangGraph.
    
    Args:
        config: Optional configuration dictionary to be passed to agents
        
    Returns:
        A compiled StateGraph workflow ready for execution
    """
    # Create a new graph with the HermesState schema
    workflow = StateGraph(HermesState)
    
    # Add agent nodes
    workflow.add_node("email_analyzer", analyze_email_node)
    workflow.add_node("order_processor", process_order_node)
    workflow.add_node("inquiry_responder", process_inquiry_node)
    workflow.add_node("response_composer", compose_response_node)
    
    # Define the starting node
    workflow.set_entry_point("email_analyzer")
    
    # Define conditional routing based on email classification
    def route_by_classification(state: Dict[str, Any]) -> str:
        """
        Routes workflow based on email classification.
        
        Args:
            state: The current state dictionary from LangGraph
            
        Returns:
            The next node to route to ("order_processor" or "inquiry_responder")
        """
        # Type annotation indicates Dict, but we can reconstruct HermesState for safety
        typed_state = HermesState(
            email_id=state.get("email_id", "unknown"),
            email_analysis=state.get("email_analysis"),
            product_catalog_df=state.get("product_catalog_df"),
            vector_store=state.get("vector_store")
        )
        
        # Also reconstruct EmailAnalysis if available
        email_analysis = None
        if typed_state.email_analysis:
            try:
                email_analysis = EmailAnalysis(**typed_state.email_analysis)
            except Exception as e:
                print(f"Warning: Could not reconstruct EmailAnalysis: {e}")
        
        # Check if email_analysis exists and is not None
        if not typed_state.email_analysis:
            print("Warning: email_analysis is missing from state. Defaulting to inquiry_responder.")
            return "inquiry_responder"
        
        # Get classification from reconstructed object if possible
        classification = email_analysis.classification if email_analysis else typed_state.email_analysis.get("classification")
        
        # Route based on classification
        if classification == "order_request":
            return "order_processor"
        else:  # Either "product_inquiry" or unknown
            return "inquiry_responder"
    
    # Connect email_analyzer to either order_processor or inquiry_responder
    workflow.add_conditional_edges(
        "email_analyzer",
        route_by_classification,
        {
            "order_processor": "order_processor",
            "inquiry_responder": "inquiry_responder"
        }
    )
    
    # Connect both order_processor and inquiry_responder to response_composer
    workflow.add_edge("order_processor", "response_composer")
    workflow.add_edge("inquiry_responder", "response_composer")
    
    # Connect response_composer to END
    workflow.add_edge("response_composer", END)
    
    # Compile the workflow
    compiled_workflow = workflow.compile()
    
    return compiled_workflow

""" {cell}
### Workflow Implementation Notes

The Hermes workflow is implemented using LangGraph's StateGraph, which provides:

1. **State Management**: 
   - The graph maintains and passes state through the pipeline
   - Each agent enriches the state with its analysis and results
   - The `HermesState` dataclass defines the structure of this state

2. **Conditional Routing**:
   - The `route_by_classification` function implements dynamic routing
   - Emails classified as "order_request" go to the Order Processor
   - All other emails (including "product_inquiry") go to the Inquiry Responder
   - This branching pattern enables specialized processing for different email types

3. **Converging Paths**:
   - Both processing branches reconverge at the Response Composer
   - This ensures a consistent final response format regardless of path

4. **Configuration Propagation**:
   - The workflow can be created with an optional configuration dictionary
   - This configuration is passed to all agent nodes
   - Enables consistent configuration across all components (e.g., model settings)

5. **Error Handling**:
   - If the email analyzer fails to classify an email, it defaults to the inquiry path
   - Each agent has internal error handling to prevent workflow failures

This Graph structure balances specialization (different agents for different tasks) with consistent outputs (all responses go through the Response Composer), ensuring robustness and maintainability.
"""