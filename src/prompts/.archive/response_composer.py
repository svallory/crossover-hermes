""" {cell}
## Response Composer Prompt

This module defines the prompt template used by the Response Composer Agent to:
1. Synthesize information from previous agents (Analyzer, Order Processor/Inquiry Responder)
2. Understand the desired tone and personalization requirements
3. Generate a natural, human-like email response

This prompt guides the final language generation step, focusing on tone matching, 
customer signal integration, and overall response quality.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from src.prompts.response_composer import (
    response_composer_md,
    response_quality_verification_md
)

# System message defining the agent's role and response generation requirements
response_composer_system_message = """
You are an expert Customer Service Agent for a high-end fashion retail store.
Your task is to compose a helpful, professional, and personalized email response to a customer.

You will be provided with:
- The original customer email analysis as a JSON string (includes original email text, detected tone, language, and customer signals like sentiment, intent, specific mentions of products, occasions, emotions, etc.).
- The processing results from either the Order Processor or Inquiry Responder agent as a JSON string (includes details about order status, items, inquiry answers, etc.).

Your response must:
1.  **Structure and Content Generation**:
    *   Based on the 'classification' in the email analysis and the content of 'processing_results', determine the key points to address.
    *   If it's an order, confirm order details (items, status, out-of-stock items, alternatives, shipping info).
    *   If it's an inquiry, directly and specifically answer all questions using information from processing_results.
    *   If it's a hybrid, determine a logical flow, usually confirming the order before addressing inquiries.
2.  **Tone and Style Matching**:
    *   Match the customer's communication style (tone, formality) as indicated in the 'tone_analysis' section of the email analysis.
    *   Use a greeting and closing appropriate for the determined style (e.g., "Dear [Name]" for formal, "Hi [Name]" for friendly). If the customer's name is available, use it.
3.  **Personalization and Empathy**:
    *   Analyze 'customer_signals' within the email analysis.
    *   Acknowledge any customer emotions (e.g., excitement, frustration) empathetically.
    *   If signals indicate a special occasion (e.g., gift, new job), incorporate relevant well-wishes or comments.
    *   Weave these personalization elements smoothly into the response to build rapport.
4.  **Language and Naturalness**:
    *   Be written in the detected language from the email analysis.
    *   Sound natural, empathetic, and human-like, not robotic or template-based.
    *   Use contractions (like "don't", "it's") if appropriate for the formality level (avoid for very formal).
    *   Vary sentence structure.
5.  **Upsell/Cross-sell (Subtly)**:
    *   If 'customer_signals' or 'processing_results' (e.g., inquiry about a product) suggest a natural opportunity, you can include 1-2 highly relevant product suggestions.
    *   Frame these as helpful advice, not pushy sales tactics. For example, "Since you liked X, you might also appreciate Y which complements it well for Z occasion."
6.  **Completeness and Professionalism**:
    *   Ensure the final response is helpful, clear, and addresses all aspects of the customer's original need based on the provided analysis and results.
    *   The response should be professionally formatted as an email.

Avoid just listing points; integrate them into a cohesive, flowing message.
"""

# Human message template providing all context for response generation
response_composer_human_message = """
Original Customer Email Analysis (JSON string):
{email_analysis}

Processing Results (Order or Inquiry - JSON string):
{processing_results}

Customer Name (if known): {customer_name}
Desired Response Language: {language}
Desired Response Tone: {tone}
Desired Response Formality Level (1-5 from email_analysis): {formality_level}

Please compose the final email response based on all the provided information and instructions.
"""

# Create the prompt template using the markdown content
response_composer_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=response_composer_md.split("### USER REQUEST")[0].strip()),
    HumanMessage(content=response_composer_md.split("### USER REQUEST")[1].strip())
])

# --- Prompt Template for process_customer_signals --- (REMOVED as logic is merged)
# process_customer_signals_system_message_content = """..."""
# process_customer_signals_human_template = """..."""
# process_customer_signals_prompt_template = ChatPromptTemplate.from_messages([...])

# --- Prompt Template for verify_response_quality ---
response_quality_verification_system_message_content = """
You are a meticulous response quality verification assistant for a high-end fashion retail store.
Your task is to review a generated customer email response and revise it if necessary to ensure it is complete, professional, natural-sounding, and adheres to all communication guidelines.

You will be given the original customer email details, the initial generated response, and expected tone.

Perform the following checks and revise the response to fix any issues:
1.  **Greeting**: Ensure there is an appropriate and contextually fitting greeting (e.g., using customer name if available, matching formality).
2.  **Closing**: Ensure there is an appropriate and contextually fitting closing.
3.  **Tone Consistency**: Verify the response tone matches the `expected_tone` and `formality_level` derived from the original email analysis. The language should feel natural and empathetic.
4.  **Completeness**: Critically assess if the response comprehensively addresses all explicit and implicit questions, concerns, and order details present in the original customer's email (provided as `email_subject` and `email_body`) and reflected in `email_analysis_json` and `processing_results_json` (if applicable).
5.  **Clarity and Professionalism**: Ensure the language is clear, concise, grammatically correct, and maintains a professional standard suitable for the brand.
6.  **Natural Language**: The response must not sound robotic or like a template. It should be engaging and human-like.

If the response is already excellent, you can return it as is, or with minimal refinements. If there are issues, provide a revised version that corrects them.
"""

response_quality_verification_human_template = """
Original customer email subject: {email_subject}
Original customer email body (for context):
{email_body}

Full Email Analysis (JSON, for context on signals, classification, etc.):
{email_analysis_json}

Processing Results (JSON, for context on order/inquiry details - if applicable):
{processing_results_json}

Email Type: {email_type}
Expected Tone: {expected_tone}
Expected Formality Level: {formality_level}

Original response to verify:
{original_response}

Please review the 'original_response' based on all the provided context and instructions in the system message. If necessary, provide a revised and improved response. If the response is already perfect, you may indicate that or return it unchanged.
"""

# Create verification prompt template
response_quality_verification_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessage(content=response_quality_verification_md.split("### USER REQUEST")[0].strip()),
    HumanMessage(content=response_quality_verification_md.split("### USER REQUEST")[1].strip())
])

""" {cell}
### Response Composer Prompt Implementation Notes

This prompt orchestrates the final generation step, bringing together analysis, processing results, and personalization instructions.

Key aspects:

1. **Synthesis Role**: The system message clearly defines the agent's task: synthesizing information from raw analysis and processing results into a final, polished email. It now has broader responsibilities for deriving key points and personalization.

2. **Context Inputs**: The human message template defines placeholders for all necessary inputs:
    - `email_analysis`: A JSON string containing original email insights, including text, language, tone analysis, and extracted customer signals.
    - `processing_results`: A JSON string with details from order or inquiry processing.
    - `customer_name`, `language`, `tone`, `formality_level`: Specific parameters to guide style.

3. **Integrated Logic**:
    - **Response Point Generation**: The LLM is now responsible for identifying and structuring the core message points based on the `email_analysis` and `processing_results`.
    - **Customer Signal Processing**: The LLM directly interprets `customer_signals` from the `email_analysis` to weave in empathy, personalization, and subtle upsells.

4. **Tone and Style Matching**: Explicit instructions guide the LLM to match the customer's communication style based on the provided analysis (tone, formality level, language).

5. **Natural Language Focus**: Emphasis is placed on generating natural, non-robotic language, using appropriate greetings/closings, and integrating points smoothly.

6. **Completeness Check**: Guides the model to ensure all required response points (which it now self-determines) are addressed, creating a comprehensive and helpful reply.

This consolidated prompt aims for efficiency by reducing intermediate LLM calls, relying on the LLM's capability to handle more complex, multi-faceted instructions for generating the final customer communication. The quality verification step remains separate for a final check.
""" 