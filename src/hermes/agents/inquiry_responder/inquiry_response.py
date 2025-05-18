"""
Main function for responding to customer inquiries.
"""

from typing import Dict, Any, Optional, Literal
from src.hermes.model import KeyedConfigDict
from langsmith import traceable

from .models import (
    InquiryAnswers,
    InquiryResponderOutput,
    InquiryResponderInput,
)
from .prompts import get_prompt
from ...config import HermesConfig
from ...utils.llm_client import get_llm_client


@traceable(
    name="Inquiry Responder Agent",
    description="Responds to customer product inquiries using product catalog information.",
)
async def respond_to_inquiry(
    state: InquiryResponderInput,
    runnable_config: Optional[
        KeyedConfigDict[
            Literal["configurable"], Dict[Literal["hermes_config"], HermesConfig]
        ]
    ] = None,
) -> InquiryResponderOutput:
    """
    Extracts and answers customer inquiries with factual information about products.
    Uses RAG techniques to retrieve relevant product information.

    Args:
        state (InquiryResponderInput): The input model containing the EmailAnalysisResult from the Email Analyzer.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        InquiryResponderOutput: The output model containing the factual answers to customer inquiries.
    """
    hermes_config = HermesConfig.from_runnable_config(runnable_config)

    # Extract email_id from the analysis result - safely handle different formats
    if hasattr(state.email_analysis, "email_id"):
        email_id = state.email_analysis.email_id
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
    inquiry_responder_prompt = get_prompt("inquiry_responder")
    inquiry_response_chain = inquiry_responder_prompt | llm.with_structured_output(
        InquiryAnswers
    )

    try:
        # Prepare input data - convert Pydantic model to dict if necessary
        email_analysis_data = (
            state.email_analysis.model_dump()
            if hasattr(state.email_analysis, "model_dump")
            else state.email_analysis
        )

        # Generate the inquiry response
        inquiry_response: InquiryAnswers = await inquiry_response_chain.ainvoke(
            {"email_analysis": email_analysis_data}
        )

        # Make sure email_id is set correctly in the response
        inquiry_response.email_id = email_id

        # Log the results
        print(f"  Response generated for {email_id}")
        print(f"  Answered {len(inquiry_response.answered_questions)} questions")
        print(f"  Identified {len(inquiry_response.primary_products)} primary products")
        print(f"  Suggested {len(inquiry_response.related_products)} related products")

        return InquiryResponderOutput(inquiry_answers=inquiry_response)

    except Exception as e:
        print(f"Error generating inquiry response for {email_id}: {e}")

        # Create a factual fallback response without customer-facing language
        fallback_response = InquiryAnswers(
            email_id=email_id,
            primary_products=[],
            answered_questions=[],
            unanswered_questions=["Unable to process inquiry due to system error."],
            related_products=[],
            response_points=[],
        )

        return InquiryResponderOutput(inquiry_answers=fallback_response)
