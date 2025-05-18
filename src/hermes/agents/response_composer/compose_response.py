"""
Main function for composing final customer responses.
"""

from typing import Dict, Any, Optional, Literal
from src.hermes.model import KeyedConfigDict
from langsmith import traceable

from .models import (
    ComposedResponse,
    ResponseComposerOutput,
    ResponseComposerInput,
)
from .prompts import get_prompt
from ...config import HermesConfig
from ...utils.llm_client import get_llm_client


@traceable(
    name="Response Composer Agent",
    description="Composes the final customer response by combining outputs from previous agents.",
)
async def compose_response(
    state: ResponseComposerInput,
    runnable_config: Optional[
        KeyedConfigDict[
            Literal["configurable"], Dict[Literal["hermes_config"], HermesConfig]
        ]
    ] = None,
) -> ResponseComposerOutput:
    """
    Composes a natural, personalized customer email response by combining information
    from the Email Analyzer, Inquiry Responder, and Order Processor agents.

    Args:
        state (ResponseComposerInput): The input model containing outputs from previous agents.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        ResponseComposerOutput: The output model containing the final composed email response.
    """
    hermes_config = HermesConfig.from_runnable_config(runnable_config)

    # Extract email_id from the analysis result
    # For Pydantic models, use hasattr and __dict__ to safely access attributes
    if hasattr(state.email_analysis, "email_id"):
        email_id = state.email_analysis.email_id
    elif isinstance(state.email_analysis, dict) and "email_id" in state.email_analysis:
        email_id = state.email_analysis["email_id"]
    else:
        email_id = "unknown_id"

    print(f"Composing final customer response for email {email_id}")

    # Use a strong model for natural language generation
    llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.7)

    # Create the prompt and chain
    response_composer_prompt = get_prompt("response_composer")

    # Prepare the input data for the prompt - convert Pydantic models to dicts if necessary
    prompt_input = {
        "email_analysis": state.email_analysis.model_dump()
        if hasattr(state.email_analysis, "model_dump")
        else state.email_analysis
    }

    # Add inquiry response if available
    if state.inquiry_response:
        prompt_input["inquiry_response"] = (
            state.inquiry_response.model_dump()
            if hasattr(state.inquiry_response, "model_dump")
            else state.inquiry_response
        )

    # Add order result if available
    if state.order_result:
        prompt_input["order_result"] = (
            state.order_result.model_dump()
            if hasattr(state.order_result, "model_dump")
            else state.order_result
        )

    # Create the chain with structured output
    response_chain = response_composer_prompt | llm.with_structured_output(
        ComposedResponse
    )

    try:
        # Generate the composed response
        composed_response: ComposedResponse = await response_chain.ainvoke(prompt_input)

        # Log the results
        print(f"  Response composed for email {email_id}")
        print(f"  Response tone: {composed_response.tone.value}")
        print(f"  Response language: {composed_response.language}")
        print(f"  Response length: {len(composed_response.response_body)} characters")

        return ResponseComposerOutput(composed_response=composed_response)

    except Exception as e:
        print(f"Error composing response for {email_id}: {e}")

        # Create a simple fallback response
        fallback_response = ComposedResponse(
            email_id=email_id,
            subject="Re: Your Recent Communication",
            response_body="Thank you for your message. We're experiencing technical difficulties at the moment. A team member will reach out to you shortly to address your inquiry or order request. We apologize for any inconvenience.\n\nBest regards,\nHermes - Delivering divine fashion",
            language="en",  # Default to English for fallback
            tone="professional",  # Default to professional tone for fallback
            response_points=[],
        )

        return ResponseComposerOutput(composed_response=fallback_response)
