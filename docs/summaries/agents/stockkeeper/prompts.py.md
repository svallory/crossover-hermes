This file, `prompts.py`, manages the various large language model (LLM) prompt templates used by the Stockkeeper agent to perform specific product resolution sub-tasks. Unlike agents that might use a single core prompt, the Stockkeeper utilizes different prompts tailored for ambiguity resolution, mention deduplication, and suggesting alternatives for out-of-stock items.

Key prompt templates defined are:
-   `DISAMBIGUATION_PROMPT_STR`: Guides the LLM to analyze an original product mention from the email context and compare it against a list of candidate products to determine the most likely match, or state if it's undecidable. The response is expected in a JSON format including the selected product ID, confidence, and reasoning.
-   `DEDUPLICATION_PROMPT_STR`: Instructs the LLM to review a list of extracted product mentions within the email context and identify/merge those referring to the same product. The output should be a JSON array of deduplicated and potentially enhanced product mentions, including summed quantities if duplicates were merged.
-   `ALTERNATIVE_SUGGESTION_PROMPT_STR`: Used for suggesting alternative products when a requested item is out of stock or unavailable. It provides details of the original product and a list of available candidates, asking the LLM to select the best alternatives based on similarity and features, returning them in a JSON array with reasoning.

These templates are stored in the `PROMPTS` dictionary, accessible via the `get_prompt` function.

Architecturally, this file demonstrates how a single agent's complex responsibilities can be broken down into distinct sub-tasks, each guided by a specialized LLM prompt. By separating concerns into different prompts, the Stockkeeper agent can leverage the LLM's capabilities for more nuanced reasoning tasks (like disambiguation and deduplication) beyond simple data retrieval, making the product resolution process more robust and intelligent.

[Link to source file](../../../../src/hermes/agents/stockkeeper/prompts.py) 