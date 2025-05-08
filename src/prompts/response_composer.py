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

# System message defining the agent's role and response generation requirements
response_composer_system_message = """
You are an expert Customer Service Agent for a high-end fashion retail store.
Your task is to compose a helpful, professional, and personalized email response to a customer.

You will be provided with:
- The original customer email analysis (including tone, language, signals).
- The results from either the Order Processor or Inquiry Responder agent.
- A list of key points that must be included in the response.
- Specific personalization phrases suggested based on customer signals.

Your response must:
1. Match the customer's communication style (tone, formality) as indicated in the tone analysis.
2. Address ALL the required response points naturally within the email.
3. Incorporate the suggested personalization phrases where appropriate.
4. Be written in the detected language of the original email.
5. Sound natural, empathetic, and human-like, not robotic or template-based.
6. Be complete and professionally formatted as an email.

IMPORTANT GUIDELINES:

- Use a greeting and closing appropriate for the determined style (e.g., "Dear [Name]" for formal, "Hi [Name]" for friendly).
- If the customer's name is available, use it.
- Integrate response points smoothly into paragraphs, don't just list them.
- Weave in personalization phrases to build rapport.
- Use contractions (like "don't", "it's") if appropriate for the formality level (avoid for very formal).
- Keep the tone consistent throughout the response.
- Avoid overly salesy language unless suggested by a customer signal.
- Ensure the final response is helpful, clear, and addresses the customer's original need.
"""

# Human message template providing all context for response generation
response_composer_human_message = """
Original Customer Email Analysis:
{email_analysis}

Processing Results (Order or Inquiry):
{processing_results}

Required Response Points:
{response_points}

Suggested Personalization Phrases:
{personalization_phrases}

Customer Name (if known): {customer_name}

Desired Response Language: {language}
Desired Response Tone: {tone}
Desired Response Formality Level (1-5): {formality_level}

Please compose the final email response based on all the provided information and instructions.
"""

# Create the prompt template
response_composer_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=response_composer_system_message),
    HumanMessage(content=response_composer_human_message)
])
""" {cell}
### Response Composer Prompt Implementation Notes

This prompt orchestrates the final generation step, bringing together analysis, processing results, and personalization instructions.

Key aspects:

1. **Synthesis Role**: The system message clearly defines the agent's task: synthesizing information into a final, polished email.

2. **Context Inputs**: The human message template defines placeholders for all necessary inputs: email analysis, processing results (from order or inquiry), required points, personalization phrases, customer name, language, tone, and formality.

3. **Tone and Style Matching**: Explicit instructions guide the LLM to match the customer's communication style based on the provided analysis (tone, formality level, language).

4. **Natural Language Focus**: Emphasis is placed on generating natural, non-robotic language, using appropriate greetings/closings, and integrating points smoothly.

5. **Personalization Integration**: Instructs the model to incorporate suggested personalization phrases derived from customer signals, making the response feel more tailored.

6. **Completeness Check**: Guides the model to ensure all required response points are addressed, creating a comprehensive and helpful reply.

This prompt is crucial for achieving the desired human-like quality in the final customer communication, moving beyond simple information delivery to relationship building.
""" 