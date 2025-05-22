## File: src/hermes/agents/fulfiller/prompts.py

This file defines the LangChain prompt templates used by the Fulfiller agent (Order Processor).

**Key Components:**

*   **`PROMPTS: dict[str, PromptTemplate]`**: A dictionary to store all prompt templates, keyed by a string identifier (e.g., `Agents.FULFILLER`).

*   **`fulfiller_prompt_template_str: markdown`**: This is the main prompt for the Fulfiller agent.
    *   **System Instructions:**
        *   Role: "efficient Order Processing Agent for a fashion retail store."
        *   Goal: Process resolved products, determine stock, mark items (created/out_of_stock), update inventory, prepare for promotion application, suggest alternatives for OOS, compile results.
        *   Output: Structured order processing result for the Response Composer.
    *   **Important Guidelines:**
        *   Use Stockkeeper output for resolved products.
        *   Default quantity to 1 if not specified.
        *   Suggest alternatives for OOS items (same category, season-appropriate, complementary).
        *   Always update inventory.
        *   Promotion information is handled by a separate system; agent should just prepare items with correct IDs, quantities, prices.
        *   Focus on order segments in mixed-intent emails.
        *   Calculate total price based on available items only.
        *   Set `overall_status` based on item statuses ("created", "out_of_stock", "partially_fulfilled", "no_valid_products").
    *   **Output Format:**
        *   MUST be a valid JSON object following an `OrderProcessingResult` model (Note: The agent code actually expects an `Order` model from `src.hermes.model.order`. The fields listed in the prompt largely align with the `Order` and `OrderLine` models, though there are slight naming differences or fields that might be handled differently by the tools, like `stock` vs `available_stock`, and `price` vs `base_price`/`unit_price`).
        *   Includes fields like `email_id`, `overall_status`, `ordered_items` (array of `OrderedItem`-like objects), `total_price`, `message`, `stock_updated`.
        *   `OrderedItem` fields include `product_id`, `name`, `description`, `category`, `product_type`, `seasons`, `price`, `quantity`, `status`, `total_price`, `available_stock`, `alternatives`, `promotion` (initially null).
    *   **User Request Section:**
        *   Inputs: `{{email_analysis}}`, `{{resolved_products}}` (using Mustache templating).
        *   Instruction: "Please process this order request and return a complete `OrderProcessingResult`."

*   **`promotion_calculation_prompt_template_str: markdown`**: A fallback prompt for calculating discounted prices if the promotion tool fails.
    *   Inputs: `{{original_price}}`, `{{promotion_text}}`, `{{quantity}}`.
    *   Instruction: Analyze promotion, determine final unit price. Handle percentage discounts, BOGO. If unclear, return original price.
    *   Output: ONLY the final unit price as a decimal number.

*   **Prompt Registration:**
    *   `PROMPTS[Agents.FULFILLER]` is set to a `PromptTemplate` created from `fulfiller_prompt_template_str`.
    *   `PROMPTS["PROMOTION_CALCULATOR"]` is set to a `PromptTemplate` from `promotion_calculation_prompt_template_str`.

*   **`get_prompt(key: str) -> PromptTemplate` function:**
    *   Retrieves a compiled `PromptTemplate` from the `PROMPTS` dictionary by its key.
    *   Raises a `KeyError` if the key is not found.

**Observations:**

*   The main fulfiller prompt specifies an output format named `OrderProcessingResult` and details its fields. While the `process_order` function in `agent.py` uses `llm.with_structured_output(Order)`, the field descriptions in the prompt are intended to guide the LLM to produce a structure compatible with the `Order` and `OrderLine` Pydantic models from `src.hermes.model.order`.
*   The prompt gives specific instructions on how to handle stock, alternatives, and pricing before promotions are applied by a separate system/tool (`apply_promotion` tool).
*   A fallback mechanism for promotion calculation via LLM is defined, though it's intended for situations where the primary tool-based approach fails. 