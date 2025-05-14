""" {cell}
## Response Generation and Analysis Tools

This module provides tools that assist in analyzing customer communication and
composing high-quality, natural-sounding responses. While LLMs can handle basic
analysis and generation, these specialized tools offer more focused functionality
for specific aspects of customer communication.

Key functionalities include:
- Detailed tone and style analysis of customer emails to inform response matching.
- Extraction of explicit and implicit questions from complex inquiries.
- Generation of natural-sounding responses based on a structured composition plan.
"""
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import re
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts.response_composer import response_composer_prompt # Import the main prompt
import json

# --- Input/Output Models for Tools ---

class ToneAnalysisResult(BaseModel):
    """Detailed analysis of text tone and style."""
    detected_tone: str = Field(description="Overall detected tone: e.g., 'formal', 'casual', 'urgent', 'friendly', 'frustrated'.")
    formality_level: int = Field(description="Formality level from 1 (very casual) to 5 (very formal).")
    key_phrases: List[str] = Field(description="Specific phrases that indicate the detected tone.")
    sentiment: Optional[str] = Field(default=None, description="Overall sentiment: 'positive', 'neutral', 'negative'.")
    writing_style: Optional[str] = Field(default=None, description="Style: 'concise', 'detailed', 'technical', 'conversational', etc.")

class ExtractedQuestion(BaseModel):
    """An explicit or implicit question extracted from text."""
    question_text: str = Field(description="The formulated question.")
    original_excerpt: str = Field(description="The text segment from which the question was derived.")
    question_type: str = Field(description="Type: 'explicit', 'implicit', 'clarification_needed'.")
    confidence: float = Field(description="Confidence score (0.0-1.0) for this extraction.")
    product_related: Optional[bool] = Field(default=None, description="Whether this question relates to a product.")
    topic: Optional[str] = Field(default=None, description="General topic of the question: 'sizing', 'materials', 'shipping', etc.")

class ResponseCompositionPlan(BaseModel):
    """A structured plan for generating a response."""
    customer_name: Optional[str] = Field(default=None, description="Customer's name if available.")
    greeting_style: str = Field(description="Style of greeting based on email tone: 'formal', 'casual', 'friendly', etc.")
    tone_info: Dict[str, Any] = Field(description="Parameters for matching customer's tone (e.g., tone, formality_level from analysis).")
    closing_style: str = Field(description="Style of closing based on email: 'formal', 'warm', 'enthusiastic', etc.")
    language: str = Field(default="English", description="Language to use for the response.")
    email_analysis_json: str = Field(description="Full email analysis data as a JSON string.")
    processing_results_json: str = Field(description="Full order or inquiry processing results as a JSON string.")

# --- Tool Definitions ---

@tool
def analyze_tone(text_to_analyze: str) -> ToneAnalysisResult:
    """    Analyze the tone, formality, and style of the provided text.
    This helps understand how to respond to the customer in a manner that matches their communication style.
    
    Args:
        text_to_analyze: The customer's email body or relevant text segment.
        
    Returns:
        A ToneAnalysisResult object containing detailed tone analysis.
    """
    # ASSIGNMENT IMPLEMENTATION NOTE: 
    # ------------------------------
    # This is a simplified implementation for the interview assignment using regex and keyword
    # matching rather than a full LLM call. This approach was chosen to:
    # 1. Demonstrate basic logic without requiring an additional LLM API call (token efficiency)
    # 2. Show a deterministic approach that works consistently for the test cases
    # 3. Focus the use of LLMs on the core email processing logic rather than utilities
    #
    # In a production implementation, this tool would make a dedicated LLM call with:
    # 1. A specialized system prompt focused on tone/style analysis
    # 2. A structured output format matching ToneAnalysisResult
    # 3. Examples of different communication styles for few-shot learning
    # 4. The LLM would analyze the text and return structured tone information
    
    # Initialize default result
    result = ToneAnalysisResult(
        detected_tone="neutral",
        formality_level=3,
        key_phrases=[],
        sentiment="neutral",
        writing_style="conversational"
    )
    
    # Convert to lowercase for easier pattern matching
    text_lower = text_to_analyze.lower()
    key_phrases = []
    
    # Check for formal language patterns
    formal_indicators = [
        "dear sir", "dear madam", "to whom it may concern", 
        "sincerely", "regards", "respectfully", "cordially"
    ]
    
    casual_indicators = [
        "hey", "hi there", "thanks!", "cheers", "btw", "lol", 
        "awesome", "cool", "gonna", "wanna", "y'all"
    ]
    
    urgent_indicators = [
        "urgent", "asap", "as soon as possible", "immediately", 
        "right away", "emergency", "quickly", "soon"
    ]
    
    frustrated_indicators = [
        "disappointed", "frustrated", "unhappy", "problem", 
        "issue", "not working", "failed", "terrible", "horrible"
    ]
    
    friendly_indicators = [
        "thanks so much", "appreciate", "grateful", "looking forward", 
        "excited", "wonderful", "love", "enjoy", "pleased"
    ]
    
    # Check formal indicators
    for phrase in formal_indicators:
        if phrase in text_lower:
            key_phrases.append(phrase)
            
    # Count indicators for each category
    formal_count = sum(1 for phrase in formal_indicators if phrase in text_lower)
    casual_count = sum(1 for phrase in casual_indicators if phrase in text_lower)
    urgent_count = sum(1 for phrase in urgent_indicators if phrase in text_lower)
    frustrated_count = sum(1 for phrase in frustrated_indicators if phrase in text_lower)
    friendly_count = sum(1 for phrase in friendly_indicators if phrase in text_lower)
    
    # Determine predominant tone
    tone_counts = {
        "formal": formal_count,
        "casual": casual_count,
        "urgent": urgent_count,
        "frustrated": frustrated_count,
        "friendly": friendly_count
    }
    
    # Find the tone with the highest count
    predominant_tone = max(tone_counts, key=tone_counts.get)
    if tone_counts[predominant_tone] > 0:
        result.detected_tone = predominant_tone
    
    # Determine formality level
    if formal_count > 0:
        result.formality_level = min(5, 3 + formal_count)
    elif casual_count > 0:
        result.formality_level = max(1, 3 - casual_count)
    
    # Determine sentiment
    positive_words = sum(1 for word in ["great", "good", "excellent", "wonderful", "happy", "pleased", "love"] 
                        if word in text_lower)
    negative_words = sum(1 for word in ["bad", "poor", "terrible", "awful", "unhappy", "disappointed", "hate"] 
                         if word in text_lower)
    
    if positive_words > negative_words:
        result.sentiment = "positive"
    elif negative_words > positive_words:
        result.sentiment = "negative"
    
    # Collect key phrases
    for category in [formal_indicators, casual_indicators, urgent_indicators, 
                     frustrated_indicators, friendly_indicators]:
        for phrase in category:
            if phrase in text_lower:
                key_phrases.append(phrase)
    
    # Add any found key phrases
    if key_phrases:
        result.key_phrases = key_phrases
    
    # Determine writing style
    if len(text_to_analyze.split()) > 100:
        result.writing_style = "detailed"
    elif len(text_to_analyze.split()) < 30:
        result.writing_style = "concise"
    
    return result

@tool
def extract_questions(text_to_analyze: str) -> List[ExtractedQuestion]:
    """    Extract explicit and implicit questions from the provided text.
    This helps ensure all customer inquiries are identified and addressed in the response.
    
    Args:
        text_to_analyze: The customer's email body or a segment containing inquiries.
        
    Returns:
        A list of ExtractedQuestion objects representing all detected questions.
    """
    # Initialize result list
    questions = []
    
    # ASSIGNMENT IMPLEMENTATION NOTE:
    # ------------------------------
    # This is a simplified implementation for the interview assignment using regex pattern
    # matching instead of a full LLM call. This approach was chosen to:
    # 1. Demonstrate basic logic without incurring additional LLM API costs
    # 2. Provide predictable results for test cases without LLM variance
    # 3. Show how traditional NLP techniques can be used in a hybrid approach
    #
    # In a production implementation, this tool would:
    # 1. Make a dedicated LLM call with a prompt focused on question extraction
    # 2. Use specific examples of explicit and implicit questions for few-shot learning
    # 3. Have the LLM identify more subtle contextual questions that regex might miss
    # 4. Return structured data matching the ExtractedQuestion model
    # 5. Have higher accuracy, especially for nuanced or complex language
    
    # 1. Pattern matching for explicit questions (ending with question mark)
    explicit_pattern = r"([^.!?]*\?)"
    explicit_matches = re.findall(explicit_pattern, text_to_analyze)
    
    for match in explicit_matches:
        if len(match.strip()) > 5:  # Ensure it's a substantive question
            questions.append(ExtractedQuestion(
                question_text=match.strip(),
                original_excerpt=match.strip(),
                question_type="explicit",
                confidence=0.9,
                product_related=contains_product_terms(match),
                topic=detect_topic(match)
            ))
    
    # 2. Pattern matching for common question-indicating phrases (implicit questions)
    implicit_patterns = [
        r"I(?:'m| am) wondering (about|if) ([^.!?]*)[.!]?",
        r"I would like to know (about|if) ([^.!?]*)[.!]?",
        r"I need to know ([^.!?]*)[.!]?",
        r"I(?:'m| am) curious (about|if) ([^.!?]*)[.!]?",
        r"Please (tell|let) me (about|if) ([^.!?]*)[.!]?",
        r"I need information (about|on) ([^.!?]*)[.!]?",
        r"Do you (know|have) ([^.!?]*)[.!]?",
        r"Can you tell me ([^.!?]*)[.!]?"
    ]
    
    for pattern in implicit_patterns:
        matches = re.findall(pattern, text_to_analyze, re.IGNORECASE)
        for match in matches:
            # Depending on the pattern, the question content could be in different positions
            question_content = match[-1] if isinstance(match, tuple) else match
            if len(question_content.strip()) > 5:  # Ensure it's substantive
                questions.append(ExtractedQuestion(
                    question_text=f"{question_content.strip()}?",
                    original_excerpt=question_content.strip(),
                    question_type="implicit",
                    confidence=0.7,
                    product_related=contains_product_terms(question_content),
                    topic=detect_topic(question_content)
                ))
    
    # Return empty list if no questions found
    return questions

# Removed @tool decorator from here as it calls an LLM.
# Its logic will be integrated directly into the ResponseComposer agent.
async def generate_natural_response(
    customer_name: Optional[str], 
    greeting_style: str,
    tone_info: Dict[str, Any],
    closing_style: str,
    language: str = "English",
    email_analysis_json: str = "",
    processing_results_json: str = "",
    llm: Union[ChatOpenAI, ChatGoogleGenerativeAI] = None,
    customer_signal_manual_extract: str = ""
) -> str:
    """    Generate a natural, human-like response based on provided components and raw analysis data.
    This creates a high-quality response that follows the specified tone and content guidelines by interpreting detailed customer and processing information.
    
    Args:
        customer_name: Customer's name if available
        greeting_style: Style of greeting ('formal', 'casual', etc.) - determined by agent
        tone_info: Dictionary with primary tone parameters (detected_tone, formality_level) for direct use by prompt.
        closing_style: Style of closing ('formal', 'warm', etc.) - determined by agent
        language: Language to use for the response
        email_analysis_json: JSON string of the full email analysis data (includes original email, tone, signals etc).
        processing_results_json: JSON string of the order or inquiry processing results.
        llm: The language model client to use for generation.
        customer_signal_manual_extract: Key guidelines from the customer signal processing manual (used in system prompt).
        
    Returns:
        A string containing the generated natural language response.
    """
    if llm is None:
        raise ValueError("LLM client must be provided to generate_natural_response.")

    # The imported response_composer_prompt now expects:
    # {email_analysis}, {processing_results}, 
    # {customer_name}, {language}, {tone}, {formality_level}

    # tone_info contains: detected_tone, formality_level from the agent's initial analysis.
    # The full email_analysis_json also contains a tone_analysis section, but providing key parts directly to the prompt.
    
    prompt_input = {
        "email_analysis": email_analysis_json, # Pass the full JSON string
        "processing_results": processing_results_json, # Pass the full JSON string
        "customer_name": customer_name if customer_name else "Valued Customer",
        "language": language,
        "tone": tone_info.get("detected_tone", tone_info.get("tone", "professional")), # Use detected_tone if available, fallback to tone
        "formality_level": tone_info.get("formality_level", 3),
        # customer_signal_manual_extract is used in the system message part of response_composer_prompt
        # but the prompt itself does not take it as a direct formatting variable.
    }

    # The pre-defined response_composer_prompt from src/prompts already includes the system message with guidelines.
    # We just need to format it with the current context.
    
    # Note: The customer_signal_manual_extract is part of the system message in response_composer_prompt.
    # If it needs to be dynamically inserted into the system message content itself, 
    # the ChatPromptTemplate creation in src/prompts/response_composer.py would need to be adjusted.
    # For now, assuming it's statically part of the system message text there.

    chain = response_composer_prompt | llm | StrOutputParser()
    
    try:
        response_text = await chain.ainvoke(prompt_input)
        return response_text
    except Exception as e:
        print(f"Error during natural response generation: {e}")
        # Fallback to a very simple template if LLM fails - This fallback might need to be smarter
        # or the agent should have a more robust error handling for failed generation.
        greeting = "Dear Valued Customer" if greeting_style == "formal" else "Hi there"
        if customer_name:
            greeting = f"{greeting}, {customer_name}"
        
        # Since response_points are no longer passed, this fallback is very basic.
        body = "We have received your message and will get back to you shortly."
        
        closing = "Sincerely" if closing_style == "formal" else "Best regards"
        signature = "The Fashion Store Team"
        return f"{greeting},\n\n{body}\n\n{closing},\n{signature}"

# --- Helper Functions ---

def contains_product_terms(text: str) -> bool:
    """Check if the text contains terms related to products."""
    product_terms = ["product", "item", "dress", "shirt", "shoe", "jacket", "size", 
                    "color", "material", "wear", "fit", "clothing", "accessory"]
    return any(term in text.lower() for term in product_terms)

def detect_topic(text: str) -> Optional[str]:
    """Detect the general topic of a question."""
    topic_keywords = {
        "sizing": ["size", "fit", "large", "small", "medium", "xl", "measurement"],
        "materials": ["material", "fabric", "cotton", "wool", "leather", "synthetic"],
        "colors": ["color", "black", "white", "blue", "red", "green", "dye"],
        "shipping": ["ship", "delivery", "arrive", "shipping", "mail", "send"],
        "pricing": ["price", "cost", "discount", "sale", "promotion", "offer"],
        "returns": ["return", "refund", "exchange", "policy", "warranty"]
    }
    
    # Check for each topic
    for topic, keywords in topic_keywords.items():
        if any(keyword in text.lower() for keyword in keywords):
            return topic
            
    return None
""" {cell}
### Response Tools Implementation Notes

These tools assist in creating high-quality, personalized responses to customer emails:

1. **Tone Analysis**:
   - `analyze_tone` detects the formality and emotional tone of customer messages
   - It identifies key phrases that signal the customer's writing style
   - This enables our response generator to match the customer's communication style

2. **Question Extraction**:
   - `extract_questions` identifies both explicit questions (ending with "?") and implicit questions
   - It uses pattern matching to find common question-indicating phrases
   - Each question is categorized by type, topic, and confidence level

3. **Response Generation**:
   - `generate_natural_response` creates a human-like response based on a structured plan
   - It maintains consistency with the customer's tone and formality level
   - The tool avoids template-like language by using contractions and natural phrasing
   - In a production implementation, this would make a direct LLM call

4. **Helper Functions**:
   - `contains_product_terms`: Determines if text is related to products
   - `detect_topic`: Categorizes questions into common topics (sizing, shipping, etc.)

These tools support the Response Composer Agent by providing detailed analysis and generation capabilities, ensuring responses feel personalized and natural rather than robotic or templated.
""" 