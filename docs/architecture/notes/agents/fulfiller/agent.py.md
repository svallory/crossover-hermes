## File: src/hermes/agents/fulfiller/agent.py

**Note: Analysis based on lines 1-250 of 273 due to token limits.**

This file defines the `process_order` function, which is the core logic for the Fulfiller agent. This agent is responsible for processing customer order requests.

**Key Responsibilities (from `agents-flow.md` and partial code):**

*   Takes email analysis and resolved products (from Stockkeeper) as input.
*   Verifies stock availability for requested products.
*   Updates inventory levels for fulfilled orders.
*   Processes ordered items with individual status tracking.
*   Applies promotions based on a list of `PromotionSpec`.
*   Suggests alternatives for out-of-stock items.
*   Calculates total prices with promotions applied.
*   Provides detailed order status information.

**Function: `process_order`**

*   **Inputs:**
    *   `email_analysis: dict[str, Any]`: Output from the Classifier agent (or relevant parts of `OverallState`).
    *   `stockkeeper_output: StockkeeperOutput`: Output from the Stockkeeper agent, containing resolved products.
    *   `promotion_specs: list[PromotionSpec]`: A list of promotion specifications to apply to the order.
    *   `email_id: str`: ID of the email being processed.
    *   `model_strength: Literal["weak", "strong"]`: Specifies LLM strength.
    *   `temperature: float`: LLM temperature setting.
    *   `hermes_config: HermesConfig | None`: System configuration.
*   **Output:**
    *   `Order`: A Pydantic model representing the processed order, including line items, statuses, promotions, and totals.

**Core Logic (lines 1-250):**

1.  **Initialization:**
    *   Prints a message indicating the start of order processing.
    *   Retrieves the Fulfiller agent's prompt using `get_prompt(Agents.FULFILLER)`.
    *   Initializes the LLM client (`get_llm_client`) based on `hermes_config`, `model_strength`, and `temperature`.
    *   Extracts the relevant `email_analysis` dictionary, handling cases where it might be nested within an `OverallState` object or a dictionary.
2.  **LLM Invocation for Initial Order Structure:**
    *   Creates an LLM chain (`fulfiller_prompt | llm.with_structured_output(Order)`). This chain is expected to take the email analysis and resolved products and return an initial `Order` structure.
    *   Invokes the chain with `email_analysis` and `stockkeeper_output` (both JSON dumped) as input.
    *   Handles the LLM response:
        *   If it's already an `Order` object, use it.
        *   If it's a dictionary, convert it to an `Order` object, ensuring `email_id` and a default `overall_status` are set.
        *   Provides a fallback `Order` object in case of unexpected response types.
    *   Ensures `processed_order.email_id` is correctly set.
3.  **Order Line Item Processing:**
    *   If `processed_order.lines` (list of `OrderLine`) exists:
        *   Initializes `total_price = 0.0` and `order_items = []` (used for promotion application).
        *   Iterates through each `line` in `processed_order.lines`:
            *   **Stock Checking:**
                *   Calls `check_stock` tool (from `src.hermes.tools.order_tools`) with `product_id` and `requested_quantity`.
                *   Calls `find_product_by_id` tool (from `src.hermes.tools.catalog_tools`) to get product details.
                *   If `stock_result` is `StockStatus` and `is_available`:
                    *   Sets `line.status` to `OrderLineStatus.CREATED`.
                    *   Sets `line.stock` to `stock_result.current_stock`.
                    *   If `product_result` is `Product`, creates an `order_item` dictionary (for promotions) with `product_id`, `description`, `base_price`, `quantity`.
                    *   Calls `update_stock` tool to decrement stock. If successful, sets `processed_order.stock_updated = True`.
                    *   Adds `line.total_price` to `total_price` (pre-promotion).
                *   If `stock_result` is `StockStatus` but `is_available` is false (out of stock):
                    *   Sets `line.status` to `OrderLineStatus.OUT_OF_STOCK`.
                    *   Sets `line.stock` to `stock_result.current_stock`.
                    *   Calls `find_alternatives_for_oos` tool to find alternatives; if found, assigns to `line.alternatives`.
                *   If `stock_result` is `ProductNotFound` or an unexpected type, sets `line.status` to `OrderLineStatus.OUT_OF_STOCK` and `line.stock = 0`.
                *   Includes a `try-except` block to catch errors during item processing, setting status to `OUT_OF_STOCK` on error.
4.  **Promotion Application:**
    *   If `order_items` (items confirmed in stock) exist:
        *   Calls `apply_promotion` tool (from `src.hermes.tools.promotion_tools`) with `order_items`, `promotion_specs` (model dumped), and `email_id`.
        *   If `order_result` is an `Order` object:
            *   Iterates through `processed_order.lines` and updates them based on `order_result.lines` (matching by `product_id`):
                *   If `promotion_applied` in `order_line`, creates a simple `PromotionSpec` with the description and assigns it to `line.promotion`.
                *   Updates `line.unit_price` and `line.total_price` from `order_line`.
            *   Updates `processed_order.total_discount` and `processed_order.total_price` (sum of `total_price` for `CREATED` lines) from `order_result`.
        *   Includes a `try-except` block; if `apply_promotion` fails, uses original `total_price`.
    *   If no `order_items` (nothing in stock), sets `processed_order.total_price = 0.0`.
5.  **Determine Overall Order Status (lines 246-250 shown):**
    *   Counts `in_stock_count` and `total_count` of lines.
    *   (The rest of the logic for setting `overall_status` is not visible in the provided snippet but would likely depend on these counts).

**Models Used:**

*   LLM (specific model determined by `hermes_config` and `model_strength`). Link: Not specified, depends on `get_llm_client` implementation.

**Tools Used:**

*   `get_prompt` (from `.prompts`)
*   `get_llm_client` (from `src.hermes.utils.llm_client`)
*   `check_stock` (from `src.hermes.tools.order_tools`)
*   `find_product_by_id` (from `src.hermes.tools.catalog_tools`)
*   `update_stock` (from `src.hermes.tools.order_tools`)
*   `find_alternatives_for_oos` (from `src.hermes.tools.order_tools`)
*   `apply_promotion` (from `src.hermes.tools.promotion_tools`)

**Input/Output Data Models (Pydantic):**

*   Input: `StockkeeperOutput` (from `src.hermes.agents.stockkeeper.models`)
*   Input: `PromotionSpec` (from `src.hermes.model.promotions`)
*   Output: `Order`, `OrderLine` (from `src.hermes.model.order`)
*   Uses `OrderLineStatus` enum (from `src.hermes.model.order`)
*   Interacts with tool output models: `StockStatus`, `ProductNotFound`, `StockUpdateResult` (from `src.hermes.tools.order_tools`), `Product` (from `src.hermes.tools.catalog_tools`). 