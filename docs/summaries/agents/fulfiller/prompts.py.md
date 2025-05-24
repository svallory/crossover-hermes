# Summary of src/hermes/agents/fulfiller/prompts.py

This file, `prompts.py`, defines the LangChain prompt templates used by the Fulfiller agent (Order Processor) to guide Large Language Model (LLM) interactions for processing customer orders and handling promotions.

Key components and responsibilities:
-   **Main Fulfiller Prompt (`fulfiller_prompt_template_str`):** This is the primary prompt for the Fulfiller agent. Its responsibilities include:
    -   Instructing the LLM to act as an "efficient Order Processing Agent."
    -   Guiding the LLM to use resolved product information from the Stockkeeper agent.
    -   Detailing how to handle stock (default quantity, suggest alternatives for out-of-stock items, update inventory).
    -   Specifying that promotion information is handled by a separate system/tool, but the agent should prepare items with correct details for it.
    -   Defining the output structure, which should be a JSON object compatible with the `Order` Pydantic model from `hermes.model.order` (though the prompt refers to it as `OrderProcessingResult`). This includes fields for overall status, ordered items with their details (ID, name, price, quantity, status, alternatives), total price, and a message.
    -   Taking `{{email_analysis}}` and `{{resolved_products}}` as input.
-   **Promotion Calculation Fallback Prompt (`promotion_calculation_prompt_template_str`):** This prompt serves as a fallback mechanism if a dedicated promotion tool fails.
    -   It instructs the LLM to analyze a promotion text (e.g., percentage discount, BOGO) and calculate the final unit price for an item.
    -   It takes `{{original_price}}`, `{{promotion_text}}`, and `{{quantity}}` as input.
    -   The expected output is *only* the final unit price as a decimal number.
-   **Prompt Management (`PROMPTS` dictionary and `get_prompt` function):**
    -   The compiled `PromptTemplate` objects from the string templates are stored in the `PROMPTS` dictionary, keyed by identifiers like `Agents.FULFILLER` and `"PROMOTION_CALCULATOR"`.
    -   The `get_prompt(key: str)` function allows retrieval of these compiled prompts, raising a `KeyError` if a key is not found.

Architecturally, `prompts.py` for the Fulfiller agent provides the instructional backbone for its LLM interactions. The main prompt ensures that the LLM processes order requests systematically, considering stock, alternatives, and preparing for promotions, while outputting a structured result compatible with the Hermes `Order` model. The fallback promotion prompt adds a layer of resilience for promotion calculations. This separation of concerns into distinct prompts allows for targeted guidance of the LLM for different aspects of order fulfillment.

[Link to source file](../../../../src/hermes/agents/fulfiller/prompts.py) 