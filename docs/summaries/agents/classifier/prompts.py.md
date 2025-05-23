# Summary of src/hermes/agents/classifier/prompts.py

**File Link:** [`src/hermes/agents/classifier/prompts.py`](/src/hermes/agents/classifier/prompts.py)

This file defines the detailed prompt template used by the Classifier agent (`src/hermes/agents/classifier/agent.py`) to instruct the language model on how to analyze customer emails and format the output.

**Purpose and Responsibilities:**

-   **LLM Instruction:** Contains the `classifier_prompt_template_str`, which provides the language model with explicit instructions on its role, the information to extract (email segments, product mentions, primary intent, PII), and detailed guidelines for the analysis process.
-   **Output Format Specification:** Defines the required JSON structure for the language model's output, ensuring that the extracted information conforms to the `EmailAnalysis` and related Pydantic models defined in `models.py`. This includes specifying field names, types, and expected values (e.g., for `primary_intent`, `segment_type`).
-   **Extraction Guidelines:** Includes specific instructions and rules for handling various aspects of the email, such as segmenting, identifying different types of product information (IDs, names, types, descriptions), assigning confidence scores, and extracting PII, with examples and caveats.
-   **Prompt Management:** Provides a simple dictionary (`PROMPTS`) and a helper function (`get_prompt`) for storing and retrieving prompt templates, although currently, it only contains the classifier prompt.

In summary, `prompts.py` is the configuration layer for the Classifier agent's interaction with the LLM, ensuring that the model performs the analysis as required and provides output in a machine-readable, structured format necessary for the subsequent steps in the Hermes workflow. 