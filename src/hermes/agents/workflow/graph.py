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

# Build the graph
graph_builder = StateGraph(OverallState, input=EmailAnalyzerInput, config_schema=HermesConfig)

# Add nodes with the agent functions directly, specifying that they expect runnable_config
graph_builder.add_node(
    Nodes.ANALYZE,
    analyze_email_node
)
graph_builder.add_node(
    Nodes.PROCESS, 
    process_order,
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


