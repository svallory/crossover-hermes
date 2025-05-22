# Summary of src/hermes/agents/classifier/agent.py

**File Link:** [`src/hermes/agents/classifier/agent.py`](/src/hermes/agents/classifier/agent.py)

This file contains the core implementation of the Classifier agent within the Hermes system. Its primary function is to analyze incoming customer emails to extract structured information.

**Purpose and Responsibilities:**

-   **Email Analysis:** The main asynchronous function `analyze_email` takes the email subject and message as input.
-   **LLM Interaction:** It utilizes a language model (configured with a "weak" model strength) and a specific prompt (`get_prompt("classifier")`) to process the email content.
-   **Information Extraction:** The LLM is tasked with identifying the email's primary intent (e.g., order, inquiry), segmenting the message, extracting product mentions, identifying customer signals (urgency, sentiment), and recognizing potential customer PII.
-   **Output Parsing and Validation:** It handles the parsing of the LLM's output, which is expected to be in JSON format corresponding to the `EmailAnalysis` model. Includes error handling for invalid or unparseable output.
-   **Structured Output:** Returns a `WorkflowNodeOutput` containing a `ClassifierOutput` object, which encapsulates the structured `EmailAnalysis` result. Includes a helper function `get_product_mention_stats` for summarizing product mentions.

In summary, `agent.py` for the Classifier is responsible for the initial interpretation and structuring of the customer's email, converting raw text into a format that subsequent agents in the workflow can utilize. 