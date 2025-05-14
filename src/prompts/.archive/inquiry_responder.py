""" {cell}
## Inquiry Responder Prompt

This module defines the prompt template used by the Inquiry Responder Agent to:
1. Answer customer questions about products using RAG
2. Generate structured output in the InquiryResponse format
3. Provide relevant information about products mentioned in the inquiry

This prompt works with the with_structured_output() method to enforce output schema compliance.
"""
from langchain_core.prompts import ChatPromptTemplate, FewShotPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from src.prompts.inquiry_responder import (
    inquiry_responder_md,
    answer_question_md, 
    inquiry_response_verification_md
)

# System message defining the agent's role and RAG process
inquiry_responder_system_message = """
You are an expert AI assistant for a high-end fashion retail store.
Your task is to analyze a customer's inquiry (based on email analysis and product information) and generate a comprehensive structured response.

You will be provided with:
- The full email analysis (JSON) which includes the original email text, classification, detected language, tone, customer signals, and product references.
- A list of primary products (JSON) that were successfully resolved from the customer's email, including their details, availability, and promotions.
- A list of questions (JSON) extracted from the customer's email that need to be answered.
- A list of related products (JSON) that could be suggested to the customer.

Your goal is to generate the `InquiryResponse` Pydantic model, which includes:
1.  `email_id`: (Will be pre-filled, focus on other fields).
2.  `primary_products`: (Will be pre-filled, focus on other fields).
3.  `answered_questions`: For each question from the input, use the `answer_question_prompt_template` logic (see below) to determine if it can be answered using the `primary_products` context or general knowledge. If answered, populate a `QuestionAnswer` model.
4.  `related_products`: (Will be pre-filled, focus on other fields).
5.  `response_points`: Generate a concise list of key talking points for the final email response. These points should cover:
    *   Information about primary products (name, availability, price if important, promotions).
    *   Answers to customer questions.
    *   Suggestions for related products (if any).
    *   Address any unsuccessful product references (apologize if a product couldn't be found).
    *   Acknowledge any unanswered questions (if context was insufficient).
    *   An invitation for the customer to ask for more details.
6.  `unanswered_questions`: List of original question texts that could not be answered.
7.  `unsuccessful_references`: List of original reference texts for products that could not be resolved/found.

When generating `response_points`, make them actionable and informative for the Response Composer agent that will write the final email.
When deciding on `answered_questions`, if a question cannot be confidently answered from the given product context or general fashion knowledge, list it in `unanswered_questions`.
"""

# Human message template providing context and the question
inquiry_responder_human_message = """
Email ID: {email_id}
Full Email Analysis (JSON):
{email_analysis_json}

Primary Products Identified (JSON List of ProductInformation):
{primary_products_json}

Extracted Customer Questions (JSON List of ExtractedQuestion model):
{questions_json}

Potentially Related Products (JSON List of ProductInformation):
{related_products_json}

Unsuccessful Product References (List of strings):
{unsuccessful_references_list}

Please generate the full InquiryResponse JSON object based on all this information and the system prompt instructions.
Focus on populating `answered_questions`, `unanswered_questions`, and `response_points` accurately.
"""

# Create the prompt template using the markdown content
inquiry_responder_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=inquiry_responder_md.split("### USER REQUEST")[0].strip()),
    HumanMessage(content=inquiry_responder_md.split("### USER REQUEST")[1].strip())
])

# --- Prompt Template for Answering a Single Question (to be used by an LLM or a sub-chain) ---
# This will output the LLMAnsweredQuestionResult Pydantic model.

answer_question_system_message_content = """
You are an AI assistant specialized in answering customer questions about fashion products.
Given a customer's question and context about one or more products, determine if you can answer the question confidently.
If yes, provide the answer, a confidence score, and the IDs of products relevant to the answer.
If no, indicate that it cannot be answered.
Prioritize information from the provided context. Only use general fashion knowledge if the context is insufficient but the question is general (e.g., 'Is silk good for summer?').
Be concise. Structure your output as a JSON object matching the LLMAnsweredQuestionResult model.
"""

answer_question_human_template = """
Product Context (JSON objects describing one or more products):
{product_context_json}

Customer Question:
{question_text}

Please analyze the question based on the product context and provide your answer as a JSON object conforming to the LLMAnsweredQuestionResult model (fields: is_answered, answer_text, confidence, relevant_product_ids).
"""

answer_question_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessage(content=answer_question_md.split("### USER REQUEST")[0].strip()),
    HumanMessage(content=answer_question_md.split("### USER REQUEST")[1].strip())
])


# --- Verification Prompt Template for Inquiry Response ---
inquiry_response_verification_system_message_content = """
You are a verification assistant for product inquiry responses. Your job is to fix issues
in the structured response to ensure it's accurate and helpful.
"""

inquiry_response_verification_human_message_content = """
The inquiry response has the following errors:
{errors_found_str}

Please fix these issues in the response.

Original response:
{original_response_json}

Email analysis context:
{email_analysis_json}
"""

inquiry_response_verification_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessage(content=inquiry_response_verification_md.split("### USER REQUEST")[0].strip()),
    HumanMessage(content=inquiry_response_verification_md.split("### USER REQUEST")[1].strip())
])


""" {cell}
### Inquiry Responder Prompt Implementation Notes

This prompt is designed to work with LangChain's structured output capabilities, generating an InquiryResponse directly.

Key aspects:

1. **Structured Output Focus**: The prompt works with `with_structured_output(InquiryResponse)` to ensure compliance with the required schema.

2. **RAG Implementation**: Uses retrieval augmented generation to ground responses in factual product information.

3. **Comprehensive Response Generation**: Addresses all customer questions while providing relevant product details and suggesting related products.

4. **Response Point Generation**: Creates key talking points that will be used by the Response Composer to generate the final email.

5. **Strict Factual Grounding**: Emphasis on using only the provided product information to prevent hallucination.

This prompt ensures the Inquiry Responder provides accurate, helpful responses based on actual product information, while maintaining a consistent structure that can be easily processed by downstream components.
""" 