"""Main function for composing final customer responses."""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langsmith import traceable

from hermes.utils.response import create_node_response
from hermes.utils.tool_error_handler import ToolCallRetryHandler, DEFAULT_RETRY_TEMPLATE

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
from hermes.utils.logger import logger, get_agent_logger

# We don't want to make ALL catalog tools available to the composer agent
ComposerToolkit: list[BaseTool] = [
    find_complementary_products,  # For suggesting additional items
    find_products_for_occasion,  # For occasion-based suggestions
]


@traceable(run_type="chain", name="Composer agent Agent")  # type: ignore
async def run_composer(
    state: ComposerInput,
    config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.COMPOSER], ComposerOutput]:
    """Composes a natural, personalized customer email response by combining information
    from the Classifier agent, Advisor agent, and Fulfiller agent agents.

    Args:
        state: The validated ComposerInput containing outputs from previous agents
        config: Optional config dict with HermesConfig instance

    Returns:
        WorkflowNodeOutput containing the composed response or error

    """
    agent_name = Agents.COMPOSER.value.capitalize()
    email_analysis = state.classifier.email_analysis
    email_id = state.email.email_id
    hermes_config = HermesConfig.from_runnable_config(config)

    logger.info(
        get_agent_logger(
            agent_name,
            f"Attempting to compose response for email [cyan]{email_id}[/cyan]",
        )
    )

    prompt_input_dict = {"email_analysis": email_analysis.model_dump()}
    if state.advisor and state.advisor.inquiry_answers:
        prompt_input_dict["inquiry_answers"] = (
            state.advisor.inquiry_answers.model_dump()
        )
    if state.fulfiller and state.fulfiller.order_result:
        prompt_input_dict["order_result"] = state.fulfiller.order_result.model_dump()

    try:
        # Use a strong model for natural language generation with tools
        llm_with_tools = get_llm_client(
            config=hermes_config,
            schema=ComposerOutput,
            tools=ComposerToolkit,
            model_strength="strong",
            temperature=0.1,
        )
        chain_with_tools = COMPOSER_PROMPT | llm_with_tools

        # Use the retry handler to handle validation errors
        retry_handler = ToolCallRetryHandler(max_retries=2, backoff_factor=0.0)

        response_data = await retry_handler.retry_with_tool_calling(
            chain=chain_with_tools,
            input_data=prompt_input_dict,
            retry_prompt_template=DEFAULT_RETRY_TEMPLATE,
        )

        if isinstance(response_data, ComposerOutput):
            response = response_data
        elif isinstance(response_data, dict):
            if "email_id" not in response_data:
                response_data["email_id"] = email_id
            response = ComposerOutput(**response_data)
        else:
            # This case should ideally be handled by the retry handler
            raise ValueError(
                f"Unexpected response format from LLM after parsing attempts: {type(response_data)}"
            )

        response.email_id = email_id  # Ensure email_id is set
        logger.info(
            get_agent_logger(
                agent_name,
                f"Response composition complete for email [cyan]{email_id}[/cyan]. Response length: [yellow]{len(response.response_body)}[/yellow] chars.",
            )
        )
        return create_node_response(Agents.COMPOSER, response)

    except Exception as e:  # Catch-all for errors from chain invocation or processing
        error_email_id = (
            email_id if "email_id" in locals() and email_id else state.email.email_id
        )
        # This will catch OutputParserException if retries fail,
        # ToolCallError if tools fail, or any other unexpected error.
        error_message = f"Error during composition for email {error_email_id}: {e}"
        logger.error(get_agent_logger(agent_name, error_message), exc_info=True)
        raise RuntimeError(
            f"Composer: Error during composition for email {error_email_id}"
        ) from e
