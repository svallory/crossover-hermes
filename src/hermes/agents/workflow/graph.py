#!/usr/bin/env python
"""StateGraph-based workflow for Hermes agent system using LangGraph.

This module defines the agent flow for processing customer emails:
1. Classifier agent to classify and segment the email
2. Stockkeeper to resolve product mentions to catalog products
3. Conditional routing to Fulfiller agent and/or Advisor agent
4. Composer agent for generating the final response

The workflow is implemented as a LangGraph StateGraph.
"""


from collections.abc import Hashable

from langchain_core.runnables import RunnableConfig
from langgraph.constants import END, START

# LangGraph imports
from langgraph.graph import StateGraph

from src.hermes.agents.advisor.agent import respond_to_inquiry

# Import agent functions directly
from src.hermes.agents.classifier.agent import analyze_email

# Import agent models
from src.hermes.agents.classifier.models import (
    ClassifierInput,
)
from src.hermes.agents.composer.agent import compose_response
from src.hermes.agents.fulfiller.agent import process_order
from src.hermes.agents.stockkeeper.agent import resolve_product_mentions
from src.hermes.agents.stockkeeper.models import StockkeeperInput
from src.hermes.agents.workflow.states import OverallState
from src.hermes.config import HermesConfig
from src.hermes.model import Nodes

def route_resolver_result(
    state: OverallState,
) -> list[Hashable] | Hashable:
    """Route after product resolution based on email intents."""
    classifier = state.classifier

    if classifier is not None:
        analysis = classifier.email_analysis

        return (
            Nodes.ADVISOR
            if analysis.primary_intent == "product inquiry"
            else [Nodes.FULFILLER, Nodes.ADVISOR]
            if analysis.has_inquiry()
            else Nodes.FULFILLER
        )

    return END


async def analyze_email_node(state: OverallState, config: RunnableConfig) -> dict:
    # Convert OverallState to ClassifierInput before passing to analyze_email
    classifier_input = ClassifierInput(email_id=state.email_id, subject=state.subject, message=state.message)
    return await analyze_email(state=classifier_input, runnable_config=config)


async def resolve_products_node(state: OverallState, config: RunnableConfig) -> dict:
    """Wrapper function for resolve_product_mentions that passes the classifier output.

    Args:
        state: The workflow state containing classifier output
        config: Runnable configuration for the agent

    Returns:
        Result from resolve_product_mentions function

    """
    # Extract classifier from state
    classifier = state.classifier

    if classifier is None:
        # If classifier is None, return an error
        from src.hermes.model.enums import Agents
        from src.hermes.utils.errors import create_node_response

        return create_node_response(
            Agents.STOCKKEEPER, Exception("Email analyzer output is required for product resolution")
        )

    # Create StockkeeperInput from classifier
    stockkeeper_input = StockkeeperInput(classifier=classifier)

    # Call resolve_product_mentions with the StockkeeperInput
    return await resolve_product_mentions(state=stockkeeper_input, runnable_config=config)


async def process_order_node(state: OverallState, config: RunnableConfig) -> dict:
    """Wrapper function for process_order that correctly extracts email_id and classifier from state.

    Args:
        state: The workflow state containing classifier output
        config: Runnable configuration for the agent

    Returns:
        Result from process_order function in dictionary format

    """
    # Extract email_id from state
    email_id = state.email_id

    # Extract classifier from state - handle potential None case
    classifier = state.classifier
    stockkeeper_output_data = state.stockkeeper

    if classifier is None or stockkeeper_output_data is None:
        # If classifier or stockkeeper_output is None, return an error
        from src.hermes.model import Agents
        from src.hermes.utils.errors import create_node_response

        error_message = "Email analyzer output is required for order processing" \
                        if classifier is None else "Stockkeeper output is required for order processing"
        return create_node_response(Agents.FULFILLER, Exception(error_message))

    # Get resolved products if available
    # resolved_products = state.stockkeeper.resolved_products if state.stockkeeper else [] # No longer directly needed here
    # unresolved_mentions = state.stockkeeper.unresolved_mentions if state.stockkeeper else [] # No longer directly needed here

    # Convert ClassifierOutput to dict for process_order
    if hasattr(classifier, "model_dump"):
        email_analysis_dict = classifier.model_dump()
    else:
        # Fallback if model_dump not available
        email_analysis_dict = dict(classifier)

    # Add resolved products to the email analysis dict (process_order expects this within email_analysis)
    # This was how it was previously, but process_order signature is (email_analysis, stockkeeper_output, ...)
    # email_analysis_dict["resolved_products"] = resolved_products
    # email_analysis_dict["unresolved_mentions"] = unresolved_mentions

    hermes_config_instance = HermesConfig.from_runnable_config(config)
    promotion_specs_data = hermes_config_instance.promotion_specs

    # Call process_order with the extracted information
    processed_order_result = process_order(
        email_analysis=email_analysis_dict, # This should be the raw classifier output / email analysis part
        stockkeeper_output=stockkeeper_output_data, # Pass the full StockkeeperOutput
        promotion_specs=promotion_specs_data,
        email_id=email_id,
        hermes_config=hermes_config_instance,
    )

    # Convert the result to a dictionary for LangGraph
    from src.hermes.agents.fulfiller.models import FulfillerOutput
    from src.hermes.model import Agents
    from src.hermes.utils.errors import create_node_response

    # Create the expected output type
    fulfiller_output_response = FulfillerOutput(order_result=processed_order_result)

    # Return in the format expected by LangGraph
    return create_node_response(Agents.FULFILLER, fulfiller_output_response)


# Build the graph
graph_builder = StateGraph(OverallState, input=ClassifierInput, config_schema=HermesConfig)

# Add nodes with the agent functions directly, specifying that they expect runnable_config
graph_builder.add_node(Nodes.CLASSIFIER, analyze_email_node)
graph_builder.add_node(Nodes.STOCKKEEPER, resolve_products_node)
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
