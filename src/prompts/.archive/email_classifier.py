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

# System message defining the agent's role and analysis requirements
email_analyzer_system_message = """
You are an expert email analysis AI for a high-end fashion retail store.
Your task is to meticulously analyze customer emails and extract structured information.

Given the email subject and body, provide a comprehensive analysis covering:
1.  **Classification**: Determine if it's an 'order_request' or 'product_inquiry'. Some emails might have elements of both; choose the primary purpose.
2.  **Classification Confidence**: A float between 0.0 and 1.0.
3.  **Classification Evidence**: A short quote from the email that best supports your classification.
4.  **Language**: Detect the primary language of the email (e.g., 'English', 'Spanish').
5.  **Customer Name**: Identify the customer's first name if it's apparent from common greetings (e.g., "Hi John,", "Dear Jane,", "Thanks, Sarah"). Be case-insensitive. If no clear name is found, leave it null.
6.  **Tone Analysis**: Analyze the customer's tone ('formal', 'casual', 'urgent', 'friendly', 'frustrated', etc.), formality level (1-5), and list key phrases indicating this tone.
7.  **Product References**: Identify ALL mentions of products. For each reference:
    *   `reference_text`: The exact text snippet from the email referring to the product.
    *   `reference_type`: Classify as 'product_id', 'product_name', or 'descriptive_phrase'.
    *   `product_id`: The specific product ID if mentioned (e.g., "SKU123", "ABC-001").
    *   `product_name`: The product name if mentioned (e.g., "Silk Scarf", "Chelsea Boots").
    *   `quantity`: If a quantity is specified for this reference (e.g., "two shirts", "1x boots").
    *   `excerpt`: The sentence or phrase from the email that contains this product reference, providing context.
8.  **Customer Signals**: Identify ALL customer signals related to purchase intent, context, emotion, or specific needs. For each signal:
    *   `signal_category`: Classify as 'purchase_intent', 'product_interest', 'urgency', 'sentiment_positive', 'sentiment_negative', 'budget_mention', 'occasion_mention' (e.g., gift, wedding), 'new_customer_indicator', 'loyalty_mention', 'comparison_shopping', 'feature_request', 'problem_report'.
    *   `signal_text`: The specific text snippet from the email that indicates this signal.
    *   `relevance_score`: A float (0.0-1.0) indicating the signal's importance for response personalization.
    *   `excerpt`: The sentence or phrase from the email that contains this signal, providing context.
9.  **Reasoning**: Briefly explain your overall reasoning for the classification and key findings.

Ensure all `excerpt` fields are accurate, non-empty, and directly from the provided email body, offering sufficient context for the reference or signal.
Output should be a JSON object strictly conforming to the EmailAnalysis Pydantic model.
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
    SystemMessage(content=email_analyzer_system_message)
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

# --- Prompt Template for verify_email_analysis ---
email_analysis_verification_system_message_content = """
You are a meticulous verification AI for email analysis.
Your task is to review a structured JSON analysis of a customer email and ensure its accuracy and completeness against the original email content.

Key areas to verify:
1.  **Classification**: Ensure `classification`, `classification_confidence`, and `classification_evidence` are consistent and accurately reflect the primary purpose of the email.
2.  **Customer Name**: If a `customer_name` is extracted, verify it seems plausible based on common greeting patterns in the `email_body`. If it's clearly wrong or absent when it should be present, correct it or add it. If no name is identifiable, it should be null.
3.  **Excerpts**: For ALL `product_references` and `customer_signals`:
    *   Verify that the `excerpt` field is not empty.
    *   Verify that the `excerpt` is an actual, accurate, and relevant snippet from the `email_body` that provides necessary context for the extracted `reference_text` or `signal_text`.
    *   Ensure `reference_text` (for products) and `signal_text` (for signals) are themselves accurate sub-strings or summaries of the information within their respective `excerpt`.
4.  **Completeness of References/Signals**: Check if any obvious product references or customer signals in the `email_body` were missed in the original analysis. If so, add them.
5.  **Overall Coherence**: Ensure the `reasoning` field is consistent with the rest of the analysis.

If the analysis is already excellent, return it as is. If there are issues, provide a revised JSON output that corrects them, strictly adhering to the EmailAnalysis Pydantic model structure.
"""

email_analysis_verification_human_template = """
Original Email Subject: {email_subject}
Original Email Body:
{email_body}

Original Email Analysis (JSON string to verify and correct):
{original_analysis_json}

Potential issues identified by initial checks (these are just pointers, perform a full review based on system message):
{errors_found_str}

Please review the 'original_analysis_json' against the 'Original Email Subject' and 'Original Email Body'.
If corrections are needed, provide the revised and corrected JSON output.
If the analysis is perfect, you can return it unchanged or confirm its accuracy.
"""

email_analysis_verification_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessage(content=email_analysis_verification_system_message_content),
    HumanMessage(content=email_analysis_verification_human_template)
])

""" {cell}
### Email Classifier Prompt Implementation Notes

The Email Classifier prompt is designed to produce comprehensive, structured analysis of customer emails. Key design features include:

1. **Detailed System Message**:
   - Clearly defines the analyzer's role and responsibilities
   - Provides explicit categorization guidelines for classifying emails
   - Includes a thorough customer signals framework to help identify subtle cues

2. **Structured Output Format**:
   - Uses with_structured_output() to enforce Pydantic schema format
   - No need for explicit JSON formatting instructions
   - Leverages LangChain's capabilities to handle structure validation

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