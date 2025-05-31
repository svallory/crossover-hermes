"""Main function for analyzing customer emails."""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from ...utils.response import create_node_response

from ...model.email import EmailAnalysis
from .models import ClassifierInput, ClassifierOutput

from ...config import HermesConfig
from ...model.enums import Agents
from ...workflow.types import WorkflowNodeOutput
from hermes.utils.llm_client import get_llm_client
from hermes.utils.logger import logger, get_agent_logger

from .prompts import CLASSIFIER_PROMPT


@traceable(run_type="chain")
async def run_classifier(
    state: ClassifierInput, config: RunnableConfig
) -> WorkflowNodeOutput[Literal[Agents.CLASSIFIER], ClassifierOutput]:
    """Analyzes a customer email to extract structured information about intent, product references,
    and customer signals.

    Args:
        state (ClassifierInput): The input model containing email_id, subject, and message.
        config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'],
            HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {"classifier": ClassifierOutput} or {"errors": Error}

    """
    agent_name = Agents.CLASSIFIER.value.capitalize()
    try:
        hermes_config = HermesConfig.from_runnable_config(config)

        logger.info(
            get_agent_logger(
                agent_name,
                f"Analyzing email [cyan]{state.email.email_id}[/cyan] - Subject: '[italic]{state.email.subject if state.email.subject else 'No subject'}[/italic]'...",
            )
        )

        # Use a weak model for initial analysis since it's a relatively simple task
        llm = get_llm_client(
            config=hermes_config,
            schema=EmailAnalysis,
            tools=[],
            model_strength="strong",
            temperature=0.0,
        )

        analysis_chain = CLASSIFIER_PROMPT | llm

        # chain_result should now be an EmailAnalysis instance directly
        email_analysis_result: EmailAnalysis = await analysis_chain.ainvoke(
            state.email.model_dump()
        )

        # Set the email_id in the analysis, as it's not part of the LLM's direct output
        email_analysis_result.email_id = state.email.email_id

        logger.info(
            get_agent_logger(
                agent_name,
                f"Email [cyan]{state.email.email_id}[/cyan] analysis complete: {email_analysis_result.primary_intent}",
            )
        )

        return create_node_response(
            Agents.CLASSIFIER,
            ClassifierOutput(
                email_analysis=email_analysis_result,
            ),
        )

    except Exception as e:
        e.add_note(f"Error in {agent_name} for email {state.email.email_id}")
        raise e
