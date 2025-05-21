#!/usr/bin/env python
"""
StateGraph-based workflow for Hermes agent system using LangGraph.

This module defines the agent flow for processing customer emails:
1. Email Analyzer to classify and segment the email
2. Product Resolver to resolve product mentions to catalog products
3. Conditional routing to Order Processor and/or Inquiry Responder
4. Response Composer for generating the final response

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
from src.hermes.agents.classifier.models import (
    EmailAnalyzerInput,
    EmailAnalyzerOutput,
)
from src.hermes.config import HermesConfig

# Import agent functions directly
from src.hermes.agents.classifier.agent import analyze_email
from src.hermes.agents.product_resolver.resolve_products import resolve_product_mentions
from src.hermes.agents.fulfiller.agent import process_order
from src.hermes.agents.advisor.agent import respond_to_inquiry
from src.hermes.agents.response_composer.compose_response import compose_response
from src.hermes.model import Nodes

from src.hermes.agents.workflow.states import OverallState

def route_resolver_result(
    state: OverallState,
) -> List[Hashable] | Hashable:
    """Route after product resolution based on email intents."""
    
    email_analyzer = state.email_analyzer
    
    if email_analyzer is not None:
        analysis = email_analyzer.email_analysis

        return \
          Nodes.ADVISOR if analysis.primary_intent is "product inquiry" else \
          [Nodes.FULFILLER, Nodes.ADVISOR] if analysis.has_inquiry() else \
          Nodes.FULFILLER
    
    return END

async def analyze_email_node(state: OverallState, config: RunnableConfig) -> dict:
    # Convert OverallState to EmailAnalyzerInput before passing to analyze_email
    email_analyzer_input = EmailAnalyzerInput(
        email_id=state.email_id,
        subject=state.subject,
        message=state.message
    )
    return await analyze_email(state=email_analyzer_input, runnable_config=config)

async def resolve_products_node(state: OverallState, config: RunnableConfig) -> dict:
    """
    Wrapper function for resolve_product_mentions that passes the email_analyzer output.
    
    Args:
        state: The workflow state containing email_analyzer output
        config: Runnable configuration for the agent
    
    Returns:
        Result from resolve_product_mentions function
    """
    # Extract email_analyzer from state
    email_analyzer = state.email_analyzer
    
    if email_analyzer is None:
        # If email_analyzer is None, return an error
        from src.hermes.utils.errors import create_node_response
        from src.hermes.model.enums import Agents
        return create_node_response(
            Agents.PRODUCT_RESOLVER,
            Exception("Email analyzer output is required for product resolution")
        )
    
    # Call resolve_product_mentions with the email analyzer output
    return await resolve_product_mentions(
        state=email_analyzer,
        runnable_config=config
    )

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
    
    # Get resolved products if available
    resolved_products = state.product_resolver.resolved_products if state.product_resolver else []
    unresolved_mentions = state.product_resolver.unresolved_mentions if state.product_resolver else []
    
    # Convert EmailAnalyzerOutput to dict for process_order
    if hasattr(email_analyzer, "model_dump"):
        email_analysis_dict = email_analyzer.model_dump()
    else:
        # Fallback if model_dump not available
        email_analysis_dict = dict(email_analyzer)
    
    # Add resolved products to the email analysis dict
    email_analysis_dict["resolved_products"] = resolved_products
    email_analysis_dict["unresolved_mentions"] = unresolved_mentions
    
    # Call process_order with the extracted information
    processed_order = process_order(
        email_analysis=email_analysis_dict,
        email_id=email_id,
        hermes_config=HermesConfig.from_runnable_config(config),
    )
    
    # Convert the result to a dictionary for LangGraph
    from src.hermes.utils.errors import create_node_response
    from src.hermes.model import Agents
    from hermes.agents.fulfiller.models.agent import OrderProcessorOutput
    
    # Create the expected output type
    order_processor_output = OrderProcessorOutput(order_result=processed_order)
    
    # Return in the format expected by LangGraph
    return create_node_response(Agents.ORDER_PROCESSOR, order_processor_output)

# Build the graph
graph_builder = StateGraph(OverallState, input=EmailAnalyzerInput, config_schema=HermesConfig)

# Add nodes with the agent functions directly, specifying that they expect runnable_config
graph_builder.add_node(
    Nodes.CLASSIFIER,
    analyze_email_node
)
graph_builder.add_node(
    Nodes.STOCKKEEPER,
    resolve_products_node
)
graph_builder.add_node(
    Nodes.FULFILLER, 
    process_order_node,
)
graph_builder.add_node(
    Nodes.ADVISOR, 
    respond_to_inquiry,
)
graph_builder.add_node(
    Nodes.COMPOSER, 
    compose_response,
)

# Add edges to create the workflow
graph_builder.add_edge(START, Nodes.CLASSIFIER)
graph_builder.add_edge(Nodes.CLASSIFIER, Nodes.STOCKKEEPER)

# graph_builder.add_conditional_edges(
#     Nodes.ANALYZE,
#     lambda state: END if len(state.errors.keys()) > 0 else Nodes.PROCESS,
#     [Nodes.RESOLVE, END],
# )

graph_builder.add_conditional_edges(
    Nodes.STOCKKEEPER,
    route_resolver_result,
    [Nodes.FULFILLER, Nodes.ADVISOR],
)
graph_builder.add_edge(Nodes.FULFILLER, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.ADVISOR, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.COMPOSER, END)

# Compile the workflow
workflow = graph_builder.compile()


