"""Main function for responding to customer inquiries."""

from __future__ import annotations

from typing import Literal
import json

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from ...config import HermesConfig
from ...model.enums import Agents
from ...workflow.types import WorkflowNodeOutput
from ...utils.response import create_node_response
from ...utils.llm_client import get_llm_client
from .models import (
    AdvisorInput,
    AdvisorOutput,
    InquiryAnswers,
)
from .prompts import ADVISOR_PROMPT
from hermes.tools.toolkits import CatalogToolkit
from hermes.utils.tool_error_handler import ToolCallRetryHandler, DEFAULT_RETRY_TEMPLATE
from hermes.utils.logger import logger, get_agent_logger


@traceable(
    run_type="chain",
    name="Advisor agent Agent",
)
async def run_advisor(
    state: AdvisorInput,
    runnable_config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.ADVISOR], AdvisorOutput]:
    """Run the advisor agent to analyze customer inquiries and provide factual responses.

    This agent extracts questions from customer emails and provides objective answers
    using the product catalog and resolved product information.

    Args:
        state: AdvisorInput containing classifier output and optional stockkeeper output
        runnable_config: Optional configuration for the runnable

    Returns:
        WorkflowNodeOutput containing the advisor's factual response
    """
    agent_name = Agents.ADVISOR.value.capitalize()
    email_id = (
        state.classifier.email_analysis.email_id
    )  # Define email_id early for context in case of error
    logger.info(
        get_agent_logger(agent_name, f"Running for email [cyan]{email_id}[/cyan]")
    )

    try:  # ADDED try block
        # Extract data from state
        email_analysis = state.classifier.email_analysis
        # email_id is already defined above
        resolved_products = (
            state.stockkeeper.resolved_products if state.stockkeeper else []
        )

        logger.debug(
            get_agent_logger(
                agent_name,
                f"  Resolved products for [cyan]{email_id}[/cyan]: [yellow]{len(resolved_products)}[/yellow]",
            )
        )

        # Get LLM instance
        llm = get_llm_client(
            config=HermesConfig.from_runnable_config(runnable_config),
            schema=InquiryAnswers,
            tools=CatalogToolkit.get_tools(),
            model_strength="strong",
            temperature=0.1,
        )

        # Prepare product context - pass raw product data as list of dicts
        product_context = []
        if resolved_products:
            for product in resolved_products:
                product_dict = (
                    product.model_dump() if hasattr(product, "model_dump") else product
                )
                product_context.append(product_dict)

        # Create the chain using LangChain composition
        inquiry_response_chain = ADVISOR_PROMPT | llm

        # Use the retry handler to handle validation errors
        retry_handler = ToolCallRetryHandler(max_retries=2, backoff_factor=0.0)

        # Prepare input data
        email_analysis_data = (
            email_analysis.model_dump()
            if hasattr(email_analysis, "model_dump")
            else email_analysis
        )

        response_data = await retry_handler.retry_with_tool_calling(
            chain=inquiry_response_chain,
            input_data={
                "email_analysis": email_analysis_data,
                "retrieved_products_context": product_context,
            },
            retry_prompt_template=DEFAULT_RETRY_TEMPLATE,
        )

        # Ensure we get the right type
        if isinstance(response_data, InquiryAnswers):
            inquiry_response = response_data
        elif isinstance(response_data, dict):
            response_data["email_id"] = email_id

            # Attempt to parse stringified metadata
            for product_list_key in ["primary_products", "related_products"]:
                if (
                    product_list_key in response_data
                    and response_data[product_list_key]
                ):
                    for product_data in response_data[product_list_key]:
                        if (
                            isinstance(product_data, dict)
                            and "metadata" in product_data
                            and isinstance(product_data["metadata"], str)
                        ):
                            try:
                                product_data["metadata"] = json.loads(
                                    product_data["metadata"]
                                )
                            except json.JSONDecodeError:
                                print(
                                    f"Warning: Could not parse metadata string for product in {product_list_key}: {product_data.get('product_id')}"
                                )
                        elif (
                            isinstance(product_data, dict)
                            and "metadata" in product_data
                            and product_data["metadata"] is None
                        ):
                            product_data["metadata"] = None

            inquiry_response = InquiryAnswers(**response_data)
        else:
            # Fallback for unexpected response type
            # This path should ideally not be hit if retry_handler works or schema is good
            error_msg = f"Unexpected response type {type(response_data)} from LLM for email [cyan]{email_id}[/cyan] after retries."
            logger.error(get_agent_logger(agent_name, error_msg))
            raise RuntimeError(f"Advisor: {error_msg}")

        # Ensure email_id is set correctly
        inquiry_response.email_id = email_id
        logger.info(
            get_agent_logger(
                agent_name,
                f"Factual response generation complete for email [cyan]{email_id}[/cyan]",
            )
        )

        return create_node_response(
            Agents.ADVISOR, AdvisorOutput(inquiry_answers=inquiry_response)
        )
    except Exception as e:  # ADDED except block
        # Removed: # print(f"Advisor: Top-level error during processing: {e}")
        error_message = f"Error in {agent_name} for email {email_id}: {e}"
        logger.error(get_agent_logger(agent_name, error_message), exc_info=True)
        raise RuntimeError(
            f"Advisor: Error during processing for email {email_id}"
        ) from e  # MODIFIED to raise with context from e
