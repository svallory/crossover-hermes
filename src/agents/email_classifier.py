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
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_openai import ChatOpenAI
from ..config import HermesConfig
# Import the new LLM client utility
from ..llm_client import get_llm_client

# Reusing models from state.py to ensure consistency
# In a real implementation, these could be imported from a shared location
class ProductReference(BaseModel):
    """A single product reference extracted from an email."""
    reference_text: str = Field(description="Original text from email referencing the product")
    reference_type: str = Field(description="Type: 'product_id', 'product_name', 'description', or 'category'")
    product_id: Optional[str] = Field(default=None, description="Extracted or inferred product ID if available")
    product_name: Optional[str] = Field(default=None, description="Extracted or inferred product name if available")
    quantity: int = Field(default=1, description="Requested quantity, defaults to 1 if not specified")
    confidence: float = Field(description="Confidence in the extraction/match (0.0-1.0)")
    excerpt: str = Field(description="The exact text phrase from the email that contains this reference")

class CustomerSignal(BaseModel):
    """A customer signal detected in the email, based on the sales intelligence framework."""
    signal_type: str = Field(description="Type of customer signal detected")
    signal_category: str = Field(description="Category from sales intelligence framework") 
    signal_text: str = Field(description="The specific text in the email that indicates this signal")
    signal_strength: float = Field(description="Perceived strength or confidence in this signal (0.0-1.0)")
    excerpt: str = Field(description="The exact text phrase from the email that triggered this signal detection")

class ToneAnalysis(BaseModel):
    """Analysis of the customer's tone and writing style."""
    tone: str = Field(description="Overall detected tone")
    formality_level: int = Field(description="Formality level from 1 (very casual) to 5 (very formal)")
    key_phrases: List[str] = Field(description="Key phrases from the email that informed the tone analysis")

class EmailAnalysis(BaseModel):
    """Comprehensive structured analysis of a customer email."""
    classification: str = Field(description="Primary classification: 'product_inquiry' or 'order_request'")
    classification_confidence: float = Field(description="Confidence in the classification (0.0-1.0)")
    classification_evidence: str = Field(description="Key text that determined the classification")
    language: str = Field(description="Detected language of the email")
    tone_analysis: ToneAnalysis = Field(description="Analysis of customer's tone and writing style")
    product_references: List[ProductReference] = Field(default_factory=list, description="List of all detected product references")
    customer_signals: List[CustomerSignal] = Field(default_factory=list, description="List of all detected customer signals")
    reasoning: str = Field(description="Reasoning behind the classification")

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
    # Extract configuration
    if config and "configurable" in config and "hermes_config" in config["configurable"]:
        hermes_config = config["configurable"]["hermes_config"]
    else:
        hermes_config = HermesConfig()
    
    # Extract email data from state - handle both Dict and HermesState
    if hasattr(state, 'email_id'):
        # It's a HermesState object
        email_id = state.email_id if hasattr(state, 'email_id') else "unknown"
        email_subject = state.email_subject if hasattr(state, 'email_subject') else ""
        email_body = state.email_body if hasattr(state, 'email_body') else ""
    else:
        # It's a dictionary
        email_id = state.get("email_id", "unknown")
        email_subject = state.get("email_subject", "")
        email_body = state.get("email_body", "")
    
    # Log processing start
    print(f"Analyzing email {email_id}")
    
    # Initialize LLM with appropriate parameters using the utility function
    llm = get_llm_client(
        config=hermes_config, 
        temperature=hermes_config.llm_classification_temperature
    )
    
    # Create parser for structured output
    output_parser = PydanticOutputParser(pydantic_object=EmailAnalysis)
    
    # Import the prompt template
    from ..prompts.email_classifier import email_analyzer_prompt
    
    # Create the analysis chain
    analysis_chain = email_analyzer_prompt | llm | output_parser
    
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

async def verify_email_analysis(analysis: EmailAnalysis, llm: ChatOpenAI, 
                               email_subject: str, email_body: str) -> EmailAnalysis:
    """
    Verify the email analysis output and fix any issues.
    
    Args:
        analysis: The initial EmailAnalysis result
        llm: The language model to use for verification/correction
        email_subject: Original email subject for context
        email_body: Original email body for context
        
    Returns:
        Verified (potentially corrected) EmailAnalysis
    """
    # Check for basic validation issues
    validation_errors = []
    
    # 1. Verify classification is one of the required values
    if analysis.classification not in ["product_inquiry", "order_request"]:
        validation_errors.append(f"Invalid classification: '{analysis.classification}'. Must be 'product_inquiry' or 'order_request'.")
    
    # 2. Verify product references have required fields
    for i, ref in enumerate(analysis.product_references):
        if ref.reference_type not in ["product_id", "product_name", "description", "category"]:
            validation_errors.append(f"Product reference {i} has invalid reference_type: '{ref.reference_type}'")
        if not ref.excerpt:
            validation_errors.append(f"Product reference {i} is missing excerpt from email")
    
    # 3. Verify customer signals have required fields
    for i, signal in enumerate(analysis.customer_signals):
        if not signal.signal_type or not signal.signal_category:
            validation_errors.append(f"Customer signal {i} is missing required fields")
        if not signal.excerpt:
            validation_errors.append(f"Customer signal {i} is missing excerpt from email")
    
    # 4. Check confidence values are between 0 and 1
    if not (0 <= analysis.classification_confidence <= 1):
        validation_errors.append(f"Classification confidence should be between 0 and 1, got {analysis.classification_confidence}")
    
    # If there are validation errors, ask the LLM to fix them
    if validation_errors:
        # Construct verification prompt
        verification_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
            You are a verification assistant for email analysis. Your job is to fix issues in the structured analysis
            of customer emails. Review the original analysis and fix all the errors that have been identified.
            Produce a complete, corrected output that follows the required format.
            """),
            HumanMessage(content=f"""
            Original email subject: {email_subject}
            Original email body: {email_body}
            
            Original analysis: {json.dumps(analysis.model_dump(), indent=2)}
            
            Errors found:
            {chr(10).join(f"- {err}" for err in validation_errors)}
            
            Please fix these errors and return a complete corrected JSON that matches the EmailAnalysis schema.
            """)
        ])
        
        try:
            # Ask LLM to fix the errors
            fix_response = await (verification_prompt | llm | StrOutputParser()).ainvoke({})
            
            # Try to parse the fixed response
            fixed_analysis = EmailAnalysis.model_validate_json(fix_response)
            print("Email analysis verification: Errors fixed successfully")
            return fixed_analysis
        except Exception as e:
            # If parsing fails, return original with a warning
            print(f"Email analysis verification: Failed to fix errors: {e}")
            # We'll modify the reasoning field to note the verification issues
            analysis.reasoning += f" [Verification failed with errors: {', '.join(validation_errors)}]"
            return analysis
    
    # No validation errors found
    return analysis

def create_structured_output_chain(prompt, llm, output_schema):
    """
    Helper function to create a structured output chain using LangChain components.
    This is used for generating structured outputs from LLM calls.
    
    This function exists primarily to be mocked during testing.
    
    Args:
        prompt: The prompt template to use
        llm: The language model to use
        output_schema: The Pydantic schema for the output
        
    Returns:
        A callable chain that produces structured output
    """
    output_parser = PydanticOutputParser(pydantic_object=output_schema)
    return prompt | llm | output_parser
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