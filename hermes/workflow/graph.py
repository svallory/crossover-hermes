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
from langgraph.constants import END, START  # type: ignore

# LangGraph imports
from langgraph.graph import StateGraph

from hermes.agents.advisor.agent import run_advisor

# Import agent functions directly
from hermes.agents.classifier.agent import run_classifier

# Import agent models
from hermes.agents.composer.agent import run_composer
from hermes.agents.fulfiller.agent import run_fulfiller
from hermes.agents.stockkeeper.agent import run_stockkeeper
from hermes.agents.stockkeeper.models import StockkeeperInput
from hermes.workflow.states import OverallState, WorkflowInput, WorkflowOutput
from hermes.config import HermesConfig
from hermes.model import Nodes


def route_resolver_result(
    state: OverallState,
) -> list[Hashable] | Hashable:
    """Route after product resolution based on email intents."""
    classifier = state.classifier

    if classifier is not None:
        analysis = classifier.email_analysis

        if analysis.primary_intent == "product inquiry":
            return Nodes.ADVISOR
        elif analysis.has_inquiry():
            return [Nodes.FULFILLER, Nodes.ADVISOR]
        else:
            return Nodes.FULFILLER

    return END


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
        from hermes.model.enums import Agents
        from hermes.utils.response import create_node_response

        return create_node_response(
            Agents.STOCKKEEPER,
            Exception("Email analyzer output is required for product resolution"),
        )

    # Create StockkeeperInput from classifier
    stockkeeper_input = StockkeeperInput(email=state.email, classifier=classifier)

    # Call resolve_product_mentions with the StockkeeperInput
    return await run_stockkeeper(state=stockkeeper_input, runnable_config=config)


# Build the graph
graph_builder = StateGraph(
    input=WorkflowInput,
    output=WorkflowOutput,
    state_schema=OverallState,
    config_schema=HermesConfig,
)

# Add nodes with the agent functions directly, specifying that they expect runnable_config
graph_builder.add_node(Nodes.CLASSIFIER, run_classifier)
graph_builder.add_node(Nodes.STOCKKEEPER, run_stockkeeper)
graph_builder.add_node(
    Nodes.FULFILLER,
    run_fulfiller,
)
graph_builder.add_node(
    Nodes.ADVISOR,
    run_advisor,
)
graph_builder.add_node(
    Nodes.COMPOSER,
    run_composer,
)

# Add edges to create the workflow
graph_builder.add_edge(START, Nodes.CLASSIFIER)
graph_builder.add_edge(Nodes.CLASSIFIER, Nodes.STOCKKEEPER)

graph_builder.add_conditional_edges(
    Nodes.STOCKKEEPER,
    route_resolver_result,
    [Nodes.FULFILLER, Nodes.ADVISOR, END],
)
graph_builder.add_edge(Nodes.FULFILLER, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.ADVISOR, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.COMPOSER, END)

# Compile the workflow
workflow = graph_builder.compile()
