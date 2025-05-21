#!/usr/bin/env python
"""
StateGraph-based workflow for Hermes agent system using LangGraph.

This module defines the agent flow for processing customer emails:
1. Email Analyzer to classify and segment the email
2. Conditional routing to Order Processor and/or Inquiry Responder
3. Response Composer for generating the final response

The workflow is implemented as a LangGraph StateGraph.
"""

from typing import (
    List,
)
from typing_extensions import Hashable

# LangGraph imports
from langgraph.graph import StateGraph
from langgraph.constants import END, START
from langchain_core.runnables import RunnableConfig
# Import agent models
from src.hermes.agents.email_analyzer.models import (
    EmailAnalyzerInput,
)
from src.hermes.config import HermesConfig

# Import agent functions directly
from src.hermes.agents.email_analyzer.analyze_email import analyze_email
from src.hermes.agents.order_processor.process_order import process_order
from src.hermes.agents.inquiry_responder.respond_to_inquiry import respond_to_inquiry
from src.hermes.agents.response_composer.compose_response import compose_response
from src.hermes.model import Nodes

from src.hermes.agents.workflow.states import OverallState

# Conditional Logic Functions
def route_analysis_result(
    state: OverallState,
) -> List[Hashable] | Hashable:
    """Determine the next node in the workflow based on the current state."""
    print("\nExecuting route_analysis_result...")
    errors = getattr(state, "errors", None)
    email_analyzer = getattr(state, "email_analyzer", None)
    
    print(f"Inside route_analysis_result: errors={bool(errors)}, email_analyzer={email_analyzer is not None}")
    if not errors and email_analyzer is not None:
        email_analysis = email_analyzer.email_analysis
        
        email_has_order = email_analysis.has_order()
        email_has_inquiry = email_analysis.has_inquiry()

        print(f"\nRouting Decision:\n email_has_order: {email_has_order}\n email_has_inquiry: {email_has_inquiry}")

        return \
          [Nodes.PROCESS, Nodes.ANSWER] if email_has_order and email_has_inquiry else \
          Nodes.PROCESS if email_has_order else \
          Nodes.ANSWER if email_has_inquiry else \
          Nodes.COMPOSE
    
    return END

async def analyze_email_node(state: OverallState, config: RunnableConfig) -> dict:
    # Convert OverallState to EmailAnalyzerInput before passing to analyze_email
    email_analyzer_input = EmailAnalyzerInput(
        email_id=state.email_id,
        subject=state.subject,
        message=state.message
    )
    return await analyze_email(state=email_analyzer_input, runnable_config=config)

async def process_order_node(state: OverallState, config: RunnableConfig) -> dict:
    """
    Wrapper function for process_order that correctly extracts email_id and email_analyzer from state.
    
    Args:
        state: The workflow state containing email_analyzer output
        config: Runnable configuration for the agent
    
    Returns:
        Result from process_order function in dictionary format
    """
    # Extract email_id from state
    email_id = state.email_id
    
    # Extract email_analyzer from state - handle potential None case
    email_analyzer = state.email_analyzer
    
    if email_analyzer is None:
        # If email_analyzer is None, return an error
        from src.hermes.utils.errors import create_node_response
        from src.hermes.model import Agents
        return create_node_response(
            Agents.ORDER_PROCESSOR,
            Exception("Email analyzer output is required for order processing")
        )
    
    # Convert EmailAnalyzerOutput to dict for process_order
    if hasattr(email_analyzer, "model_dump"):
        email_analysis_dict = email_analyzer.model_dump()
    else:
        # Fallback if model_dump not available
        email_analysis_dict = dict(email_analyzer)
    
    # Call process_order with the extracted information
    processed_order = process_order(
        email_analysis=email_analysis_dict,
        email_id=email_id,
        hermes_config=HermesConfig.from_runnable_config(config),
    )
    
    # Convert the result to a dictionary for LangGraph
    from src.hermes.utils.errors import create_node_response
    from src.hermes.model import Agents
    from hermes.agents.order_processor.models.agent import OrderProcessorOutput
    
    # Create the expected output type
    order_processor_output = OrderProcessorOutput(order_result=processed_order)
    
    # Return in the format expected by LangGraph
    return create_node_response(Agents.ORDER_PROCESSOR, order_processor_output)

# Build the graph
graph_builder = StateGraph(OverallState, input=EmailAnalyzerInput, config_schema=HermesConfig)

# Add nodes with the agent functions directly, specifying that they expect runnable_config
graph_builder.add_node(
    Nodes.ANALYZE,
    analyze_email_node
)
graph_builder.add_node(
    Nodes.PROCESS, 
    process_order_node,  # Use the wrapper function to correctly pass email_id
)
graph_builder.add_node(
    Nodes.ANSWER, 
    respond_to_inquiry,
)
graph_builder.add_node(
    Nodes.COMPOSE, 
    compose_response,
)

# Add edges to create the workflow
graph_builder.add_edge(START, Nodes.ANALYZE)
graph_builder.add_conditional_edges(
    Nodes.ANALYZE,
    route_analysis_result,
    [Nodes.PROCESS, Nodes.ANSWER, Nodes.COMPOSE, END],
)
graph_builder.add_edge(Nodes.PROCESS, Nodes.COMPOSE)
graph_builder.add_edge(Nodes.ANSWER, Nodes.COMPOSE)
graph_builder.add_edge(Nodes.COMPOSE, END)

# Compile the workflow
workflow = graph_builder.compile()


