# Summary of src/hermes/agents/advisor/README.md

**File Link:** [`src/hermes/agents/advisor/README.md`](/src/hermes/agents/advisor/README.md)

This file is the README documentation for the Inquiry Responder Agent (Advisor agent). It provides a detailed overview of the agent's function, capabilities, structure, and role within the Hermes workflow.

**Purpose and Responsibilities:**

-   **Agent Overview:** Introduces the Advisor agent as the component responsible for processing customer product inquiries.
-   **Core Capabilities:** Lists the agent's key functions, including using LLM for question extraction and classification, providing factual product information and answers, identifying related products objectively, and tracking unanswered questions.
-   **Implementation:** Outlines the main files composing the agent (`models.py`, `prompts.py`, and the core logic file, referred to as `inquiry_response.py`).
-   **Input and Output:** Describes the required input (`EmailAnalysisResult`) and the structured output (`InquiryResponse`), detailing the information contained in both.
-   **Separation of Concerns:** Explicitly explains the division of responsibilities between the Advisor (factual processing) and the Composer (response formatting and tone adaptation).
-   **LLM Usage:** Highlights how the agent leverages LLM for end-to-end factual processing of inquiries.
-   **Usage Example:** Provides a Python code example demonstrating how to use the `respond_to_inquiry` function.
-   **Extensibility:** Suggests ways to extend the agent's capabilities.

In summary, `README.md` provides a comprehensive understanding of the Advisor agent's function in handling product inquiries, its technical components, and its specific role in the overall Hermes architecture, emphasizing its focus on factual accuracy and its distinction from the response generation agent. 