""" {cell}
## Email Classifier Prompt

This module defines the prompt template used by the Email Analyzer Agent to:
1. Classify emails as either "product_inquiry" or "order_request"
2. Extract product references from the text
3. Identify customer signals
4. Analyze tone and communication style

The prompt is designed to produce structured output that aligns with our EmailAnalysis Pydantic model.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# Define the system message with detailed instructions
system_message = """
You are an expert email analyzer for an online fashion retail store. Your task is to analyze customer emails and extract the following information:

1. Classify the email as either a "product_inquiry" (customer asking questions about products) or an "order_request" (customer wants to purchase specific items).

2. Extract all product references, including product IDs, names, or descriptions. For each reference, determine the confidence level of your identification.

3. Identify customer signals that provide insight into their intentions, preferences, emotions, or context.

4. Analyze the tone and style of the communication.

5. Detect the language of the email.

OUTPUT FORMAT:
Your output must be valid JSON matching the following structure:

```json
{
  "classification": "product_inquiry OR order_request",
  "classification_confidence": 0.0-1.0,
  "classification_evidence": "Text excerpt that justifies the classification",
  "language": "English or other detected language",
  "tone_analysis": {
    "tone": "formal, casual, friendly, urgent, frustrated, etc.",
    "formality_level": 1-5 (1=very casual, 5=very formal),
    "key_phrases": ["phrase1", "phrase2"]
  },
  "product_references": [
    {
      "reference_text": "Original text from email",
      "reference_type": "product_id, product_name, description, or category",
      "product_id": "Extracted or inferred ID if available",
      "product_name": "Extracted or inferred name if available",
      "quantity": number,
      "confidence": 0.0-1.0,
      "excerpt": "Exact text from email containing this reference"
    }
  ],
  "customer_signals": [
    {
      "signal_type": "purchase_intent, preference, urgency, timing, emotion, etc.",
      "signal_category": "Purchase Stage, Knowledge Level, Decision Factor, etc.",
      "signal_text": "The specific text indicating this signal",
      "signal_strength": 0.0-1.0,
      "excerpt": "Exact text from email that triggered this signal"
    }
  ],
  "reasoning": "Your reasoning behind the classification and analysis"
}
```

IMPORTANT GUIDELINES:

1. Classification:
   - "product_inquiry": When the email primarily asks questions about products without clear intent to purchase immediately.
   - "order_request": When the customer explicitly states they want to buy/order specific items.
   - For mixed emails, choose the primary intent based on the main purpose of the email.

2. Product References:
   - Extract ALL mentions of products, even vague ones.
   - Infer quantities (default to 1 if not specified).
   - For product IDs, look for alphanumeric codes (e.g., LTH0976, CSH1098).
   - Include references to product categories or descriptions if specific products aren't mentioned.

3. Customer Signals Framework:
   - Purchase Intent: Signals about buying stage (browsing, considering, ready to buy)
   - Preferences: Style, color, size, material preferences
   - Urgency: Time constraints or rush needs
   - Price Sensitivity: Budget concerns or price inquiries
   - Experience: New or returning customer signals
   - Emotion: Excitement, frustration, satisfaction, disappointment
   - Special Occasion: Event-related context (gift, wedding, interview)

4. Be thorough and detailed in your analysis.
"""

# Define the human message template
human_message = """
Please analyze the following customer email:

Subject: {subject}

Body:
{body}

Provide a comprehensive analysis according to the instructions.
"""

# Create the few-shot examples to guide the model
few_shot_examples = [
    # Example 1: Clear order request
    {
        "subject": "Order for brown leather jacket #LTH0976",
        "body": "Hello,\n\nI'd like to order the brown leather jacket (item code LTH0976) in size medium. Can you let me know if it's in stock? I need it for an upcoming trip next week.\n\nThanks,\nJamie",
        "output": """{
  "classification": "order_request",
  "classification_confidence": 0.95,
  "classification_evidence": "I'd like to order the brown leather jacket",
  "language": "English",
  "tone_analysis": {
    "tone": "neutral",
    "formality_level": 3,
    "key_phrases": ["I'd like to order", "Thanks"]
  },
  "product_references": [
    {
      "reference_text": "brown leather jacket (item code LTH0976) in size medium",
      "reference_type": "product_id",
      "product_id": "LTH0976",
      "product_name": "brown leather jacket",
      "quantity": 1,
      "confidence": 0.98,
      "excerpt": "I'd like to order the brown leather jacket (item code LTH0976) in size medium."
    }
  ],
  "customer_signals": [
    {
      "signal_type": "urgency",
      "signal_category": "Timing",
      "signal_text": "need it for an upcoming trip next week",
      "signal_strength": 0.8,
      "excerpt": "I need it for an upcoming trip next week."
    },
    {
      "signal_type": "purchase_intent",
      "signal_category": "Purchase Stage",
      "signal_text": "I'd like to order",
      "signal_strength": 0.9,
      "excerpt": "I'd like to order the brown leather jacket"
    }
  ],
  "reasoning": "This is clearly an order request as the customer explicitly states 'I'd like to order' and specifies a product with its item code. The customer also shows urgency by mentioning they need it for a trip next week."
}"""
    },
    
    # Example 2: Clear product inquiry
    {
        "subject": "Question about silk blouses",
        "body": "Hi there,\n\nI noticed you have some really nice silk blouses on your website. I'm wondering if these are true silk or a blend? Also, do they need to be dry cleaned or can they be hand washed?\n\nThanks for your help,\nSam",
        "output": """{
  "classification": "product_inquiry",
  "classification_confidence": 0.9,
  "classification_evidence": "I'm wondering if these are true silk or a blend? Also, do they need to be dry cleaned",
  "language": "English",
  "tone_analysis": {
    "tone": "friendly",
    "formality_level": 2,
    "key_phrases": ["Hi there", "Thanks for your help"]
  },
  "product_references": [
    {
      "reference_text": "silk blouses",
      "reference_type": "category",
      "product_id": null,
      "product_name": "silk blouses",
      "quantity": 1,
      "confidence": 0.8,
      "excerpt": "I noticed you have some really nice silk blouses on your website."
    }
  ],
  "customer_signals": [
    {
      "signal_type": "preference",
      "signal_category": "Product Features",
      "signal_text": "wondering if these are true silk or a blend",
      "signal_strength": 0.7,
      "excerpt": "I'm wondering if these are true silk or a blend?"
    },
    {
      "signal_type": "product_care",
      "signal_category": "Usage Information",
      "signal_text": "do they need to be dry cleaned or can they be hand washed",
      "signal_strength": 0.8,
      "excerpt": "do they need to be dry cleaned or can they be hand washed?"
    }
  ],
  "reasoning": "This email is a product inquiry as the customer is asking for information about product features (material composition) and care instructions. There is no explicit intent to purchase in the message."
}"""
    },
    
    # Example 3: Mixed intent but primarily an order
    {
        "subject": "Ordering CSH1098 cashmer scarf + question",
        "body": "Hello,\n\nI want to buy the blue cashmere scarf (CSH1098) that I saw on your site. Before I finalize my purchase, can you tell me if it's suitable for sensitive skin? I have a slight wool allergy but I've been fine with some cashmere products in the past.\n\nAlso, do you do gift wrapping?\n\nRegards,\nAlex",
        "output": """{
  "classification": "order_request",
  "classification_confidence": 0.75,
  "classification_evidence": "I want to buy the blue cashmere scarf (CSH1098)",
  "language": "English",
  "tone_analysis": {
    "tone": "formal",
    "formality_level": 4,
    "key_phrases": ["Hello", "Regards"]
  },
  "product_references": [
    {
      "reference_text": "blue cashmere scarf (CSH1098)",
      "reference_type": "product_id",
      "product_id": "CSH1098",
      "product_name": "blue cashmere scarf",
      "quantity": 1,
      "confidence": 0.95,
      "excerpt": "I want to buy the blue cashmere scarf (CSH1098) that I saw on your site."
    }
  ],
  "customer_signals": [
    {
      "signal_type": "purchase_intent",
      "signal_category": "Purchase Stage",
      "signal_text": "I want to buy",
      "signal_strength": 0.9,
      "excerpt": "I want to buy the blue cashmere scarf (CSH1098) that I saw on your site."
    },
    {
      "signal_type": "health_concern",
      "signal_category": "Decision Factor",
      "signal_text": "suitable for sensitive skin",
      "signal_strength": 0.8,
      "excerpt": "can you tell me if it's suitable for sensitive skin? I have a slight wool allergy"
    },
    {
      "signal_type": "gift_purpose",
      "signal_category": "Purchase Context",
      "signal_text": "do you do gift wrapping",
      "signal_strength": 0.7,
      "excerpt": "Also, do you do gift wrapping?"
    }
  ],
  "reasoning": "While this email contains product questions, the primary intent is to place an order as indicated by the clear statement 'I want to buy'. The questions are asked in the context of finalizing a purchase rather than general information gathering."
}"""
    }
]

# Construct the full prompt template with examples
email_analyzer_prompt_parts = [
    SystemMessage(content=system_message)
]

# Add few-shot examples to the prompt
for example in few_shot_examples:
    email_analyzer_prompt_parts.append(
        HumanMessage(content=human_message.format(
            subject=example["subject"],
            body=example["body"]
        ))
    )
    email_analyzer_prompt_parts.append(
        HumanMessage(content=example["output"])
    )

# Add the actual user query template at the end
email_analyzer_prompt_parts.append(
    HumanMessage(content=human_message)
)

# Create the final prompt template
email_analyzer_prompt = ChatPromptTemplate.from_messages(email_analyzer_prompt_parts)
""" {cell}
### Email Classifier Prompt Implementation Notes

The Email Classifier prompt is designed to produce comprehensive, structured analysis of customer emails. Key design features include:

1. **Detailed System Message**:
   - Clearly defines the analyzer's role and responsibilities
   - Provides explicit categorization guidelines for classifying emails
   - Includes a thorough customer signals framework to help identify subtle cues

2. **Structured Output Format**:
   - Specifies exact JSON structure matching our `EmailAnalysis` Pydantic model
   - Includes nested objects for tone analysis, product references, and customer signals
   - Requires confidence scores to indicate certainty levels in analysis

3. **Few-Shot Examples**:
   - Includes three carefully selected examples covering different scenarios:
     - Clear order request
     - Clear product inquiry
     - Mixed intent (primarily an order with questions)
   - Examples demonstrate the expected reasoning process and level of detail

4. **Tone Analysis Guidelines**:
   - Instructs the model to detect formality level on a 1-5 scale
   - Requires extraction of key phrases that indicate tone
   - Handles multiple emotional dimensions (friendly, urgent, frustrated, etc.)

5. **Product Inference Capabilities**:
   - Directs the model to extract both explicit and implicit product references
   - Handles various reference types (IDs, names, descriptions, categories)
   - Includes quantity inference with sensible defaults

This prompt structure ensures the Email Analyzer Agent produces consistent, detailed, and structured outputs that can be reliably used by downstream agents in the pipeline.
""" 