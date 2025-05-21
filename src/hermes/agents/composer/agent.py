"""Main function for composing final customer responses."""

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from src.hermes.utils.errors import create_node_response

from ...agents.advisor.models import InquiryAnswers
from ...agents.classifier.models import EmailAnalysis
from ...config import HermesConfig
from ...model.enums import Agents
from ...types import WorkflowNodeOutput
from ...utils import get_llm_client
from ..fulfiller.models.agent import ProcessedOrder
from .models import (
    ComposedResponse,
    ComposerInput,
    ComposerOutput,
    ResponseTone,
)
from .prompts import get_prompt

@traceable(run_type="chain", name="Response Composer Agent")  # type: ignore
async def compose_response(
    state: ComposerInput,
    runnable_config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.COMPOSER], ComposerOutput]:
    """Composes a natural, personalized customer email response by combining information
    from the Email Analyzer, Inquiry Responder, and Order Processor agents.

    Args:
        state (OverallState): The current overall state of the workflow.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {"composer": ComposerOutput} or {"errors": Error}

    """
    try:
        email_analysis_data: EmailAnalysis | None = None
        if state.classifier and state.classifier.email_analysis:
            email_analysis_data = state.classifier.email_analysis

        if email_analysis_data is None:
            return create_node_response(
                Agents.COMPOSER, Exception("No email analysis available for response composition.")
            )

        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        email_id = email_analysis_data.email_id if email_analysis_data.email_id else state.email_id or "unknown_id"

        print(f"Composing final customer response for email {email_id}")

        # Prepare data for the prompt
        inquiry_answers_data: InquiryAnswers | None = None
        if state.advisor and state.advisor.inquiry_answers:
            inquiry_answers_data = state.advisor.inquiry_answers

        order_result_data: ProcessedOrder | None = None
        if state.fulfiller and state.fulfiller.order_result:
            order_result_data = state.fulfiller.order_result

        # Use a strong model for natural language generation
        llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.7)

        # Create the prompt
        composer_prompt = get_prompt(Agents.COMPOSER)

        # Create the chain
        composer_chain = composer_prompt | llm.with_structured_output(ComposedResponse)

        try:
            # Prepare the input dictionary for the chain, ensuring all keys expected by the prompt are present
            # (typically matching fields of ComposerInput model)
            prompt_input_data = {
                "email_analysis": email_analysis_data.model_dump() if email_analysis_data else None,
                "inquiry_response": inquiry_answers_data.model_dump() if inquiry_answers_data else None,
                "order_result": order_result_data.model_dump() if order_result_data else None,
            }
            # Filter out keys with None values to avoid passing them if not available
            filtered_prompt_input_data = {k: v for k, v in prompt_input_data.items() if v is not None}

            # Execute the chain
            response_data = await composer_chain.ainvoke(filtered_prompt_input_data)

            # Properly handle the response with type checking
            if isinstance(response_data, ComposedResponse):
                response = response_data
            # If we got a dict, convert it to ComposedResponse
            elif isinstance(response_data, dict):
                # Make sure email_id is included
                response_data["email_id"] = email_id
                response = ComposedResponse(**response_data)
            else:
                # Fallback if we got something unexpected
                response = ComposedResponse(
                    email_id=email_id,
                    subject="Re: Your Recent Inquiry",
                    response_body="Thank you for contacting us. We're processing your request.",
                    language="en",
                    tone=ResponseTone.PROFESSIONAL,
                    response_points=[],
                )

            # Make sure the email_id is set correctly
            response.email_id = email_id

            # Log the results
            print(f"  Response composed for email {email_id}")
            print(f"  Response tone: {response.tone.value}")
            print(f"  Response language: {response.language}")
            print(f"  Response length: {len(response.response_body)} characters")

            return create_node_response(Agents.COMPOSER, ComposerOutput(composed_response=response))

        except Exception as e:
            # Create a basic response in case of errors
            response = ComposedResponse(
                email_id=email_id,
                subject="Re: Your Recent Inquiry",
                response_body=f"Thank you for your message. We're experiencing technical difficulties processing your request. Error: {str(e)}",
                language="en",
                tone=ResponseTone.PROFESSIONAL,
                response_points=[],
            )
            # Although it's an internal error, we return a composed response for the user
            return create_node_response(Agents.COMPOSER, ComposerOutput(composed_response=response))

    except Exception as e:
        # Return errors in the format expected by LangGraph
        print(f"Outer error in compose_response: {e}")
        return create_node_response(Agents.COMPOSER, e)
