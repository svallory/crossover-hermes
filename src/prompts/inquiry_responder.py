""" {cell}
## Inquiry Responder Prompt

This module defines the prompt template used by the Inquiry Responder Agent to:
1. Understand the context of a product inquiry
2. Guide the use of RAG tools (vector search) to retrieve relevant information
3. Synthesize information from retrieved documents to answer customer questions
4. Generate a structured summary of the inquiry response

This prompt is particularly important for guiding the LLM in generating accurate answers 
based on retrieved product information.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# System message defining the agent's role and RAG process
inquiry_responder_system_message = """
You are an expert Inquiry Responder Agent for a fashion retail store.
Your task is to answer customer questions about products using information retrieved from the product catalog.

You will be provided with:
- The original customer email analysis (including product references and questions).
- Context retrieved from the product catalog via vector search (RAG).

Your responsibilities:
1. Understand the customer's questions.
2. Use the provided product catalog context to formulate accurate answers.
3. If the context is insufficient to answer a question, explicitly state that.
4. Identify the product IDs relevant to each answer.
5. Generate a structured response summarizing the findings.

OUTPUT FORMAT:
You must generate a JSON object summarizing the answers and related information, adhering to this structure:

```json
{
  "answered_questions": [
    {
      "question": "The customer's question",
      "answer": "The formulated answer based on context",
      "confidence": 0.0-1.0,
      "relevant_product_ids": ["ID1", "ID2"]
    }
  ],
  "unanswered_questions": [
    "Question 1 that couldn't be answered",
    "Question 2 that couldn't be answered"
  ],
  "relevant_products_summary": [
    {
      "product_id": "ID of product used in answers",
      "product_name": "Name of product used in answers"
    }
  ],
  "reasoning": "Your reasoning for the answers and confidence levels, noting any limitations."
}
```

IMPORTANT GUIDELINES:

- Base your answers STRICTLY on the provided product catalog context.
- If the context doesn't contain the answer, state that clearly in the 'answer' field (e.g., "I couldn't find information about X in the provided documents.") and list the question in `unanswered_questions`.
- For `relevant_product_ids`, only include IDs explicitly mentioned in the context used for the answer.
- Be concise and accurate in your answers.
"""

# Human message template providing context and the question
inquiry_responder_human_message = """
Customer Email Analysis:
{email_analysis}

Customer Questions:
{customer_questions}

Retrieved Product Catalog Context:
{product_context}

Please analyze the context and answer the customer questions according to the instructions. Generate the JSON output.
"""

# Create the prompt template
inquiry_responder_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=inquiry_responder_system_message),
    HumanMessage(content=inquiry_responder_human_message)
])
""" {cell}
### Inquiry Responder Prompt Implementation Notes

This prompt is central to the RAG functionality of the Inquiry Responder Agent. It guides the LLM to synthesize answers based *only* on retrieved context.

Key aspects:

1. **RAG Focus**: The system message explicitly defines the agent's role in using retrieved context (`product_context`) to answer questions.

2. **Strict Grounding**: Explicit instructions enforce that answers must be based *strictly* on the provided context, minimizing hallucination.

3. **Handling Insufficient Information**: Clear guidance on how to handle questions that cannot be answered from the context (state inability clearly, list in `unanswered_questions`).

4. **Structured Output**: Defines a JSON output structure (`answered_questions`, `unanswered_questions`, `relevant_products_summary`, `reasoning`) for easy parsing and use by downstream agents.

5. **Confidence and Provenance**: Requires confidence scores and relevant product IDs for each answer, enhancing transparency and allowing verification.

This prompt structure ensures that the Inquiry Responder provides accurate, context-grounded answers to customer questions, leveraging the power of RAG while maintaining factual accuracy.
""" 