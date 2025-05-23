# Summary of src/hermes/agents/classifier/README.md

**File Link:** [`src/hermes/agents/classifier/README.md`](/src/hermes/agents/classifier/README.md)

This file is the README documentation for the Email Analyzer Agent (Classifier agent). It provides a high-level overview and guide for developers.

**Purpose and Responsibilities:**

-   **Agent Overview:** Introduces the Email Analyzer Agent and its role in extracting structured information from customer emails.
-   **Structure:** Outlines the organization of files within the classifier directory, listing key components like models, prompts, and the main agent logic file (referencing `analyze_email.py`).
-   **Agent Flow:** Describes the sequence of operations within the agent, from receiving email data to using the LLM with a specific prompt and returning the structured output.
-   **Configuration:** Details the relevant settings from `HermesConfig` that influence the agent's behavior, specifically related to the LLM provider and weak model name.
-   **Prompts and Models:** Lists the specific prompt templates (`classifier`) and Pydantic models (`EmailAnalysisResult`, `Segment`, `ProductMention`, `ClassifierInput`, `ClassifierOutput`) used by the agent.
-   **Usage Example:** Provides a clear Python code example demonstrating how to initialize the configuration and run the `analyze_email` function with sample data.

In summary, `README.md` serves as essential documentation for anyone wanting to understand the purpose, structure, configuration, and usage of the Classifier agent. 