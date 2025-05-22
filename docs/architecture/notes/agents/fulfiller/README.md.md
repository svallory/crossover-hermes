## File: src/hermes/agents/fulfiller/README.md

This file provides an overview of the Fulfiller agent.

**Purpose:**

*   Processes customer order requests, using resolved products from the Stockkeeper.
*   Checks stock, creates order items, suggests alternatives for OOS items, updates inventory.
*   Applies promotions using a declarative system (`PromotionSpec`).
*   Outputs an `Order`

**Workflow Summary:**

1.  Receives resolved products from Stockkeeper.
2.  Checks stock, creates order lines, suggests alternatives, updates inventory.
3.  Uses `apply_promotion` tool to apply promotions.
4.  Formats results into an `Order` object.

**Key Functionality:**

*   Stock verification.
*   Inventory management.
*   Alternative product suggestions.
*   Promotion processing.

**Components:**

*   `agent.py` (previously `process_order.py` in README): Main logic for `process_order` function.
*   `models.py`: Pydantic models for input/output.
*   `prompts.py`: LLM prompts.

**Integration:**

*   Receives email analysis from Email Analyzer (Classifier).
*   Passes `Order` (as `order_result` in `FulfillerOutput`) to Response Composer.

**Promotion System:**

*   Uses `PromotionSpec` objects defining conditions and effects.
*   Allows for easy addition of new promotions, independent testing, and tracking.

**Note:** The README mentions `ProcessedOrder` as the output, but the actual implementation uses the `Order` model from `src.hermes.model.order`. The file name `process_order.py` mentioned in the README for the main entry point is also incorrect; it's `agent.py` which contains the `process_order` function. 