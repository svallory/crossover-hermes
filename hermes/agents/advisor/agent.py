"""Main function for responding to customer inquiries."""

from __future__ import annotations

from typing import Literal

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
    try:
        # Extract data from state
        email_analysis = state.classifier.email_analysis
        email_id = email_analysis.email_id
        resolved_products = (
            state.stockkeeper.resolved_products if state.stockkeeper else []
        )

        print(f"Running advisor for email {email_id}")
        print(f"  Resolved products: {len(resolved_products)}")

        # Get LLM instance
        llm = get_llm_client(
            config=HermesConfig.from_runnable_config(runnable_config),
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
        inquiry_response_chain = ADVISOR_PROMPT | llm.with_structured_output(
            InquiryAnswers
        )

        try:
            # Prepare input data
            email_analysis_data = (
                email_analysis.model_dump()
                if hasattr(email_analysis, "model_dump")
                else email_analysis
            )

            # Generate the inquiry response using the chain
            response_data = await inquiry_response_chain.ainvoke(
                {
                    "email_analysis": email_analysis_data,
                    "retrieved_products_context": product_context,
                }
            )

            # Ensure we get the right type
            if isinstance(response_data, InquiryAnswers):
                inquiry_response = response_data
            elif isinstance(response_data, dict):
                response_data["email_id"] = email_id
                inquiry_response = InquiryAnswers(**response_data)
            else:
                # Fallback for unexpected response type
                inquiry_response = InquiryAnswers(
                    email_id=email_id,
                    primary_products=[],
                    answered_questions=[],
                    unanswered_questions=[
                        "Unable to process inquiry due to unexpected response type."
                    ],
                    related_products=[],
                    unsuccessful_references=[],
                )

            # Ensure email_id is set correctly
            inquiry_response.email_id = email_id

            # Log the results
            print(f"  Response generated for {email_id}")
            print(f"  Answered {len(inquiry_response.answered_questions)} questions")
            print(
                f"  Identified {len(inquiry_response.primary_products)} primary products"
            )
            print(
                f"  Suggested {len(inquiry_response.related_products)} related products"
            )

            return create_node_response(
                Agents.ADVISOR, AdvisorOutput(inquiry_answers=inquiry_response)
            )

        except Exception as e:
            print(f"Error generating inquiry response for {email_id}: {e}")

            # Create a factual fallback response
            fallback_response = InquiryAnswers(
                email_id=email_id,
                primary_products=[],
                answered_questions=[],
                unanswered_questions=["Unable to process inquiry due to system error."],
                related_products=[],
                unsuccessful_references=[],
            )

            return create_node_response(
                Agents.ADVISOR, AdvisorOutput(inquiry_answers=fallback_response)
            )

    except Exception as e:
        # Return errors in the format expected by LangGraph
        return create_node_response(Agents.ADVISOR, e)


# Note: format_resolved_products and search_vector_store functions removed
# as part of simplification - we now pass raw product data directly to LLM
