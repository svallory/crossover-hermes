# Summary of src/hermes/agents/fulfiller/README.md

This file, `README.md`, provides a comprehensive overview and documentation for the Fulfiller agent, also known as the Order Processor, within the Hermes system. It outlines the agent's purpose, core functionalities, workflow, components, and integration points.

Key components and responsibilities:
-   **Purpose:** The Fulfiller agent is responsible for processing customer order requests. This involves using resolved product information from the Stockkeeper agent to verify stock, create order items, suggest alternatives for out-of-stock (OOS) items, and update inventory.
-   **Workflow Summary:**
    1.  Receives resolved products (from Stockkeeper) and email analysis (from Classifier).
    2.  Processes order segments, checks stock, creates order lines for available items.
    3.  Suggests alternatives for OOS items.
    4.  Updates inventory based on fulfilled items.
    5.  Utilizes an `apply_promotion` tool to apply promotions based on `PromotionSpec` objects.
    6.  Formats the final processed order into an `Order` object (from `hermes.model.order`).
-   **Key Functionality:**
    -   Stock verification and inventory management.
    -   Creation of order lines with accurate pricing and quantities.
    -   Alternative product suggestions for unavailable items.
    -   Promotion processing using a declarative system (`PromotionSpec`).
-   **Components:** The agent is composed of:
    -   `agent.py`: Contains the main logic in the `process_order` function.
    -   `models.py`: Defines Pydantic models for input (`FulfillerInput`) and output (`FulfillerOutput`, which wraps the `Order` model).
    -   `prompts.py`: Contains LLM prompt templates for guiding order processing and promotion calculation.
-   **Integration:**
    -   Receives `ClassifierOutput` from the Classifier agent (via `FulfillerInput`).
    -   Receives `StockkeeperOutput` from the Stockkeeper agent (via `FulfillerInput`).
    -   Its output (`FulfillerOutput` containing the `Order`) is passed to the Response Composer agent.
-   **Promotion System:** Leverages `PromotionSpec` objects that define promotion conditions and effects, allowing for a modular and extensible way to manage discounts and offers. The agent prepares order items for this system and uses a tool to apply them.
-   **Usage Example:** Provides a Python code snippet demonstrating how to instantiate `FulfillerInput` (with prerequisite outputs from Classifier and Stockkeeper) and call the `process_order` function.

Architecturally, the Fulfiller agent plays a crucial role in the Hermes e-commerce workflow by handling the transactional aspects of customer orders. It acts as an intermediary between product resolution (Stockkeeper) and final response generation (Composer), ensuring orders are processed accurately according to stock availability and applicable promotions. The README clarifies its dependencies, internal structure, and its use of a sophisticated promotion system.

[Link to source file](../../../../src/hermes/agents/fulfiller/README.md) 