"""
Main function for analyzing customer emails.
"""

from typing import Literal
from langsmith import traceable
from langchain_core.runnables import RunnableConfig
import json

from .models import (
    EmailAnalysis,
    ClassifierInput,
    ClassifierOutput,
)
from .prompts import get_prompt
from ...config import HermesConfig
from ...utils.llm_client import get_llm_client
from ...data_processing.product_deduplication import get_product_mention_stats
from ...model.enums import Agents
from ...types import WorkflowNodeOutput
from ...utils.errors import create_node_response


@traceable(run_type="chain")
async def analyze_email(
    state: ClassifierInput, runnable_config: RunnableConfig
) -> WorkflowNodeOutput[Literal[Agents.CLASSIFIER], ClassifierOutput]:
    """
    Analyzes a customer email to extract structured information about intent, product references, and customer signals.

    Args:
        state (ClassifierInput): The input model containing email_id, subject, and message.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {"classifier": ClassifierOutput} or {"errors": Error}
    """
    try:
        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        print(
            f"Analyzing email {state.email_id} - Subject: '{state.subject[:50] if state.subject else 'No subject'}...'"
        )

        # Use a weak model for initial analysis since it's a relatively simple task
        llm = get_llm_client(config=hermes_config, model_strength="weak", temperature=0.0)

        analyzer_prompt = get_prompt("classifier")
        analysis_chain = analyzer_prompt | llm

        try:
            raw_llm_output = await analysis_chain.ainvoke(state.model_dump())

            # Manually parse the JSON output
            if not isinstance(raw_llm_output.content, str) or not raw_llm_output.content.strip():
                # Handle empty or non-string output from LLM
                error_message = f"Expected LLM output content to be a non-empty string, but got {type(raw_llm_output.content)} with content: '{raw_llm_output.content[:100]}...'"
                print(f"Error analyzing email {state.email_id}: {error_message}")
                # Return an error response indicating LLM output issue
                return create_node_response(Agents.CLASSIFIER, ValueError(error_message))

            try:
                # Strip markdown code block fences before parsing
                json_string = raw_llm_output.content.strip().strip("```json").strip("```")
                print(f"Attempting to parse JSON string: {json_string[:200]}...")
                parsed_output = json.loads(json_string)
            except json.JSONDecodeError as e:
                # Handle JSON parsing errors
                error_message = f"Failed to parse LLM output as JSON for email {state.email_id}: {e}. Raw output: '{raw_llm_output.content[:200]}...'"
                print(f"Error analyzing email {state.email_id}: {error_message}")
                # Return an error response indicating JSON parsing failure
                return create_node_response(Agents.CLASSIFIER, ValueError(error_message))

            # Explicitly handle the customer_pii field if it's a string (though with manual parsing,
            # json.loads should handle it if it's valid JSON string of a dict)
            # Add additional validation/cleaning for customer_pii if needed here
            # For now, we rely on json.loads to parse the nested dictionary correctly

            email_analysis = EmailAnalysis(**parsed_output)

            # Check if customer_pii is a string and attempt to parse it as JSON
            if isinstance(email_analysis.customer_pii, str):
                try:
                    email_analysis.customer_pii = json.loads(email_analysis.customer_pii)
                except json.JSONDecodeError:
                    # Handle cases where it's a string but not valid JSON, maybe log a warning
                    print(
                        f"Warning: customer_pii for email {state.email_id} is a string but not valid JSON: {email_analysis.customer_pii}"
                    )
                    email_analysis.customer_pii = {}

            # Set the email_id in the analysis
            email_analysis.email_id = state.email_id

            # Get stats about product mentions
            product_stats = await get_product_mention_stats(email_analysis)
            print(
                f"  Analysis for {state.email_id} complete. Found {product_stats['total_mentions']} product mentions across {product_stats['segments_with_products']} segments."
            )

            return create_node_response(
                Agents.CLASSIFIER,
                ClassifierOutput(
                    email_analysis=email_analysis,
                ),
            )

        except Exception as e:
            print(f"Error analyzing email {state.email_id}: {e}")

            return create_node_response(Agents.CLASSIFIER, e)

    except Exception as e:
        # Return errors in the format expected by LangGraph
        print(f"Outer error in analyze_email for {state.email_id}: {e}")
        return create_node_response(Agents.CLASSIFIER, e)
