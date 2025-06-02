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
    QuestionAnswer,
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
    config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.ADVISOR], AdvisorOutput]:
    """Run the advisor agent to analyze customer inquiries and provide factual responses.

    This agent extracts questions from customer emails and provides objective answers
    using the product catalog and resolved product information.

    Args:
        state: AdvisorInput containing classifier output and optional stockkeeper output
        config: Optional configuration for the runnable

    Returns:
        WorkflowNodeOutput containing the advisor's factual response
    """
    agent_name = Agents.ADVISOR.value.capitalize()
    email_id = state.classifier.email_analysis.email_id
    # Ensure stockkeeper output is accessed correctly
    stockkeeper_output = state.stockkeeper  # StockkeeperOutput | None

    logger.info(
        get_agent_logger(agent_name, f"Running for email [cyan]{email_id}[/cyan]")
    )

    try:
        hermes_config = HermesConfig.from_runnable_config(config)
        llm_with_tools = get_llm_client(
            config=hermes_config,
            schema=InquiryAnswers,
            tools=CatalogToolkit.get_tools(),
            model_strength="strong",
            temperature=0.05,
        )

        email_analysis_dump = state.classifier.email_analysis.model_dump()

        # Prepare inputs for the prompt based on the new StockkeeperOutput structure
        candidate_products_input = []
        unresolved_mentions_input = []
        programmatic_answered_questions: list[QuestionAnswer] = []
        programmatic_unsuccessful_references: list[str] = []
        explicitly_not_found_ids_for_prompt: list[str] = []

        if stockkeeper_output:
            if stockkeeper_output.candidate_products_for_mention:
                candidate_products_input = [
                    {
                        "original_mention": mention.model_dump(),
                        "candidates": [p.model_dump(exclude_none=True) for p in prods],
                    }
                    for mention, prods in stockkeeper_output.candidate_products_for_mention
                ]
            if stockkeeper_output.unresolved_mentions:
                unresolved_mentions_input = [
                    mention.model_dump()
                    for mention in stockkeeper_output.unresolved_mentions
                ]

            # Process exact_id_misses
            if (
                hasattr(stockkeeper_output, "exact_id_misses")
                and stockkeeper_output.exact_id_misses
            ):
                for missed_mention in stockkeeper_output.exact_id_misses:
                    if missed_mention.product_id:
                        question_text = f"Regarding product ID '{missed_mention.product_id}' (mentioned as '{missed_mention.mention_text}'), is it available?"
                        answer_text = f"The product with ID '{missed_mention.product_id}' (mentioned as '{missed_mention.mention_text}') could not be found in our catalog."

                        programmatic_qa = QuestionAnswer(
                            question=question_text,
                            answer=answer_text,
                            confidence=1.0,
                            reference_product_ids=[missed_mention.product_id],
                            answer_type="unavailable",
                        )
                        programmatic_answered_questions.append(programmatic_qa)
                        if (
                            missed_mention.product_id
                            not in programmatic_unsuccessful_references
                        ):
                            programmatic_unsuccessful_references.append(
                                missed_mention.product_id
                            )
                        if (
                            missed_mention.product_id
                            not in explicitly_not_found_ids_for_prompt
                        ):
                            explicitly_not_found_ids_for_prompt.append(
                                missed_mention.product_id
                            )

        prompt_input_dict = {
            "email_analysis": email_analysis_dump,
            "candidate_products_for_mention": candidate_products_input,
            "unresolved_mentions": unresolved_mentions_input,
            "explicitly_not_found_ids": explicitly_not_found_ids_for_prompt,
        }

        # Determine which prompt to use based on language
        # This part of your existing logic might need to be preserved/adapted
        current_prompt = ADVISOR_PROMPT
        if state.classifier.email_analysis.language == "Arabic":
            # current_prompt = الاجابه_على_السؤال_بالعربية_prompt # Ensure this is correctly defined and imported
            logger.info(get_agent_logger(agent_name, "Using Arabic prompt for Advisor"))
            # For now, let's assume ADVISOR_PROMPT is language-agnostic or English,
            # and handle multilingual aspects within the prompt or via separate prompts if truly needed.
            pass

        chain_with_tools = current_prompt | llm_with_tools
        retry_handler = ToolCallRetryHandler(max_retries=2, backoff_factor=0.0)

        response_data = await retry_handler.retry_with_tool_calling(
            chain=chain_with_tools,
            input_data=prompt_input_dict,
            retry_prompt_template=DEFAULT_RETRY_TEMPLATE,
        )

        if isinstance(response_data, InquiryAnswers):
            inquiry_answers = response_data
        elif isinstance(response_data, dict):
            # Ensure email_id is present if creating from dict
            if "email_id" not in response_data and email_id:
                response_data["email_id"] = email_id
            inquiry_answers = InquiryAnswers(**response_data)
        else:
            raise ValueError(
                f"Unexpected response format from LLM: {type(response_data)}"
            )

        inquiry_answers.email_id = email_id  # Ensure email_id is set

        # Merge programmatic answers and unsuccessful references
        # Prepend to ensure they appear first or are distinctly handled if order matters
        inquiry_answers.answered_questions = (
            programmatic_answered_questions + inquiry_answers.answered_questions
        )
        for ref_id in programmatic_unsuccessful_references:
            if ref_id not in inquiry_answers.unsuccessful_references:
                inquiry_answers.unsuccessful_references.append(ref_id)

        logger.info(
            get_agent_logger(
                agent_name,
                f"Successfully processed inquiries for email [cyan]{email_id}[/cyan]. Questions answered: {len(inquiry_answers.answered_questions)}",
            )
        )
        return create_node_response(
            Agents.ADVISOR, AdvisorOutput(inquiry_answers=inquiry_answers)
        )

    except Exception as e:
        error_message = f"Error in {agent_name} for email {email_id}: {e}"
        logger.error(get_agent_logger(agent_name, error_message), exc_info=True)
        raise RuntimeError(
            f"Advisor: Error during processing for email {email_id}"
        ) from e
