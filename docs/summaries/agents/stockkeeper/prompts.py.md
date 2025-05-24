# Summary of src/hermes/agents/stockkeeper/prompts.py

This file, `prompts.py`, is responsible for defining and managing a suite of large language model (LLM) prompt templates utilized by the Stockkeeper agent. Unlike agents with a single primary prompt, the Stockkeeper employs distinct prompts for specialized sub-tasks within product resolution, such as disambiguation, deduplication, and suggesting alternatives.

Key components and responsibilities:
-   **Disambiguation Prompt (`DISAMBIGUATION_PROMPT_STR`):**
    -   Guides the LLM to analyze an original product mention from an email and compare it against a list of candidate products.
    -   The goal is to determine the most likely match or to indicate if the mention is undecidable based on the provided context.
    -   Expects a JSON response containing the selected product ID, a confidence score, and the reasoning behind the selection.
-   **Deduplication Prompt (`DEDUPLICATION_PROMPT_STR`):**
    -   Instructs the LLM to review a list of extracted product mentions from the email context.
    -   The task is to identify and merge mentions that refer to the same underlying product.
    -   The output should be a JSON array of deduplicated product mentions, potentially enhanced with summed quantities if duplicates were merged.
-   **Alternative Suggestion Prompt (`ALTERNATIVE_SUGGESTION_PROMPT_STR`):**
    -   Used when a requested product is out of stock or unavailable.
    -   Provides the LLM with details of the original product and a list of available candidate products.
    -   Asks the LLM to select the best alternative(s) based on similarity in features and other relevant criteria.
    -   Expects a JSON array of suggested alternatives, including the reasoning for each suggestion.
-   **Prompt Management:**
    -   These string templates are compiled into `PromptTemplate` objects and stored in a `PROMPTS` dictionary, keyed by descriptive strings (e.g., `"DISAMBIGUATION"`, `"DEDUPLICATION"`).
    -   A `get_prompt(key: str)` function is provided to retrieve the compiled prompts by their keys, raising a `KeyError` if a key is not found.

Architecturally, `prompts.py` for the Stockkeeper agent showcases a modular approach to leveraging LLMs. By breaking down the complex product resolution process into distinct, LLM-driven sub-tasks (disambiguation, deduplication, alternative suggestion), each guided by a specialized prompt, the agent can perform more nuanced and intelligent operations than simple lookups. This design allows for targeted LLM guidance, making the overall product resolution more robust and accurate, which is vital for the subsequent Advisor and Fulfiller agents.

[Link to source file](../../../../src/hermes/agents/stockkeeper/prompts.py) 