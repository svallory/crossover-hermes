""" {cell}
### Prompts for the Inquiry Responder Agent

This module contains LangChain `ChatPromptTemplate`(s) for the `Inquiry Responder Agent`. This agent is responsible for handling product inquiries by leveraging Retrieval-Augmented Generation (RAG).

**Core tasks supported by these prompts:**

1.  **Answer Synthesis**: Given the customer's questions (as identified by the `Email Analyzer Agent` or further refined) and relevant product information retrieved from the vector store (and other catalog tools), the LLM synthesizes clear and informative answers.
2.  **Contextual Information Integration**: The LLM incorporates details from the retrieved product documents (name, description, specifications, price, stock, promotions) directly into the answers.
3.  **Handling Multiple Questions/Products**: If the inquiry involves multiple questions or refers to several products, the LLM addresses each systematically.
4.  **Suggestion of Related Products**: Based on the inquiry context and retrieved products, the LLM can be prompted to suggest relevant alternatives or complementary items.
5.  **Structured Output Preparation**: The final output of the agent should be a structured object (e.g., conforming to the `InquiryResponse` Pydantic model from `reference-agent-flow.md`) that includes answered questions, details of primary products discussed, and any related product suggestions. This structured output is then used by the `Response Composer Agent`.

Prompts will emphasize using ONLY the provided product information to answer questions to prevent hallucination and ensure accuracy based on the catalog.
"""

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

# --- Main Prompt for Answering Inquiries and Structuring Response Data ---

SYNTHESIZE_INQUIRY_RESPONSE_SYSTEM_MESSAGE_CONTENT = """
You are an expert assistant for "Hermes" fashion retail, specializing in answering customer product inquiries based *solely* on provided product information from our catalog.
Your goal is to generate a structured JSON object that will be used to compose a helpful email response. The JSON should conform to the `InquiryResponse` Pydantic model.

**Key Instructions:**
1.  **Answer Based on Provided Context**: Use ONLY the information given in the 'Retrieved Product Context' sections to answer the customer's questions. Do NOT use any external knowledge or make assumptions beyond this context.
2.  **Address All Questions**: If multiple questions are identified from the customer's email, try to answer each one clearly.
3.  **Product Details**: For each product primarily discussed or relevant to a question, populate its details (ID, name, relevant specs from context, availability, price, promotions).
4.  **Related Products**: If appropriate and supported by the context (e.g., if a product is out of stock, or if complementary items are obvious from descriptions), you can suggest related or alternative products found in the provided context.
5.  **Response Points**: Generate a list of key textual points or sentences that should be included in the final email response. These points should be natural-sounding and directly address the customer's inquiry using the product information.

**Pydantic Model for `InquiryResponse` (summary):**
```json
{{
  "email_id": "(string) The ID of the original email being processed",
  "primary_products": [
    {{
      "product_id": "(string)",
      "product_name": "(string)",
      "details": {{ "(object with key-value pairs of product specs relevant to the inquiry, extracted from context)" }},
      "availability": "(string, e.g., 'In stock', 'Out of stock', 'Low stock')",
      "price": {{float, if available}},
      "promotions": "(string, any promotions mentioned for this product, if available)"
    }}
  ],
  "answered_questions": [
    {{
      "question": "(string) The customer's question, as identified from the email analysis",
      "question_excerpt": "(string, optional) The exact text from the email that contains this question",
      "answer": "(string) Your answer to the question, based *only* on the provided product context",
      "confidence": {{float, 0.0-1.0, your confidence in the answer's accuracy based on context}},
      "relevant_product_ids": ["(list of product IDs from primary_products that this answer pertains to)"]
    }}
  ],
  "related_products": [
    {{
      "product_id": "(string)",
      "product_name": "(string)",
      "details": {{ "(object with key-value pairs of product specs)" }},
      "availability": "(string)",
      "price": {{float}},
      "promotions": "(string, optional)"
    }}
  ],
  "response_points": [
    "(string) A key point/sentence to include in the response to the customer.",
    "(string) Another key point, perhaps about a specific product feature or answering a question directly."
  ]
}}
```

**Example Scenario:**
- Customer Question: "Is the P001 Classic T-Shirt made of cotton? How much is it?"
- Retrieved Product Context for P001: "Product Name: Classic T-Shirt. ID: P001. Description: A comfortable t-shirt made from 100% cotton. Price: $25.00. Stock: 100 units."

**Expected `answered_questions` snippet for the example:**
```json
    {{
      "question": "Is the P001 Classic T-Shirt made of cotton? How much is it?",
      "answer": "Yes, the Classic T-Shirt (P001) is made from 100% cotton. It costs $25.00.",
      "confidence": 1.0,
      "relevant_product_ids": ["P001"]
    }}
```
**Expected `response_points` snippet for the example:**
```json
[
  "The Classic T-Shirt (P001) is indeed made from 100% cotton.",
  "It is priced at $25.00 and we currently have it in stock."
]
```

Be comprehensive but concise. Ensure all information in your JSON output is directly supported by the provided customer questions and product context.
"""

SYNTHESIZE_INQUIRY_RESPONSE_HUMAN_MESSAGE_TEMPLATE_CONTENT = """
Generate a structured JSON output (conforming to `InquiryResponse` Pydantic model) to help answer the customer's inquiry based on the following information.

Email ID: {email_id}

Identified Customer Questions (from email analysis, as a list of strings):
```json
{identified_questions_json_string}
```

Retrieved Product Context (list of product data objects, each potentially including product_id, name, description, category, price, stock_amount, promotions, and any other relevant details from RAG search):
```json
{retrieved_product_context_json_string}
```

Your `InquiryResponse` JSON object (ensure this is the only thing you output):
"""

synthesize_inquiry_response_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(SYNTHESIZE_INQUIRY_RESPONSE_SYSTEM_MESSAGE_CONTENT),
    HumanMessagePromptTemplate.from_template(SYNTHESIZE_INQUIRY_RESPONSE_HUMAN_MESSAGE_TEMPLATE_CONTENT)
])

""" {cell}
### Notes on Inquiry Responder Prompts:

-   **RAG-Centric**: The core prompt `synthesize_inquiry_response_prompt` is designed to work with the outputs of a RAG pipeline. It expects identified customer questions and a collection of relevant product information (context chunks) retrieved from the vector store.
-   **Emphasis on Provided Context**: A critical instruction is for the LLM to base its answers *solely* on the provided product context. This is key to minimizing hallucination and ensuring responses are grounded in actual catalog data.
-   **Structured Output (`InquiryResponse` model)**: The prompt guides the LLM to produce a JSON object that should map directly to the `InquiryResponse` Pydantic model (as outlined in `reference-agent-flow.md`). This model will contain:
    -   Details of the primary products discussed.
    -   The customer's questions paired with synthesized answers.
    -   Information about related or alternative products if applicable.
    -   A list of `response_points` – these are natural language sentences that the `Response Composer Agent` can directly weave into the final email, ensuring key information is conveyed.
-   **Input Variables**: The prompt takes:
    -   `email_id`: For tracking.
    -   `identified_questions_json_string`: A JSON string representing the list of questions extracted from the customer's email by the `Email Analyzer Agent` or further processed by this agent.
    -   `retrieved_product_context_json_string`: A JSON string representing the list of product data snippets retrieved by the RAG system (vector search + fetching full details).
-   **Iterative Nature**: While this prompt provides a strong foundation, the exact phrasing and the level of detail in the `retrieved_product_context` would be refined during implementation and testing of the RAG pipeline to ensure the LLM gets the best possible information to work with.
-   **No Explicit Few-Shot Examples in this Template**: The system message provides a mini-example of expected input/output for a Q&A snippet. Depending on LLM performance, more elaborate few-shot examples detailing the full `InquiryResponse` JSON structure for various scenarios could be added, similar to the `Email Analyzer` prompt. However, strong instructions on JSON structure and data grounding are often very effective for synthesis tasks.

This prompt facilitates the core reasoning step of the `Inquiry Responder Agent`: transforming raw retrieved data and questions into a structured, actionable format for generating a high-quality customer response.
""" 