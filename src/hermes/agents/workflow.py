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
    Any,
    Literal,
    Optional,
    Protocol,
    Sequence,
    TypedDict,
    Union,
    TypeVar,
    Annotated,
)
from enum import Enum
import operator

# LangGraph imports
from langgraph.graph import StateGraph, END, START
from langchain_core.runnables import RunnableConfig
from pydantic import Field

# Import agent functions
from src.hermes.agents.email_analyzer import (
    analyze_email,
    EmailAnalysis,
    EmailAnalyzerOutput,
    EmailAnalyzerInput,
)
from src.hermes.agents.order_processor import (
    process_order,
    OrderProcessorInput,
    OrderProcessorOutput,
    ProcessedOrder,
)
from src.hermes.agents.inquiry_responder import (
    respond_to_inquiry,
    InquiryResponderInput,
    InquiryResponderOutput,
    InquiryAnswers,
)
from src.hermes.agents.response_composer import (
    compose_response,
    ResponseComposerInput,
    ResponseComposerOutput,
    ComposedResponse,
)
from src.hermes.config import HermesConfig


def merge_errors(dict1, dict2):
    """Merge two error dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


class InputState(EmailAnalyzerInput):
    """Input state for the Hermes workflow."""

    email_id: str = Field(default="E900")
    subject: Optional[str] = Field(
        default="Leather Wallets", description="Subject of the email"
    )
    message: str = Field(
        default="Hey, hope you're doing well. Last year for my birthday, my wife Emily got me a really nice leather briefcase from your store. I loved it and used it every day for work until the strap broke a few months ago. Speaking of broken things, I also need to get my lawnmower fixed before spring. Anyway, what were some of the other messenger bag or briefcase style options you have? I could go for something slightly smaller than my previous one. Oh and we also need to make dinner reservations for our anniversary next month. Maybe a nice Italian place downtown. What was I saying again? Oh right, work bags! Let me know what you'd recommend. Thanks!"
    )


class AnalyzedState(InputState):
    """WorkflowOutputState with required email analysis"""

    email_analyzer: EmailAnalyzerOutput


class ProcessedState(AnalyzedState):
    """AnalyzedState with required order"""

    order_processor: OrderProcessorOutput


class AnsweredState(AnalyzedState):
    """AnalyzedState with required inquiry answers"""

    inquiry_responder: InquiryResponderOutput


class OutputState(AnalyzedState):
    """Final state with composed response"""

    response_composer: ResponseComposerOutput
    order_processor: Optional[OrderProcessorOutput] = None
    inquiry_responder: Optional[InquiryResponderOutput] = None


class OverallState(InputState):
    """Overall state that can contain any combination of analysis, processing, and response"""

    email_analyzer: Optional[EmailAnalyzerOutput]
    order_processor: Optional[OrderProcessorOutput]
    inquiry_responder: Optional[InquiryResponderOutput]
    response_composer: Optional[ResponseComposerOutput]
    errors: Annotated[Dict[str, str], merge_errors]


class ErrorState(OverallState):
    """OverallState with required errors"""

    errors: Annotated[Dict[str, str], merge_errors]


# Node Functions
async def analyze_email_node(
    state: InputState, config: RunnableConfig
) -> Dict[str, Any]:
    """Node for Email Analyzer agent."""
    try:
        result = await analyze_email(state, config)
        return {"email_analyzer": result}
        # return {}
    except Exception as e:
        return {"errors": {"email_analyzer": str(e)}}


async def process_order_node(
    state: AnalyzedState, config: RunnableConfig
) -> Dict[str, Any]:
    """Node for Order Processor agent."""
    try:
        email_analyzer = getattr(state, "email_analyzer", None)

        if not email_analyzer or not hasattr(email_analyzer, "email_analysis"):
            return {
                "errors": {
                    "order_processor": "No email analysis available for order processing."
                }
            }

        # Create a proper OrderProcessorInput from the state
        email_analysis = email_analyzer.email_analysis
        # Convert to dict if it's not already
        if not isinstance(email_analysis, dict):
            email_analysis = (
                email_analysis.dict()
                if hasattr(email_analysis, "dict")
                else vars(email_analysis)
            )

        order_input = OrderProcessorInput(
            email_id=state.email_id, email_analysis=email_analysis
        )

        result = await process_order(order_input, config)
        return {"order_processor": result}

    except Exception as e:
        return {"errors": {"order_processor": str(e)}}


async def respond_to_inquiry_node(
    state: AnalyzedState, config: RunnableConfig
) -> Dict[str, Any]:
    """Node for Inquiry Responder agent."""
    try:
        email_analysis = getattr(state, "email_analysis", None)
        if not email_analysis:
            return {
                "errors": {
                    "inquiry_responder": "No email analysis available for inquiry response."
                }
            }

        inquiry_input = InquiryResponderInput(email_analysis=email_analysis)

        inquiry_output = await respond_to_inquiry(inquiry_input, config)
        return {"inquiry_responder": inquiry_output}
    except Exception as e:
        return {"errors": {"inquiry_responder": str(e)}}


async def compose_response_node(
    state: AnalyzedState, config: RunnableConfig
) -> Dict[str, Any]:
    """Node for Response Composer agent."""
    try:
        email_analysis = getattr(state, "email_analysis", None)
        if not email_analysis:
            return {
                "errors": {
                    "response_composer": "No email analysis available for response composition."
                }
            }

        composer_input = ResponseComposerInput(
            email_analysis=email_analysis,
            inquiry_response=getattr(state, "inquiry_response", None),
            order_result=getattr(state, "order_result", None),
        )

        response_output = await compose_response(composer_input, config)
        return {"response_composer": response_output}
    except Exception as e:
        return {"errors": {"response_composer": str(e)}}


# Enum of nodes
class Nodes(str, Enum):
    ANALYZE_EMAIL = "analyze_email"
    PROCESS_ORDER = "process_order"
    RESPOND_TO_INQUIRY = "respond_to_inquiry"
    COMPOSE_RESPONSE = "compose_response"
    END = END


# Conditional Logic Functions
def route_analysis_result(
    state: Union[AnalyzedState, ErrorState],
) -> Union[
    Sequence[Literal[Nodes.PROCESS_ORDER, Nodes.RESPOND_TO_INQUIRY]],
    Literal[
        Nodes.PROCESS_ORDER, Nodes.RESPOND_TO_INQUIRY, Nodes.COMPOSE_RESPONSE, Nodes.END
    ],
]:
    """Determine the next node in the workflow based on the current state."""
    errors = getattr(state, "errors", None)
    email_analyzer = getattr(state, "email_analyzer", None)
    if errors is None and email_analyzer is not None:
        email_analysis = email_analyzer.email_analysis
        if isinstance(email_analysis, dict):
            email_analysis = EmailAnalysis(**email_analysis)
        email_has_order = email_analysis.has_order()
        email_has_inquiry = email_analysis.has_inquiry()
        return (
            [Nodes.PROCESS_ORDER, Nodes.RESPOND_TO_INQUIRY]
            if email_has_order and email_has_inquiry
            else Nodes.PROCESS_ORDER
            if email_has_order
            else Nodes.RESPOND_TO_INQUIRY
            if email_has_inquiry
            else Nodes.COMPOSE_RESPONSE
        )
    return Nodes.END


# Build the graph
graph_builder = StateGraph(
    OverallState, input=InputState, output=OutputState, config_schema=HermesConfig
)

graph_builder.add_node(Nodes.ANALYZE_EMAIL, analyze_email_node)
graph_builder.add_node(Nodes.PROCESS_ORDER, process_order_node)
graph_builder.add_node(Nodes.RESPOND_TO_INQUIRY, respond_to_inquiry_node)
graph_builder.add_node(Nodes.COMPOSE_RESPONSE, compose_response_node)

graph_builder.add_edge(START, Nodes.ANALYZE_EMAIL)
graph_builder.add_conditional_edges(Nodes.ANALYZE_EMAIL, route_analysis_result)
graph_builder.add_edge(Nodes.PROCESS_ORDER, Nodes.COMPOSE_RESPONSE)
graph_builder.add_edge(Nodes.RESPOND_TO_INQUIRY, Nodes.COMPOSE_RESPONSE)
graph_builder.add_edge(Nodes.COMPOSE_RESPONSE, END)

workflow = graph_builder.compile()


async def hermes_langgraph_workflow(
    input_state: InputState,
    hermes_config: HermesConfig,
) -> OutputState:
    """
    LangGraph-based workflow for the Hermes agent system.

    Args:
        email_data: Dictionary containing email_id, email_subject, and email_message
        hermes_config: HermesConfig object for agent configurations

    Returns:
        The final workflow state after processing through the graph.
    """

    # Invoke the graph with the initial state and configuration
    result = await workflow.ainvoke(
        input_state, config=hermes_config.as_runnable_config()
    )

    return OutputState(**result)
