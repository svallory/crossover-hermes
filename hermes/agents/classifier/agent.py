"""Main function for analyzing customer emails."""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from ...model.email import EmailAnalysis
from .models import ClassifierInput, ClassifierOutput

from ...config import HermesConfig
from ...model.enums import Agents
from ...workflow.types import WorkflowNodeOutput
from ...utils.response import create_node_response
from hermes.utils.llm_client import get_llm_client

from .prompts import CLASSIFIER_PROMPT


@traceable(run_type="chain")
async def run_classifier(
    state: ClassifierInput, runnable_config: RunnableConfig
) -> WorkflowNodeOutput[Literal[Agents.CLASSIFIER], ClassifierOutput]:
    """Analyzes a customer email to extract structured information about intent, product references,
    and customer signals.

    Args:
        state (ClassifierInput): The input model containing email_id, subject, and message.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'],
            HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {"classifier": ClassifierOutput} or {"errors": Error}

    """
    try:
        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        print(
            f"Analyzing email {state.email.email_id} - Subject: '{state.email.subject[:50] if state.email.subject else 'No subject'}...'"
        )

        # Use a weak model for initial analysis since it's a relatively simple task
        llm = get_llm_client(
            config=hermes_config,
            schema=EmailAnalysis,
            tools=[],
            model_strength="weak",
            temperature=0.0,
        )

        analysis_chain = CLASSIFIER_PROMPT | llm

        try:
            chain_result = await analysis_chain.ainvoke(state.email.model_dump())

            email_analysis = EmailAnalysis.model_validate(chain_result)

            # Set the email_id in the analysis
            email_analysis.email_id = state.email.email_id

            print(f"  Analysis for {state.email.email_id} complete.")

            return create_node_response(
                Agents.CLASSIFIER,
                ClassifierOutput(
                    email_analysis=email_analysis,
                ),
            )

        except Exception as e:
            print(f"Error analyzing email {state.email.email_id}: {e}")

            return create_node_response(Agents.CLASSIFIER, e)

    except Exception as e:
        # Return errors in the format expected by LangGraph
        print(f"Outer error in analyze_email for {state.email.email_id}: {e}")
        return create_node_response(Agents.CLASSIFIER, e)
