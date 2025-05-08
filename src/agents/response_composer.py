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
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from ..config import HermesConfig # Ensure HermesConfig is imported at the top
# Import the new LLM client utility
from ..llm_client import get_llm_client

# Import necessary models and tools
from ..state import HermesState # Assuming state object is passed
from ..tools.response_tools import (
    ResponseCompositionPlan, 
    generate_natural_response, 
    analyze_tone, 
    extract_questions # Potentially needed if analyzing body here
)
from .email_classifier import EmailAnalysis # For type hinting
from .order_processor import OrderProcessingResult # Import for type hinting
from .inquiry_responder import InquiryResponse # Import for type hinting

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
    Composes a final response based on previous agent outputs.
    
    Args:
        state: The current state dictionary from LangGraph
        config: Optional configuration parameters
        
    Returns:
        Updated state dictionary with final_response field
    """
    # Extract configuration
    if config and "configurable" in config and "hermes_config" in config["configurable"]:
        hermes_config = config["configurable"]["hermes_config"]
    else:
        # from ..config import HermesConfig # Already imported at the top
        hermes_config = HermesConfig()
    
    # Extract data from state - handle both dictionary and object access
    # Handle email_id properly whether state is a dict or object
    if isinstance(state, dict):
        email_id = state.get("email_id", "unknown")
        email_body = state.get("email_body", "")
        email_subject = state.get("email_subject", "")
        email_analysis_data = state.get("email_analysis", {})
        order_result = state.get("order_result", {})
        inquiry_result = state.get("inquiry_result", {})
    else:
        # Object-style access with getattr
        email_id = getattr(state, "email_id", "unknown")
        email_body = getattr(state, "email_body", "")
        email_subject = getattr(state, "email_subject", "")
        email_analysis_data = getattr(state, "email_analysis", {}) 
        order_result = getattr(state, "order_result", {})
        inquiry_result = getattr(state, "inquiry_result", {})
    
    # Further extract email_id from order_result or inquiry_result if still unknown
    if email_id == "unknown":
        if isinstance(order_result, dict) and "email_id" in order_result:
            email_id = order_result["email_id"]
        elif hasattr(order_result, "email_id"):
            email_id = order_result.email_id
        elif isinstance(inquiry_result, dict) and "email_id" in inquiry_result:
            email_id = inquiry_result["email_id"]
        elif hasattr(inquiry_result, "email_id"):
            email_id = inquiry_result.email_id
    
    # Log processing start
    print(f"Composing response for email {email_id}")
    
    # Initialize LLM for response generation with slightly higher temperature for creativity
    llm = get_llm_client(
        config=hermes_config,
        temperature=hermes_config.llm_response_temperature # Higher temperature for natural responses
    )
    
    # Determine email type based on classification
    classification = None
    language = "English" # Default language
    tone_info = {}
    customer_signals = []
    
    if isinstance(email_analysis_data, dict):
        classification = email_analysis_data.get("classification", "unknown")
        language = email_analysis_data.get("language", "English")
        if "tone_analysis" in email_analysis_data:
            tone_analysis = email_analysis_data["tone_analysis"]
            # Ensure tone_analysis itself is accessed as a dict
            tone_info = {
                "tone": tone_analysis.get("tone", "neutral"),
                "formality_level": tone_analysis.get("formality_level", 3),
                "key_phrases": tone_analysis.get("key_phrases", [])
            }
        customer_signals = email_analysis_data.get("customer_signals", [])
        
    elif hasattr(email_analysis_data, 'classification'): # Check if it's an object
        classification = email_analysis_data.classification
        language = email_analysis_data.language
        if hasattr(email_analysis_data, 'tone_analysis'):
            tone_analysis = email_analysis_data.tone_analysis
            # Access attributes if tone_analysis is an object
            tone_info = {
                "tone": getattr(tone_analysis, "tone", "neutral"),
                "formality_level": getattr(tone_analysis, "formality_level", 3),
                "key_phrases": getattr(tone_analysis, "key_phrases", [])
            }
        if hasattr(email_analysis_data, 'customer_signals'):
             customer_signals = email_analysis_data.customer_signals # Should be list of objects/dicts
    
    # If tone info still empty, analyze directly
    if not tone_info:
        tone_result = analyze_tone(email_body)
        tone_info = {
            "tone": tone_result.detected_tone,
            "formality_level": tone_result.formality_level,
            "key_phrases": tone_result.key_phrases,
            "writing_style": tone_result.writing_style,
            "sentiment": tone_result.sentiment
        }
    
    # Determine source of response points based on email type
    response_points = []
    
    if classification == "order_request":
        # order_result is already a dict from state access or processing
        if order_result:
            response_points = await generate_order_response_points(order_result, email_analysis_data)
    elif classification == "product_inquiry":
        # inquiry_result could be an object or dict, handle both
        if isinstance(inquiry_result, dict):
            response_points = inquiry_result.get("response_points", [])
        elif hasattr(inquiry_result, 'response_points'):
            response_points = inquiry_result.response_points
    else:
        # Fallback for unknown email types or missing results
        response_points = ["Acknowledge receipt of the customer's email",
                          "Express appreciation for their interest",
                          "Offer general assistance"]
    
    # Get customer name if available
    customer_name = extract_customer_name(email_body)
    
    # Determine greeting and closing styles based on tone
    greeting_style = determine_greeting_style(tone_info)
    closing_style = determine_closing_style(tone_info)
    
    # Process customer signals to personalize the response
    personalization_elements = await process_customer_signals(
        customer_signals=customer_signals,
        email_body=email_body,
        email_type=classification,
        llm=llm
    )
    
    # Prepare the response composition plan
    composition_plan = ResponseCompositionPlan(
        customer_name=customer_name,
        greeting_style=greeting_style,
        response_points=response_points,
        tone_info=tone_info,
        answer_phrases=personalization_elements,
        closing_style=closing_style,
        language=language
    )
    
    # Convert the plan to the dictionary format expected by the tool
    tool_input = {
        "plan": composition_plan.model_dump() # Assuming tool expects a dict derived from Pydantic
    }
    
    # Call the tool with the dictionary input
    final_response = await generate_natural_response.ainvoke(composition_plan.model_dump(), config=config)
    
    # Verify the quality of the response
    verified_response = await verify_response_quality(
        response=final_response,
        email_body=email_body,
        email_subject=email_subject,
        response_points=response_points,
        email_type=classification,
        tone_info=tone_info,
        llm=llm
    )
    
    # Return the updated state with the final response
    return {"final_response": verified_response}

async def generate_order_response_points(order_result: Union[Dict[str, Any], OrderProcessingResult],
                                     email_analysis: Union[Dict[str, Any], EmailAnalysis]) -> List[str]:
    """Generate key response points based on order processing results."""
    points = []
    
    # Determine how to access fields based on type
    def _get_value(data, key, default=None):
        if isinstance(data, dict):
            return data.get(key, default)
        elif hasattr(data, key):
            return getattr(data, key, default)
        return default

    overall_status = _get_value(order_result, "overall_status", "unknown")
    fulfilled_count = _get_value(order_result, "fulfilled_items_count", 0)
    oos_count = _get_value(order_result, "out_of_stock_items_count", 0)
    order_items = _get_value(order_result, "order_items", [])
    alternatives = _get_value(order_result, "suggested_alternatives", [])
    processing_notes = _get_value(order_result, "processing_notes", [])
    total_price = _get_value(order_result, "total_price", 0.0)

    if overall_status == "created":
        points.append(f"Confirm order creation for {fulfilled_count} item(s).")
        for item_data in order_items:
            item_name = _get_value(item_data, "product_name", "Unknown Item")
            fulfilled_qty = _get_value(item_data, "quantity_fulfilled", 0)
            requested_qty = _get_value(item_data, "quantity_requested", 0)
            item_status = _get_value(item_data, "status", "unknown")
            promo = _get_value(item_data, "promotion_details", None)

            if item_status == "created":
                points.append(f"Confirm {fulfilled_qty} x {item_name} has been ordered.")
                if promo:
                    points.append(f"Mention applied promotion for {item_name}: {promo}")
            elif item_status == "out_of_stock":
                points.append(f"Inform that {item_name} (requested {requested_qty}) is out of stock.")
    
    # Add points for alternatives if any
    if alternatives:
        points.append("Suggest alternative products for out-of-stock items.")
        for alt_info in alternatives:
            orig_name = _get_value(alt_info, "original_product_name", "Original Item")
            sugg_name = _get_value(alt_info, "suggested_product_name", "Alternative Item")
            reason = _get_value(alt_info, "reason", "Similar product")
            points.append(f"For {orig_name}, suggest {sugg_name} because: {reason}")
    
    # Add points for processing notes
    if processing_notes:
        points.append("Additional notes:")
        # Check if processing_notes is a list of strings
        if isinstance(processing_notes, list) and all(isinstance(note, str) for note in processing_notes):
             points.append(chr(10).join(processing_notes))
        elif isinstance(processing_notes, str): # Handle if it's just a single string
             points.append(processing_notes)

    # Add information about total price if applicable
    if overall_status in ["created", "partially_fulfilled"] and total_price is not None:
        points.append(f"Mention the total price: ${total_price:.2f}") # Format price
    
    # General closing point
    points.append("Thank the customer for their business and offer further assistance")
    
    return points

def determine_greeting_style(tone_info: Dict[str, Any]) -> str:
    """
    Determine the appropriate greeting style based on tone analysis.
    
    Args:
        tone_info: Dictionary containing tone analysis information
        
    Returns:
        A greeting style string: "formal", "casual", "friendly", etc.
    """
    detected_tone = tone_info.get("tone", "neutral")
    formality_level = tone_info.get("formality_level", 3)
    
    if detected_tone == "formal" or formality_level >= 4:
        return "formal"
    elif detected_tone == "casual" and formality_level <= 2:
        return "casual"
    elif detected_tone == "friendly":
        return "friendly"
    elif detected_tone == "urgent":
        return "direct"
    else:
        # Default to a professional greeting
        return "professional"

def determine_closing_style(tone_info: Dict[str, Any]) -> str:
    """
    Determine the appropriate closing style based on tone analysis.
    
    Args:
        tone_info: Dictionary containing tone analysis information
        
    Returns:
        A closing style string: "formal", "casual", "warm", etc.
    """
    detected_tone = tone_info.get("tone", "neutral")
    formality_level = tone_info.get("formality_level", 3)
    
    if detected_tone == "formal" or formality_level >= 4:
        return "formal"
    elif detected_tone == "friendly":
        return "warm"
    elif detected_tone == "casual" and formality_level <= 2:
        return "casual"
    elif detected_tone == "urgent":
        return "efficient"
    else:
        # Default to a professional closing
        return "professional"

async def process_customer_signals(customer_signals: List[Dict[str, Any]], email_body: str, 
                                email_type: str, llm) -> List[str]:
    """
    Process customer signals to generate personalized response elements using an LLM.
    
    Args:
        customer_signals: List of detected customer signals
        email_body: The full email body text
        email_type: Type of email (order_request, product_inquiry)
        llm: Language model for processing
        
    Returns:
        List of personalization phrases to include in the response
    """
    if not customer_signals:
        return []
    
    # Create a prompt to process the signals
    signals_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""
        You're an expert in customer communication who understands sales psychology.
        Based on the customer signals in an email, suggest specific personalization phrases 
        that should be included in the response to build rapport and show understanding.
        
        Suggestions should be specific phrases (not just concepts), relevant to the email type,
        and phrased naturally as they would appear in the response.
        
        Limit your suggestions to 2-3 truly important phrases. Quality over quantity.
        """),
        HumanMessage(content=f"""
        Email Type: {email_type}
        
        Customer Signals Detected:
        {json.dumps(customer_signals, indent=2)}
        
        Email Excerpt:
        {email_body[:500]}... (truncated)
        
        Based on these signals, suggest 2-3 specific personalization phrases to include in my response.
        Return only the phrases, one per line.
        """)
    ])
    
    # Get personalization suggestions
    try:
        response = await (signals_prompt | llm | StrOutputParser()).ainvoke({})
        
        # Split into individual phrases
        phrases = [phrase.strip() for phrase in response.split('\n') if phrase.strip()]
        
        # Filter out any non-phrases or excessively long entries
        phrases = [phrase for phrase in phrases if 3 <= len(phrase.split()) <= 15]
        
        return phrases[:3]  # Limit to at most 3 phrases
        
    except Exception as e:
        print(f"Error processing customer signals: {e}")
        return []

async def verify_response_quality(response: str, email_body: str, email_subject: str,
                               response_points: List[str], email_type: str, 
                               tone_info: Dict[str, Any], llm) -> str:
    """
    Verify the quality and completeness of the generated response using an LLM.
    
    Args:
        response: The generated response text
        email_body: The original customer email
        email_subject: The subject of the customer email
        response_points: The points that should be covered
        email_type: Type of email (order_request, product_inquiry)
        tone_info: Dictionary containing tone analysis information
        llm: Language model for verification
        
    Returns:
        Verified (potentially improved) response text
    """
    # Check if the response is too short
    if len(response.split()) < 30:
        print("Response is too short, generating a more comprehensive version")
        # This likely indicates an issue with the generation - retry with a different approach
        return await generate_fallback_response(
            email_body=email_body,
            email_subject=email_subject,
            response_points=response_points,
            email_type=email_type,
            tone_info=tone_info,
            llm=llm
        )
    
    # Create a prompt to verify the response
    verification_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""
        You are a quality assurance specialist for customer email responses.
        Your job is to verify that a response meets all quality criteria:
        
        1. Contains all required information points
        2. Matches the appropriate tone and style
        3. Is natural and not template-like
        4. Is complete and professionally written
        5. Addresses the customer's concerns
        
        If the response needs improvements, provide a revised version.
        If it meets all criteria, return it unchanged.
        """),
        HumanMessage(content=f"""
        Original Customer Email Subject: {email_subject}
        
        Original Customer Email (excerpt):
        {email_body[:300]}... (truncated)
        
        Email Type: {email_type}
        
        Response Tone Information:
        {json.dumps(tone_info, indent=2)}
        
        Required Response Points:
        {chr(10).join(f"- {point}" for point in response_points)}
        
        Generated Response:
        {response}
        
        Evaluate the response against the quality criteria. If it meets all criteria, respond with "RESPONSE MEETS CRITERIA". 
        If it needs improvement, provide a revised and improved version (keeping the same general structure).
        """)
    ])
    
    # Get verification result
    verification_result = await (verification_prompt | llm | StrOutputParser()).ainvoke({})
    
    # Check if the response meets criteria
    if "RESPONSE MEETS CRITERIA" in verification_result:
        return response
    
    # Otherwise, the verification provided an improved version
    # Check that the response isn't just the verification text
    if len(verification_result.split()) > 20 and "Dear" in verification_result:
        return verification_result
    
    # If the verification result doesn't look like a proper response, return the original
    return response

async def generate_fallback_response(email_body: str, email_subject: str, response_points: List[str],
                                  email_type: str, tone_info: Dict[str, Any], llm) -> str:
    """
    Generate a fallback response when primary generation fails or needs supplementation.
    
    Args:
        email_body: The original customer email
        email_subject: The subject of the customer email
        response_points: The points that should be covered
        email_type: Type of email (order_request, product_inquiry)
        tone_info: Dictionary containing tone analysis information
        llm: Language model for generation
        
    Returns:
        Fallback response text
    """
    # Create a direct prompt for response generation
    fallback_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=f"""
        You are a helpful, friendly customer service representative for a fashion retail store.
        Generate a professional response in {tone_info.get('tone', 'professional')} tone
        with formality level {tone_info.get('formality_level', 3)} (1=very casual, 5=very formal).
        
        Your response must include ALL the following information points, presented naturally:
        {chr(10).join(f"- {point}" for point in response_points)}
        
        Make the response personal, friendly, and conversational, not robotic or template-like.
        """),
        HumanMessage(content=f"""
        Customer Email Subject: {email_subject}
        
        Customer Email:
        {email_body}
        
        Write a complete, helpful response addressing all required points.
        """)
    ])
    
    # Generate fallback response
    fallback_response = await (fallback_prompt | llm | StrOutputParser()).ainvoke({})
    
    return fallback_response

# Keep extract_customer_name defined locally in this file for now
def extract_customer_name(email_body: str) -> Optional[str]:
    """Extract customer name from email body."""
    # Placeholder implementation: Use LLM or regex
    # ... existing code ...

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