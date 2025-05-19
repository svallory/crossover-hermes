"""
Main function for composing final customer responses.
"""

from typing import Dict, Any, Optional, Literal, Union
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from src.hermes.utils.errors import create_node_response

from .models import (
    ComposedResponse,
    ResponseComposerOutput,
    ResponseComposerInput,
    ResponseTone,
)
from .prompts import get_prompt
from ...config import HermesConfig
from ...utils import get_llm_client
from ...model import WorkflowNodeOutput, Agents, Error

@traceable(run_type="chain", name="Response Composer Agent")  # type: ignore
async def compose_response(
    state: ResponseComposerInput,
    runnable_config: Optional[RunnableConfig] = None,
) -> WorkflowNodeOutput[Literal[Agents.RESPONSE_COMPOSER], ResponseComposerOutput]:
    """
    Composes a natural, personalized customer email response by combining information
    from the Email Analyzer, Inquiry Responder, and Order Processor agents.

    Args:
        state (ResponseComposerInput): The input model containing outputs from previous agents.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {"response_composer": ResponseComposerOutput} or {"errors": Error}
    """
    try:
        # Validate the input
        if not hasattr(state, "email_analysis") or not state.email_analysis:
            return create_node_response(
                Agents.RESPONSE_COMPOSER,
                Exception("No email analysis available for response composition.")
            )
            
            
        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        # Extract email_id from the analysis result
        # For Pydantic models, use hasattr and __dict__ to safely access attributes
        if hasattr(state.email_analysis, "email_id"):
            email_id = state.email_analysis.email_id  # type: ignore[attr-defined]
        elif isinstance(state.email_analysis, dict) and "email_id" in state.email_analysis:
            email_id = state.email_analysis["email_id"]
        else:
            email_id = "unknown_id"

        print(f"Composing final customer response for email {email_id}")

        # Use a strong model for natural language generation
        llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.7)

        # Create the prompt
        composer_prompt = get_prompt(Agents.RESPONSE_COMPOSER)

        # Create the chain
        composer_chain = composer_prompt | llm.with_structured_output(ComposedResponse)

        try:
            # Execute the chain
            response_data = await composer_chain.ainvoke(state.model_dump())

            # Properly handle the response with type checking
            if isinstance(response_data, ComposedResponse):
                response = response_data
            else:
                # If we got a dict, convert it to ComposedResponse
                if isinstance(response_data, dict):
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

            return create_node_response(
                Agents.RESPONSE_COMPOSER,
                ResponseComposerOutput(composed_response=response)
            )
            
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
            return create_node_response(
                Agents.RESPONSE_COMPOSER,
                ResponseComposerOutput(composed_response=response)
            )
            
    except Exception as e:
        # Return errors in the format expected by LangGraph
        print(f"Outer error in compose_response: {e}")
        return create_node_response(Agents.RESPONSE_COMPOSER, e)

