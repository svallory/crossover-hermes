""" {cell}
## Response Composer Agent

This agent serves as the final step in the email processing pipeline. It takes
the outputs from previous agents (Email Analyzer, Order Processor, or Inquiry Responder)
and composes a polished, natural-sounding response to the customer. Its primary responsibilities:

1. Match the tone and style of the customer's original email
2. Process customer signals to personalize the response
3. Ensure all aspects of the inquiry or order are addressed
4. Generate natural, non-templated language
5. Verify the quality and completeness of the final response

The Response Composer ensures our communications feel personal and human-like,
rather than automated or robotic.
"""
import json
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import re # Import re here for extract_customer_name
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from ..config import HermesConfig # Ensure HermesConfig is imported at the top
# Import the new LLM client utility
from ..llm_client import get_llm_client

# Import necessary models and tools
from ..state import HermesState # Assuming state object is passed

# Import agent-specific response models from their new locations for type hinting and reconstruction
from .email_analyzer import EmailAnalysis 
from .order_processor import OrderProcessingResult
from .inquiry_responder import InquiryResponse

from ..tools.response_tools import (
    ResponseCompositionPlan, 
    generate_natural_response, 
    analyze_tone, 
    extract_questions # Potentially needed if analyzing body here
)
# Commented out old/redundant imports:
# from ..state import EmailAnalysis # For type hinting -> Now from .email_classifier
# from .order_processor import OrderProcessingResult # Import for type hinting -> Now covered above
# from .inquiry_responder import InquiryResponse # Import for type hinting -> Now covered above

# Import the prompt templates
from ..prompts import response_composer_md, response_quality_verification_md

# Optional Pydantic model for structured internal representation
class ResponseComposition(BaseModel):
    """Structured plan for composing the response."""
    customer_name: Optional[str] = None
    greeting_style: str
    closing_style: str
    tone_parameters: Dict[str, Any]
    key_points: List[str]
    personalization_elements: List[str]
    language: str = "English"

async def compose_response_node(state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    LangGraph node function for the Response Composer Agent.
    Composes a final response based on previous agent outputs using a consolidated LLM call.
    
    Args:
        state: The current state dictionary from LangGraph
        config: Optional configuration parameters
        
    Returns:
        Updated state dictionary with final_response field
    """
    # Reconstruct typed state object for better type safety
    typed_state = HermesState(
        email_id=state.get("email_id", "unknown"),
        email_subject=state.get("email_subject", ""),
        email_body=state.get("email_body", ""),
        email_analysis=state.get("email_analysis"),
        order_result=state.get("order_result"),
        inquiry_result=state.get("inquiry_result"),
        product_catalog_df=state.get("product_catalog_df"),
        vector_store=state.get("vector_store")
    )
    
    # Also reconstruct structured objects if available
    email_analysis_obj = None
    order_result_obj = None
    inquiry_result_obj = None
    
    if typed_state.email_analysis:
        try:
            email_analysis_obj = EmailAnalysis(**typed_state.email_analysis)
        except Exception as e:
            print(f"Warning: Could not reconstruct EmailAnalysis: {e}")
    
    if typed_state.order_result:
        try:
            order_result_obj = OrderProcessingResult(**typed_state.order_result)
        except Exception as e:
            print(f"Warning: Could not reconstruct OrderProcessingResult: {e}")
    
    if typed_state.inquiry_result:
        try:
            inquiry_result_obj = InquiryResponse(**typed_state.inquiry_result)
        except Exception as e:
            print(f"Warning: Could not reconstruct InquiryResponse: {e}")
    
    # Extract configuration
    if config and "configurable" in config and "hermes_config" in config["configurable"]:
        hermes_config = config["configurable"]["hermes_config"]
    else:
        # from ..config import HermesConfig # Already imported at the top
        hermes_config = HermesConfig()
    
    # Extract data from typed state
    email_id = typed_state.email_id
    email_body = typed_state.email_body # Still useful for verify_response_quality and analyze_tone fallback
    email_subject = typed_state.email_subject
    email_analysis_data = typed_state.email_analysis # This is a dict
    order_result_data = typed_state.order_result # This is a dict
    inquiry_result_data = typed_state.inquiry_result # This is a dict
    
    # Further extract email_id from order_result or inquiry_result if still unknown
    # This logic might be redundant if email_id is always present from initial state.
    if email_id == "unknown":
        if isinstance(order_result_data, dict) and order_result_data.get("email_id"):
            email_id = order_result_data["email_id"]
        # No need for hasattr check if order_result is always a dict from state
        elif isinstance(inquiry_result_data, dict) and inquiry_result_data.get("email_id"):
            email_id = inquiry_result_data["email_id"]
            
    # Log processing start
    print(f"Composing response for email {email_id} using consolidated LLM approach")
    
    llm = get_llm_client(
        config=hermes_config,
        temperature=hermes_config.llm_response_temperature
    )
    
    # Create prompt templates from markdown content
    response_composer_prompt = PromptTemplate.from_template(response_composer_md)
    
    response_quality_verification_prompt_template = PromptTemplate.from_template(response_quality_verification_md)
    
    classification = email_analysis_data.get("classification", "unknown")
    language = email_analysis_data.get("language", "English")
    tone_info_from_analysis = email_analysis_data.get("tone_analysis", {}) # Expecting a dict
    
    # Ensure tone_info has the expected structure for the tool and prompt
    # The tool's prompt now directly uses `tone` and `formality_level` args.
    # `tone_info_from_analysis` directly from email_analysis should be suitable.
    current_tone_info = {
        "detected_tone": tone_info_from_analysis.get("detected_tone", tone_info_from_analysis.get("tone", "neutral")), # Prioritize detected_tone
        "formality_level": tone_info_from_analysis.get("formality_level", 3),
        # Other fields like key_phrases, writing_style, sentiment are in email_analysis_json for the LLM
    }

    # If tone_analysis was missing or incomplete from earlier step, analyze now (rule-based fallback)
    if not tone_info_from_analysis or "detected_tone" not in tone_info_from_analysis:
        print(f"Running fallback tone analysis for email {email_id}")
        tone_result_obj = analyze_tone(email_body) # analyze_tone returns a ToneAnalysisResult object
        current_tone_info = {
            "detected_tone": tone_result_obj.detected_tone,
            "formality_level": tone_result_obj.formality_level,
        }
        # Update email_analysis_data with this fallback tone analysis so it's in the JSON for LLM
        if email_analysis_data:
          email_analysis_data["tone_analysis"] = tone_result_obj.model_dump() 
        else: # Should not happen if email_analysis is always populated
          email_analysis_data = {"tone_analysis": tone_result_obj.model_dump()}

    # Determine greeting and closing styles based on tone
    # This logic can remain as it pre-sets style based on analysis before the main LLM call
    detected_tone_for_style = current_tone_info.get("detected_tone", "neutral")
    formality_level_for_style = current_tone_info.get("formality_level", 3)

    if detected_tone_for_style == "formal" or formality_level_for_style >= 4:
        greeting_style = "formal"
        closing_style = "formal"
    elif detected_tone_for_style == "casual" and formality_level_for_style <= 2:
        greeting_style = "casual"
        closing_style = "casual"
    elif detected_tone_for_style == "friendly":
        greeting_style = "friendly"
        closing_style = "warm"
    elif detected_tone_for_style == "urgent":
        greeting_style = "direct"
        closing_style = "efficient"
    else:
        greeting_style = "professional"
        closing_style = "professional"

    # The LLM will now generate response points and personalization from raw data.
    # So, remove calls to generate_order_response_points and process_customer_signals.
    # response_points = [] # No longer pre-calculated here
    # personalization_elements = [] # No longer pre-calculated here

    # Get customer name if available (e.g., from email_analysis or a dedicated extraction step if added)
    customer_name = email_analysis_data.get("customer_name") # Assuming email_analysis might have this
    if not customer_name:
        # Basic extraction from email_body if not found (can be improved)
        name_match = re.search(r"(?:Hi|Hello|Dear)\s+([A-Za-z]+)(?:,|!|$)", email_body, re.IGNORECASE)
        if name_match:
            customer_name = name_match.group(1)
    
    # Prepare JSON strings for the tool
    email_analysis_json_str = json.dumps(email_analysis_data if email_analysis_data else {})
    
    # Determine which processing result to use
    processing_results_to_serialize = None
    if classification == "order_request" and order_result_data:
        processing_results_to_serialize = order_result_data
    elif classification == "product_inquiry" and inquiry_result_data:
        processing_results_to_serialize = inquiry_result_data
    else:
        # Fallback: if classification is unknown or results missing, provide a generic structure or empty dict
        # The LLM prompt should be robust enough to handle cases with minimal processing_results.
        processing_results_to_serialize = {"status": "information_not_available", "notes": "Could not determine specific order/inquiry details."}
        if email_body:
             processing_results_to_serialize["original_email_excerpt_for_context"] = email_body[:500]

    processing_results_json_str = json.dumps(processing_results_to_serialize)

    # Prepare the response composition plan using the new Pydantic model structure
    composition_plan = ResponseCompositionPlan(
        customer_name=customer_name,
        greeting_style=greeting_style,
        tone_info=current_tone_info, # Pass the directly used tone/formality for prompt
        closing_style=closing_style,
        language=language,
        email_analysis_json=email_analysis_json_str,
        processing_results_json=processing_results_json_str
    )
    
    customer_signal_manual_extract = """Follow the Customer Signal Processing Guide for:
- Natural Communication: Avoid templates, use contractions (if appropriate), vary sentences, be authentic & personal.
- Response Structure: Greeting, Direct Answer, Expanded Value, Relevant Suggestions, Clear Next Steps, Closing.
- Empathy: Acknowledge emotions, connect product info to emotional context.
- Upselling: Suggest relevant items based on signals, not pushy.
- Limitations: Be transparent about OOS, suggest alternatives.
""" # Kept for generate_natural_response tool
    
    # Call the tool with the dictionary input by unpacking the Pydantic model
    # and adding the llm instance and manual extract.
    generated_response_text = await generate_natural_response.ainvoke(
        {
            **composition_plan.model_dump(), 
            "llm": llm, 
            "customer_signal_manual_extract": customer_signal_manual_extract
        },
        config=config
    )
    
    # Verify the quality of the response
    # The verify_response_quality function now needs to get response_points differently,
    # as they are no longer pre-calculated. For now, we might pass an empty list
    # or have verify_response_quality try to infer them, or this step might need its own LLM call
    # to first list what points *should have been* covered by the main LLM.
    # For simplicity, let's pass an empty list for now, acknowledging this makes verification less robust.
    # A better approach would be to have the main LLM also output the key points it *intended* to cover.
    key_points_for_verification = [] # This is a simplification due to points now being LLM-generated.
                                      # Consider enhancing verify_response_quality or main LLM output.
    
    verified_response = await verify_response_quality(
        response=generated_response_text,
        email_body=email_body,
        email_subject=email_subject,
        email_analysis_json=email_analysis_json_str, # Pass for context to verification LLM
        processing_results_json=processing_results_json_str, # Pass for context
        email_type=classification,
        tone_info=current_tone_info, # Pass for expected tone/formality
        llm=llm
    )
    
    return {"final_response": verified_response}

async def verify_response_quality(response: str, email_body: str, email_subject: str,
                               email_analysis_json: str, processing_results_json: str, # ADDED for context
                               email_type: str, 
                               tone_info: Dict[str, Any], llm: ChatOpenAI) -> str:
    """
    Verify and potentially fix issues in the generated natural language response using an LLM.
    The LLM is now responsible for identifying and fixing issues based on comprehensive context.
    
    Args:
        response: The generated email response string
        email_body: Original customer email body
        email_subject: Original email subject
        email_analysis_json: JSON string of the full email analysis for context.
        processing_results_json: JSON string of the order/inquiry results for context.
        email_type: Classification of the email
        tone_info: Analysis of customer's tone (detected_tone, formality_level)
        llm: Language model for verification and fixing the response string
        
    Returns:
        Verified (potentially improved) response string
    """
    print("Verifying response quality using LLM...")

    # The LLM will perform the checks based on the prompt.
    # Python-based error identification is removed.

    verification_prompt_payload = {
        "email_subject": email_subject,
        "email_body": email_body,
        "email_analysis_json": email_analysis_json,
        "processing_results_json": processing_results_json,
        "email_type": email_type,
        "expected_tone": tone_info.get("detected_tone", tone_info.get("tone", "neutral")),
        "formality_level": tone_info.get("formality_level", 3),
        "original_response": response
    }
    
    # Check for None values in payload that the prompt template might not expect as None
    # For example, processing_results_json might be an empty dict {} stringified, which is fine.
    # Ensure all keys expected by response_quality_verification_prompt_template are present.
    # The template now expects: email_subject, email_body, email_analysis_json, processing_results_json,
    # email_type, expected_tone, formality_level, original_response.

    verification_prompt = response_quality_verification_prompt_template.invoke(verification_prompt_payload)
    
    try:
        fixed_response = await (verification_prompt | llm | StrOutputParser()).ainvoke({})
        # The LLM might return the original response if no changes are needed, or a note.
        # We should check if the fixed_response is substantially different or contains specific keywords
        # indicating no changes were made, though this adds string matching back.
        # For now, assume the LLM returns the (potentially) improved response.
        if fixed_response.strip() != response.strip():
             print("Response verification: LLM suggested revisions.")
        else:
             print("Response verification: LLM confirmed response quality or made no major changes.")
        return fixed_response
    except Exception as e:
        print(f"Response verification: Failed to fix/review issues with LLM: {e}")
        return response # Fallback to original response if LLM verification fails

""" {cell}
### Response Composer Agent Implementation Notes

The Response Composer Agent represents the final stage in our email processing pipeline, transforming structured agent outputs into natural customer communications:

1. **Tone Matching & Personalization**:
   - Analyzes and matches the customer's writing style (formal, casual, friendly, etc.)
   - Processes customer signals to incorporate personalized elements
   - Adapts greeting and closing styles based on detected tone
   - Extracts and uses the customer's name when available

2. **Multi-Source Integration**:
   - Handles both order processing and inquiry response outputs
   - Generates appropriate response points for order statuses, including alternatives for out-of-stock items
   - Ensures all customer questions and concerns are addressed

3. **Natural Language Generation**:
   - Uses a higher temperature setting (0.7) to encourage more creative, natural-sounding text
   - Avoids template-like language through careful prompt engineering
   - Includes personalized phrases that build rapport based on detected customer signals

4. **Quality Verification**:
   - Implements a verification step to ensure all required information is included
   - Checks for appropriate tone and completeness
   - Includes fallback generation for edge cases where the primary approach fails

5. **Error Resilience**:
   - Handles missing or incomplete data from previous agents gracefully
   - Includes fallback approaches for each component of the response generation process

This agent ensures that all communications feel personal and human-like, moving beyond simple templates to create genuinely helpful and engaging customer responses.
""" 