"""Main function for composing final customer responses."""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langsmith import traceable

from hermes.utils.response import create_node_response

from ...config import HermesConfig
from ...model.enums import Agents
from ...workflow.types import WorkflowNodeOutput
from ...utils.llm_client import get_llm_client
from ...tools.catalog_tools import (
    find_complementary_products,
    find_products_for_occasion,
)
from .models import (
    ComposerInput,
    ComposerOutput,
)
from .prompts import COMPOSER_PROMPT

# We don't want to make ALL catalog tools available to the composer agent
ComposerToolkit: list[BaseTool] = [
    find_complementary_products,  # For suggesting additional items
    find_products_for_occasion,  # For occasion-based suggestions
]


@traceable(run_type="chain", name="Composer agent Agent")  # type: ignore
async def run_composer(
    state: ComposerInput,
    runnable_config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.COMPOSER], ComposerOutput]:
    """Composes a natural, personalized customer email response by combining information
    from the Classifier agent, Advisor agent, and Fulfiller agent agents.

    Args:
        state: The validated ComposerInput containing outputs from previous agents
        runnable_config: Optional config dict with HermesConfig instance

    Returns:
        WorkflowNodeOutput containing the composed response or error

    """
    try:
        # LangGraph ensures ComposerInput is properly validated with required fields
        email_analysis = state.classifier.email_analysis
        email_id = state.email.email_id

        print(f"Composing final customer response for email {email_id}")

        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        # Use a strong model for natural language generation
        llm = get_llm_client(
            config=hermes_config,
            schema=ComposerOutput,
            tools=ComposerToolkit,
            model_strength="strong",
            temperature=0.7,
        )

        # Create the chain with structured output
        composer_chain = COMPOSER_PROMPT | llm

        try:
            # Prepare prompt input - LangGraph ensures these fields exist
            prompt_input = {
                "email_analysis": email_analysis.model_dump(),
            }

            # Add optional fields if present
            if state.advisor and state.advisor.inquiry_answers:
                prompt_input["inquiry_response"] = (
                    state.advisor.inquiry_answers.model_dump()
                )

            if state.fulfiller and state.fulfiller.order_result:
                prompt_input["order_result"] = state.fulfiller.order_result.model_dump()

            # Execute the chain
            response_data = await composer_chain.ainvoke(prompt_input)

            # LangGraph's structured output should return ComposerOutput directly
            if isinstance(response_data, ComposerOutput):
                response = response_data
            elif isinstance(response_data, dict):
                response_data["email_id"] = email_id
                response = ComposerOutput(**response_data)
            else:
                # If we can't get a proper response, raise an error rather than fallback
                raise ValueError(
                    f"Unexpected response format from LLM: {type(response_data)}"
                )

            # Ensure email_id is set correctly
            response.email_id = email_id

            return create_node_response(Agents.COMPOSER, response)

        except Exception as e:
            # Don't create fallback responses - let the error propagate
            # The assignment requires adaptive tone matching, not hardcoded fallbacks
            raise RuntimeError(
                f"Failed to compose response for email {email_id}: {str(e)}"
            )

    except Exception as e:
        print(f"Error in compose_response: {e}")
        return create_node_response(Agents.COMPOSER, e)
