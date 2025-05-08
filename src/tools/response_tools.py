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
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re

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
    response_points: List[str] = Field(description="Key points to include in the response.")
    tone_info: Dict[str, Any] = Field(description="Parameters for matching customer's tone.")
    answer_phrases: List[str] = Field(default_factory=list, description="Specific phrases to include in answers.")
    closing_style: str = Field(description="Style of closing based on email: 'formal', 'warm', 'enthusiastic', etc.")
    language: str = Field(default="English", description="Language to use for the response.")

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
    # This is a simplified implementation that would be replaced with an LLM call
    # The LLM would analyze the text and return structured tone information
    
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
    
    # This is a simplified implementation that would be replaced with an LLM call
    # The LLM would identify explicit and implicit questions and return structured data
    
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

@tool
def generate_natural_response(
    customer_name: Optional[str], 
    greeting_style: str,
    response_points: List[str],
    tone_info: Dict[str, Any],
    answer_phrases: List[str],
    closing_style: str,
    language: str = "English"
) -> str:
    """    Generate a natural, human-like response based on provided components.
    This creates a high-quality response that follows the specified tone and content guidelines.
    
    Args:
        customer_name: Customer's name if available
        greeting_style: Style of greeting ('formal', 'casual', etc.)
        response_points: Key points to include in the response
        tone_info: Dictionary with tone parameters (tone, formality_level, writing_style)
        answer_phrases: Specific phrases to include in answers
        closing_style: Style of closing ('formal', 'warm', etc.)
        language: Language to use for the response
        
    Returns:
        A string containing the generated natural language response.
    """
    # In a real implementation, this would use the provided LLM to generate a response
    # based on the composition plan. Below is a simplified implementation to demonstrate
    # how the response might be structured without making an actual LLM call.
    
    # Build system prompt for the LLM
    system_prompt = f"""
    You are a helpful, friendly customer service representative for a fashion retail store.
    Generate a {tone_info.get('tone', 'professional')} response in {language} 
    with formality level {tone_info.get('formality_level', 3)} (1=very casual, 5=very formal).
    
    The response should:
    1. Use a {greeting_style} greeting
    2. Address all the following points: {', '.join(response_points)}
    3. Match the customer's communication style
    4. Close with a {closing_style} sign-off
    5. Be natural and conversational, not overly template-like
    
    IMPORTANT:
    - Avoid phrases like "based on your inquiry" or "as per your request"
    - Use contractions as appropriate for the formality level
    - Include specific product details where relevant
    - Make the response personal and warm, not robotic
    """
    
    # Create user prompt
    user_prompt = f"""
    Write a response to a customer with the following requirements:
    
    Customer name: {customer_name if customer_name else 'Valued Customer'}
    
    Response points to include:
    {chr(10).join(f'- {point}' for point in response_points)}
    
    Specific phrases to include (where natural):
    {chr(10).join(f'- {phrase}' for phrase in answer_phrases) if answer_phrases else '- None specified'}
    
    Tone matching:
    - Detected tone: {tone_info.get('tone', 'neutral')}
    - Formality level: {tone_info.get('formality_level', 3)}
    - Writing style: {tone_info.get('writing_style', 'conversational')}
    
    Response language: {language}
    """
    
    # In a real implementation, we would call the LLM here:
    # response = llm.invoke([
    #    {"role": "system", "content": system_prompt},
    #    {"role": "user", "content": user_prompt}
    # ])
    # return response.content
    
    # For now, we'll just return a placeholder response that reflects the structure
    greeting = "Dear Valued Customer" if greeting_style == "formal" else "Hi there"
    if customer_name:
        greeting = f"{greeting}, {customer_name}"
    
    body_paragraphs = []
    for point in response_points:
        body_paragraphs.append(f"{point}")
    
    closing = "Sincerely" if closing_style == "formal" else "Best regards"
    signature = "The Fashion Store Team"
    
    return f"{greeting},\n\n{chr(10).join(body_paragraphs)}\n\n{closing},\n{signature}"

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