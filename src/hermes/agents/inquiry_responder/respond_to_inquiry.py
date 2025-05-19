"""
Main function for responding to customer inquiries.
"""

from typing import Literal, Optional
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from .models import (
    InquiryAnswers,
    InquiryResponderOutput,
    InquiryResponderInput,
)
from .prompts import get_prompt
from ...config import HermesConfig
from ...utils.llm_client import get_llm_client
from ...model import WorkflowNodeOutput, Agents
from ...utils.errors import create_node_response


@traceable(
    run_type="chain",
    name="Inquiry Responder Agent",
)
async def respond_to_inquiry(
    state: InquiryResponderInput,
    runnable_config: Optional[RunnableConfig] = None,
) -> WorkflowNodeOutput[Literal[Agents.INQUIRY_RESPONDER], InquiryResponderOutput]:
    """
    Extracts and answers customer inquiries with factual information about products.
    Uses RAG techniques to retrieve relevant product information.

    Args:
        state (InquiryResponderInput): The input model containing the EmailAnalysisResult from the Email Analyzer.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {Agents.RESPOND_TO_INQUIRY: InquiryResponderOutput} or {"errors": Error}
    """
    try:
        # Validate the input
        if not hasattr(state, Agents.EMAIL_ANALYZER) or not state.email_analysis:
            return create_node_response(
                Agents.INQUIRY_RESPONDER,
                Exception("No email analysis available for inquiry response.")
            )
            
        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        # Extract email_id from the analysis result - safely handle different formats
        if hasattr(state.email_analysis, "email_id"):
            email_id = state.email_analysis.email_id  # type: ignore[attr-defined]
        elif hasattr(state.email_analysis, "model_dump"):
            analysis_dict = state.email_analysis.model_dump()
            email_id = analysis_dict.get("email_id", "unknown_id")
        elif isinstance(state.email_analysis, dict) and "email_id" in state.email_analysis:
            email_id = state.email_analysis["email_id"]
        else:
            email_id = "unknown_id"

        print(f"Generating factual answers for inquiry {email_id}")

        # Use a strong model for factual accuracy
        llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.1)

        # Create the prompt and chain
        inquiry_responder_prompt = get_prompt(Agents.INQUIRY_RESPONDER)
        inquiry_response_chain = inquiry_responder_prompt | llm.with_structured_output(InquiryAnswers)

        try:
            # Prepare input data - convert Pydantic model to dict if necessary
            email_analysis_data = (
                state.email_analysis.model_dump() if hasattr(state.email_analysis, "model_dump") else state.email_analysis
            )

            # Generate the inquiry response
            response_data = await inquiry_response_chain.ainvoke({"email_analysis": email_analysis_data})

            # Ensure we get the right type by instantiating from the response
            if isinstance(response_data, InquiryAnswers):
                inquiry_response = response_data
            else:
                # If we got a dict, convert it to InquiryAnswers
                if isinstance(response_data, dict):
                    # Make sure email_id is included
                    response_data["email_id"] = email_id
                    inquiry_response = InquiryAnswers(**response_data)
                else:
                    # Fallback if we got something unexpected
                    inquiry_response = InquiryAnswers(
                        email_id=email_id,
                        primary_products=[],
                        answered_questions=[],
                        unanswered_questions=["Unable to process inquiry due to unexpected response type."],
                        related_products=[],
                        unsuccessful_references=[],
                    )

            # Make sure email_id is set correctly in the response
            inquiry_response.email_id = email_id

            # Log the results
            print(f"  Response generated for {email_id}")
            print(f"  Answered {len(inquiry_response.answered_questions)} questions")
            print(f"  Identified {len(inquiry_response.primary_products)} primary products")
            print(f"  Suggested {len(inquiry_response.related_products)} related products")

            return create_node_response(
                Agents.INQUIRY_RESPONDER,
                InquiryResponderOutput(inquiry_answers=inquiry_response)
            )

        except Exception as e:
            print(f"Error generating inquiry response for {email_id}: {e}")

            # Create a factual fallback response without customer-facing language
            fallback_response = InquiryAnswers(
                email_id=email_id,
                primary_products=[],
                answered_questions=[],
                unanswered_questions=["Unable to process inquiry due to system error."],
                related_products=[],
                unsuccessful_references=[],
            )

            return create_node_response(
                Agents.INQUIRY_RESPONDER,
                InquiryResponderOutput(inquiry_answers=fallback_response)
            )
            
    except Exception as e:
        # Return errors in the format expected by LangGraph
        return create_node_response(Agents.INQUIRY_RESPONDER, e)
