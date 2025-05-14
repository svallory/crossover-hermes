""" {cell}
## Email Analyzer Agent

This agent serves as the first step in the email processing pipeline. Its primary 
responsibilities are:
1. Classify the email as either a "product_inquiry" or an "order_request"
2. Detect the language of the email
3. Analyze the tone and style of the customer's writing
4. Extract all product references (IDs, names, descriptions)
5. Identify customer signals (purchase intent, emotion, context, etc.)

This comprehensive analysis establishes the context for all subsequent processing.
"""
from typing import Optional, Dict, Any, List, Annotated
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel

# Project imports
from ..config import HermesConfig
from ..llm_client import get_llm_client
from ..state import HermesState
from ..model.common import (
    ProductReference, 
    CustomerSignal, 
    EmailType, 
    ToneAnalysis
)
from ..prompts import email_analyzer_md, email_analysis_verification_md

# Define EmailAnalysis Pydantic model here
class EmailAnalysis(BaseModel):
    """Comprehensive structured analysis of a customer email."""
    classification: EmailType = Field(description="Primary classification: 'product_inquiry' or 'order_request'")
    classification_confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Confidence in the classification (0.0-1.0)")]
    classification_evidence: str = Field(description="Key text that determined the classification")
    language: str = Field(description="Detected language of the email")
    customer_name: Optional[str] = Field(default=None, description="Customer's first name if identifiable from common greetings (e.g., Hi John, Dear Jane). Case-insensitive.")
    tone_analysis: ToneAnalysis = Field(description="Analysis of customer's tone and writing style")
    product_references: List[ProductReference] = Field(default_factory=list, description="List of all detected product references")
    customer_signals: List[CustomerSignal] = Field(default_factory=list, description="List of all detected customer signals")
    reasoning: str = Field(description="Reasoning behind the classification")

# Reusing models from state.py to ensure consistency
# In a real implementation, these could be imported from a shared location

async def analyze_email_node(state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    LangGraph node function for the Email Analyzer Agent.
    Analyzes an email to determine its intent, extract product references, and identify customer signals.
    
    Args:
        state: The current state dictionary from LangGraph
        config: Optional configuration parameters
        
    Returns:
        Updated state dictionary with email_analysis field
    """
    # Reconstruct typed state object for better type safety
    # (This is optional since we're accessing simple fields, but demonstrates the pattern)
    typed_state = HermesState(
        email_id=state.get("email_id", "unknown"),
        email_subject=state.get("email_subject", ""),
        email_body=state.get("email_body", ""),
        product_catalog_df=state.get("product_catalog_df"),
        vector_store=state.get("vector_store")
    )
    
    # Extract configuration
    if config and "configurable" in config and "hermes_config" in config["configurable"]:
        hermes_config = config["configurable"]["hermes_config"]
    else:
        hermes_config = HermesConfig()
    
    # Extract email data from typed state
    email_id = typed_state.email_id
    email_subject = typed_state.email_subject
    email_body = typed_state.email_body
    
    # Log processing start
    print(f"Analyzing email {email_id}")
    
    # Initialize LLM with appropriate parameters using the utility function
    llm = get_llm_client(
        config=hermes_config, 
        temperature=hermes_config.llm_classification_temperature
    )
    
    # Create the analysis chain with structured output
    email_analyzer_prompt = PromptTemplate.from_template(email_analyzer_md, template_format="mustache")
    
    # Create the verification prompt template
    email_analysis_verification_prompt_template = PromptTemplate.from_template(email_analysis_verification_md, template_format="mustache")
    
    analysis_chain = email_analyzer_prompt | llm.with_structured_output(EmailAnalysis)
    
    try:
        # Invoke the analysis chain
        analysis_result: EmailAnalysis = await analysis_chain.ainvoke({
            "subject": email_subject,
            "body": email_body
        })
        
        # Verify the result
        verified_result = await verify_email_analysis(analysis_result, llm, email_subject, email_body)
        
        # Return the updated state
        return {"email_analysis": verified_result.model_dump()}
        
    except Exception as e:
        # Handle errors gracefully
        print(f"Error analyzing email {email_id}: {e}")
        # Create a fallback analysis
        fallback_analysis = EmailAnalysis(
            classification="product_inquiry",  # Default to inquiry as safer option
            classification_confidence=0.5,
            classification_evidence="Error occurred during analysis",
            language="unknown",
            tone_analysis=ToneAnalysis(
                tone="neutral",
                formality_level=3,
                key_phrases=[]
            ),
            product_references=[],
            customer_signals=[],
            reasoning=f"Error analyzing email: {str(e)}"
        )
        
        return {"email_analysis": fallback_analysis.model_dump()}

# Trade-off Note: Verification vs. Initial Prompt Quality
# -------------------------------------------------------------------
# The approach used here represents a trade-off between two strategies:
#
# 1. Two-pass approach (current implementation):
#    - First pass: Generate analysis with the primary prompt
#    - Second pass: Verify and correct with a separate LLM call
#
# 2. Single robust prompt approach (alternative):
#    - Invest more effort in a highly robust initial prompt with examples and constraints
#    - Skip verification step entirely and trust the initial output
#
# Advantages of current approach:
# - More robust to edge cases and unexpected inputs
# - Easier to maintain (verification logic is separate from generation)
# - Provides a safety net for downstream agents
#
# Disadvantages:
# - Additional LLM call = higher cost
# - Increased latency (sequential API calls)
# - Potential for conflicting fixes that could change semantics
#
# When to consider the alternative approach:
# - In high-throughput or latency-sensitive environments
# - When API costs are a significant concern
# - When the initial prompt can be extensively tested with diverse inputs
#
# In a production environment with real users, the verification step likely 
# provides more value than its cost, especially when processing mission-critical
# emails where errors could impact customer satisfaction.
async def verify_email_analysis(analysis: EmailAnalysis, llm: BaseChatModel, 
                               email_subject: str, email_body: str) -> EmailAnalysis:
    """
    Verify the email analysis output using an LLM to check for semantic issues and completeness.
    Pydantic models handle basic structural and type validation.
    This function focuses on ensuring the LLM review of excerpts, customer name, and overall coherence.
    
    Args:
        analysis: The initial EmailAnalysis result (already passed Pydantic validation)
        llm: The language model to use for verification/correction
        email_subject: Original email subject for context
        email_body: Original email body for context
        
    Returns:
        Verified (potentially corrected) EmailAnalysis
    """
    # Python-based validation_errors list and its population are removed.
    # The LLM will perform these checks based on the updated prompt.
    print("Verifying email analysis using LLM...")

    # The errors_found_str is part of the prompt but will be less critical as LLM does a full review.
    # We can pass a generic message or an empty string if no pre-LLM checks are done.
    # For consistency with the prompt, let's pass an empty string, implying LLM should do a full review.
    errors_found_str = "N/A - LLM performing full review based on system prompt instructions."

    verification_prompt_payload = {
        "email_subject": email_subject,
        "email_body": email_body,
        "original_analysis_json": analysis.model_dump_json(), # Pass as JSON string
        "errors_found_str": errors_found_str, temp 
    }
    
    verification_prompt = email_analysis_verification_prompt_template.invoke(verification_prompt_payload)
    
    try:
        # Create structured output for the verification step
        corrector = verification_prompt | llm.with_structured_output(EmailAnalysis)
        
        # Ask LLM to fix the errors
        fixed_analysis = await corrector.ainvoke({})
        # Basic check if the LLM made changes or just returned the same analysis
        if fixed_analysis.model_dump() != analysis.model_dump():
            print("Email analysis verification: LLM suggested revisions.")
        else:
            print("Email analysis verification: LLM confirmed analysis quality or made no major changes.")
        return fixed_analysis
    except Exception as e:
        print(f"Email analysis verification: Failed to fix/review issues with LLM: {e}")
        # Fallback to original analysis, but add a note to reasoning about the failure.
        # Ensure reasoning exists and is a string.
        current_reasoning = analysis.reasoning if analysis.reasoning is not None else ""
        analysis.reasoning = f"{current_reasoning} [LLM Verification Step Failed: {str(e)}]"
        return analysis

""" {cell}
### Email Analyzer Agent Implementation Notes

The Email Analyzer Agent serves as the critical first step in our email processing pipeline. It determines how an email will be routed and processed throughout the system by:

1. **Classification Logic**:
   - The agent classifies each email as either a "product_inquiry" or an "order_request"
   - Even emails with mixed elements receive a single primary classification
   - Classification is done with a low temperature setting (0.0) for consistency

2. **Structural Design**:
   - Uses Pydantic models for structured output (`EmailAnalysis` and its components)
   - The `analyze_email_node` function is designed to be used as a LangGraph node
   - Error handling ensures the pipeline can continue even if analysis fails

3. **Verification Step**:
   - `verify_email_analysis` checks the output for errors
   - If issues are found, a second LLM call attempts to correct them
   - This improves reliability and ensures downstream agents receive valid data

4. **Language & Tone Detection**:
   - Automatically identifies the email's language (supports multi-language)
   - Analyzes tone and formality to guide response style matching

5. **Signal Processing**:
   - Extracts customer signals based on the sales intelligence framework
   - These signals help personalize responses and understand customer context

This agent provides the foundation for all subsequent processing, ensuring high-quality inputs for the Order Processor, Inquiry Responder, and Response Composer agents.
""" 

