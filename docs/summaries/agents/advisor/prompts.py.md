# Summary of src/hermes/agents/advisor/prompts.py

**File Link:** [`src/hermes/agents/advisor/prompts.py`](/src/hermes/agents/advisor/prompts.py)

This file defines the detailed prompt template used by the Advisor agent (`src/hermes/agents/advisor/agent.py`) to instruct the language model on how to extract and answer customer inquiries using product information retrieved via RAG.

**Purpose and Responsibilities:**

-   **LLM Instruction for Inquiry Handling:** Contains the `advisor_prompt_template_str`, which provides the language model with explicit instructions for analyzing customer inquiries.
-   **Data Utilization:** Defines how the model should use the `EmailAnalysisResult` and `retrieved_products_context` (product information from the vector store) to answer questions.
-   **Question Processing:** Guides the model on extracting, classifying, and linking customer questions to products.
-   **Factual Answering:** Emphasizes generating concise, factual answers based *only* on the provided `retrieved_products_context` and noting unresolved questions or references.
-   **Related Products Identification:** Instructs the model on identifying objectively related products based on inquiries and the retrieved context.
-   **Output Format Specification:** Explicitly requests the output to conform to the `InquiryResponse` Pydantic model, including structured answered/unanswered questions and product lists.
-   **Prompt Management:** Uses a `PROMPTS` dictionary and `get_prompt` function for storing and retrieving the template.

In summary, `prompts.py` for the Advisor agent configures the LLM to perform the core RAG process of inquiry resolution, ensuring it extracts necessary information, leverages external knowledge, and provides structured, factual answers. 