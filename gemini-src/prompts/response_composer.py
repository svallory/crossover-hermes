""" {cell}
### Prompts for the Response Composer Agent

This module contains the LangChain `ChatPromptTemplate` for the `Response Composer Agent`. This agent has the critical role of generating the final, polished, customer-facing email response. It synthesizes all information gathered and processed by the preceding agents (`Email Analyzer`, `Order Processor`, `Inquiry Responder`).

**The prompt for this agent is designed to guide the LLM in several key aspects:**

1.  **Information Synthesis**: Combine various pieces of information into a single, coherent message. This includes:
    *   Acknowledging the customer's original query/request.
    *   Providing order status updates (if applicable).
    *   Answering product inquiries (if applicable).
    *   Mentioning product details, alternatives, or promotions as processed by earlier agents.
2.  **Tone and Style Adaptation**: Generate a response that matches the customer's detected tone (e.g., formal, casual, enthusiastic) and formality level, while maintaining the professional and helpful brand voice of "Hermes".
3.  **Customer Signal Incorporation**: Weave in responses or actions based on the customer signals detected by the `Email Analyzer Agent`, following the guidance in `customer-signal-processing.md`. For example, if a gift context was detected, the response might include a phrase acknowledging it or suggesting gift-related services.
4.  **Natural Language and Empathy**: Craft a response that sounds natural, empathetic, and human-like, avoiding robotic or overly templated language. This includes using appropriate greetings, transitions, and closings.
5.  **Clarity and Conciseness**: Ensure the response is easy to understand and provides all necessary information without being overly verbose.
6.  **Call to Action (if applicable)**: Guide the customer on next steps if any are required (e.g., confirming an alternative, providing more information).

This prompt will take a comprehensive set of inputs, likely including the `EmailAnalysisOutput`, `OrderProcessingOutput` (if an order), and `InquiryResponseOutput` (if an inquiry), along with the original email text for full context.
"""

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

# --- Main Prompt for Composing the Final Customer Response ---

COMPOSE_RESPONSE_SYSTEM_MESSAGE_CONTENT = """
You are an expert Customer Service Agent for "Hermes", a luxury fashion retailer. Your task is to compose a polite, professional, empathetic, and helpful email response to a customer.

You will be given a full analysis of the customer's original email, details about their order (if any), and answers to their inquiries (if any).
Your response should be well-structured, address all aspects of the customer's communication, and reflect the Hermes brand voice: sophisticated, attentive, and customer-focused.

**Key Instructions for Response Composition:**

1.  **Acknowledge and Synthesize**: Start by acknowledging the customer's email. Seamlessly integrate information from the provided context (order status, inquiry answers, product details).
2.  **Tone Matching**: Adapt your tone to the customer's detected communication style (e.g., formal, casual, urgent, enthusiastic). Refer to the `tone_analysis` provided. However, always maintain a baseline of professionalism and warmth.
3.  **Address Customer Signals**: Subtly incorporate responses to detected `customer_signals` (from the `customer_signal_processing.md` guide). For example:
    *   If 'Gift Purchase' signal: "That sounds like a lovely gift for your grandmother!"
    *   If 'Urgency' signal: Acknowledge their need for a quick resolution.
    *   If 'Enthusiasm': Mirror some of their positive energy.
    *   If 'Price Concern': Gently reiterate value if product information supports it, without being defensive.
4.  **Natural Language**: Write naturally. Use contractions where appropriate for a friendly tone. Avoid overly robotic phrases like "As per your request" or "In response to your inquiry about...". Instead, use phrases like "You asked about..." or "Regarding the [product name],...".
5.  **Structure**: Organize the email logically: Greeting, main body addressing points, closing.
    *   **Greeting**: Personalize if the customer's name is known (from email or analysis).
    *   **Body**: 
        *   If an order, clearly state the status of each item. If items are out of stock, explain this gently and offer any suggested alternatives provided in the context.
        *   If an inquiry, directly answer the questions using the `response_points` and `answered_questions` from the inquiry analysis. Weave in product details naturally.
        *   If promotions were identified for relevant products, mention them.
    *   **Closing**: Professional and courteous closing (e.g., "Sincerely,", "Warm regards,", "Best regards,"). Sign off as "The Hermes Team" or a similar generic but friendly sign-off.
6.  **Completeness**: Ensure all significant points from the customer's email are addressed.
7.  **Clarity and Conciseness**: Be clear and to the point while being thorough.
8.  **Production-Ready**: The output should be a clean email body, ready to be sent.

**Input Context You Will Receive:**
- `original_email_subject`: The subject of the customer's email.
- `original_email_body`: The body of the customer's email.
- `email_analysis_json`: JSON string containing the full output from the Email Analyzer Agent (includes classification, language, tone, product references, customer signals).
- `order_processing_result_json`: (Optional) JSON string with results from Order Processor Agent, if it was an order request.
- `inquiry_response_result_json`: (Optional) JSON string with results from Inquiry Responder Agent, if it was a product inquiry.

**Example Tone Adaptation:**
- If customer is formal: "Dear Mr. Smith, Thank you for your email regarding..."
- If customer is casual and enthusiastic: "Hi Jessica! Thanks for reaching out about the Vibrant Tote bag – great choice, it's a fantastic bag!"

**Focus on being genuinely helpful and making the customer feel valued.**
Do NOT invent information. Stick to the details provided in the context JSONs.
"""

COMPOSE_RESPONSE_HUMAN_MESSAGE_TEMPLATE_CONTENT = """
Please compose a customer-facing email response based on the following information. 
Your entire output should be ONLY the body of the email response, without any extra explanations, preambles, or metadata.

**Original Customer Email Context:**
Subject: {original_email_subject}
Body:
```
{original_email_body}
```

**Email Analysis (JSON):**
```json
{email_analysis_json}
```

**Order Processing Result (JSON, if applicable, otherwise 'None'):**
```json
{order_processing_result_json}
```

**Inquiry Response Result (JSON, if applicable, otherwise 'None'):**
```json
{inquiry_response_result_json}
```

**Compose the email response body now:**
"""

compose_response_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(COMPOSE_RESPONSE_SYSTEM_MESSAGE_CONTENT),
    HumanMessagePromptTemplate.from_template(COMPOSE_RESPONSE_HUMAN_MESSAGE_TEMPLATE_CONTENT)
])

""" {cell}
### Notes on Response Composer Prompts:

-   **Comprehensive System Message**: The system message is detailed, setting the persona ("expert Customer Service Agent for Hermes"), the overall goal, and key instructions covering information synthesis, tone adaptation, customer signal incorporation, natural language use, structure, and brand voice.
-   **Input Context**: The human message template clearly defines the expected inputs:
    -   The original customer email subject and body (for full context and direct reference if needed by the LLM).
    -   `email_analysis_json`: The complete structured output from the `Email Analyzer Agent`.
    -   `order_processing_result_json`: The structured output from the `Order Processor Agent` (optional, only if it was an order).
    -   `inquiry_response_result_json`: The structured output from the `Inquiry Responder Agent` (optional, only if it was an inquiry).
    These JSON strings provide the LLM with all the necessary pre-processed information.
-   **Emphasis on Natural Language and Empathy**: The prompt repeatedly stresses the need for natural, human-like language and an empathetic tone, guiding the LLM away from generic or robotic responses.
-   **Guidance from `customer-signal-processing.md`**: The system message explicitly mentions incorporating responses to customer signals, linking back to the detailed guide.
-   **Output Instruction**: The LLM is instructed to output *only* the email body, making it easy to use the LLM's response directly.
-   **No Few-Shot Examples (Initially)**: For a complex generation task like this, the quality heavily depends on the richness of the input context and the clarity of the system message. Few-shot examples could be added if the LLM struggles with specific aspects (e.g., handling a particular combination of order status and inquiry), but often a strong system prompt with detailed instructions can be very effective for generation.

This prompt structure is designed to empower the LLM to act as a sophisticated response generation engine, leveraging all the analytical work done by the previous agents in the pipeline to create high-quality, personalized customer communications.
""" 