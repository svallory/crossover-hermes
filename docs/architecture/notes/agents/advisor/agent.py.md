This file, `agent.py`, contains the core logic for the Advisor agent, also known as the Inquiry Responder. Its primary function, `respond_to_inquiry`, is responsible for extracting customer inquiries from the analyzed email and providing factual answers, primarily by leveraging a Retrieval Augmented Generation (RAG) approach using a product catalog vector store.

Key components and responsibilities:
-   **Inquiry Extraction:** It processes the `EmailAnalysis` from the Classifier agent to identify inquiry-type segments and extract relevant search queries from the customer's questions and product mentions.
-   **Product Information Retrieval:** It combines product information resolved by the Stockkeeper agent with information retrieved from the vector store using the extracted search queries. This forms the RAG context provided to the LLM. It includes helper functions like `format_resolved_products` and `search_vector_store` for this purpose.
-   **LLM Interaction:** It uses a "strong" language model and a dedicated prompt (`get_prompt(Agents.ADVISOR)`) to generate structured answers to the inquiries based on the provided product context.
-   **Structured Output:** It guides the LLM to produce an `InquiryAnswers` object, which includes lists of answered and unanswered questions, primary and related products, and unsuccessful references. It also includes a `fix_seasons_in_response` utility to ensure product season data adheres to the expected format.
-   **Error Handling:** It includes error handling for cases like missing email analysis or failures during LLM invocation, returning appropriate error responses.
-   **Integration with Workflow:** The `respond_to_inquiry` function is designed as a node in the LangGraph workflow, accepting `AdvisorInput` (which includes the state from previous agents) and returning `AdvisorOutput` or an error, conforming to the `WorkflowNodeOutput` type.

Architecturally, this file implements the RAG pattern to provide domain-specific knowledge (product information) to the LLM, enabling it to answer customer questions accurately. It depends on the Classifier for initial analysis and the Stockkeeper for resolved product details, demonstrating its position downstream in the workflow for inquiry handling.

[Link to source file](../../../../src/hermes/agents/advisor/agent.py) 