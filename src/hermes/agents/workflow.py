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
    Dict,
    Optional,
    Annotated,
    List,
)
from pydantic import Field
from typing_extensions import Hashable

# LangGraph imports
from langchain_core.runnables.utils import ConfigurableFieldSpec
from langgraph.graph import StateGraph
from langgraph.constants import END, START
from langchain_core.runnables import RunnableConfig
# Import agent models
from src.hermes.agents.email_analyzer.models import (
    EmailAnalysis,
    EmailAnalyzerInput,
    EmailAnalyzerOutput,
)
from src.hermes.agents.order_processor.models import (
    OrderProcessorOutput,
)
from src.hermes.agents.inquiry_responder.models import (
    InquiryResponderOutput,
)
from src.hermes.agents.response_composer.models import (
    ResponseComposerOutput,
)
from src.hermes.config import HermesConfig

# Import agent functions directly
from src.hermes.agents.email_analyzer.analyze_email import analyze_email
from src.hermes.agents.order_processor.process_order import process_order
from src.hermes.agents.inquiry_responder.respond_to_inquiry import respond_to_inquiry
from src.hermes.agents.response_composer.compose_response import compose_response
from src.hermes.model import Agents, Error, Nodes

def merge_errors(dict1, dict2):
    """Merge two error dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


class OverallState(EmailAnalyzerInput):
    """Overall state that can contain any combination of analysis, processing, and response"""

    email_analyzer: Optional[EmailAnalyzerOutput] = None
    order_processor: Optional[OrderProcessorOutput] = None
    inquiry_responder: Optional[InquiryResponderOutput] = None
    response_composer: Optional[ResponseComposerOutput] = None
    errors: Annotated[Dict[Agents, Error], merge_errors] = Field(default_factory=dict)


# Conditional Logic Functions
def route_analysis_result(
    state: OverallState,
) -> List[Hashable] | Hashable:
    """Determine the next node in the workflow based on the current state."""
    errors = getattr(state, "errors", None)
    email_analyzer = getattr(state, "email_analyzer", None)
    
    if errors is None and email_analyzer is not None:
        if email_analyzer is not None:
            email_analysis = email_analyzer.email_analysis
            
            if isinstance(email_analysis, dict):
                email_analysis = EmailAnalysis(**email_analysis)
            
            email_has_order = email_analysis.has_order()
            email_has_inquiry = email_analysis.has_inquiry()

            return \
              [Nodes.PROCESS, Nodes.ANSWER] if email_has_order and email_has_inquiry else \
              Nodes.PROCESS if email_has_order else \
              Nodes.ANSWER if email_has_inquiry else \
              Nodes.COMPOSE
    
    return END

async def analyze_email_node(state: OverallState, config: RunnableConfig) -> dict:
    return await analyze_email(state, config) # type: ignore

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


async def hermes_langgraph_workflow(
    input_state: EmailAnalyzerInput,
    hermes_config: HermesConfig,
) -> OverallState:
    """
    LangGraph-based workflow for the Hermes agent system.

    Args:
        input_state: Input state containing email_id, subject, and message
        hermes_config: HermesConfig object for agent configurations

    Returns:
        The final workflow state after processing through the graph.
    """

    # Invoke the graph with the initial state and configuration
    result = await workflow.ainvoke(input_state, config=hermes_config.as_runnable_config())

    return OverallState(**result)
