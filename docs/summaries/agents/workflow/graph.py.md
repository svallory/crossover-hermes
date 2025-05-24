# Summary of src/hermes/agents/workflow/graph.py

This file, `graph.py`, defines the core operational workflow of the Hermes agent system using LangGraph's `StateGraph`. It orchestrates the sequence and conditional flow of various specialized agents (Classifier, Stockkeeper, Advisor, Fulfiller, Composer) to process customer emails from initial analysis to final response generation.

Key components and responsibilities:
-   **State Management (`OverallState`):** The workflow operates on a shared `OverallState` object (defined in `states.py`), which accumulates data and errors as the email progresses through different agent nodes.
-   **Node Definitions:** Each agent's primary function (e.g., `analyze_email` for Classifier, `resolve_product_mentions` for Stockkeeper) is wrapped into a node within the graph. These wrappers (e.g., `analyze_email_node`, `resolve_products_node`, `process_order_node`) handle input/output adaptation between the `OverallState` and the specific agent's input/output models.
    -   `analyze_email_node`: Wraps the Classifier agent.
    -   `resolve_products_node`: Wraps the Stockkeeper agent.
    -   `process_order_node`: Wraps the Fulfiller agent, handling complex input aggregation.
    -   `respond_to_inquiry_node`: Wraps the Advisor agent.
    -   `compose_response_node`: Wraps the Composer agent.
-   **Edge Definitions and Conditional Routing (`route_resolver_result`):**
    -   The graph defines edges connecting these nodes in a logical sequence: Classifier -> Stockkeeper.
    -   After the Stockkeeper, a crucial conditional routing function, `route_resolver_result`, determines the next step(s) based on the email's classified intent (inquiry, order, or both) and whether products were successfully resolved.
        -   If only inquiry: routes to Advisor.
        -   If only order: routes to Fulfiller.
        -   If both order and inquiry: routes to both Fulfiller and Advisor (implicitly, as they can run in parallel or sequence before Composer).
        -   If neither or unresolved products with no clear path: routes directly to Composer for a basic response/error handling.
    -   All paths eventually converge on the `Composer` node, which generates the final customer response.
-   **Graph Compilation:** The defined nodes and edges are compiled into an executable `workflow` object using `StateGraph(OverallState).compile()`.
-   **Configuration (`HermesConfig`):** The graph is configured to accept `HermesConfig` for its operations.
-   **Error Handling in Wrappers:** The node wrapper functions include error handling to catch issues during agent execution and record them in the `OverallState.errors` field, ensuring that failures in one agent don't necessarily halt the entire workflow but are reported.

Architecturally, `graph.py` implements the central nervous system of the Hermes application. It leverages LangGraph to create a resilient and flexible state machine that manages the complex interactions between different AI agents. The conditional routing logic allows for dynamic adaptation to various email types, ensuring that only relevant agents are invoked. The wrapper functions serve as important adaptors, ensuring data compatibility and isolating agent-specific logic from the graph structure itself. This modular design facilitates easier maintenance and extension of the workflow.

[Link to source file](../../../../src/hermes/agents/workflow/graph.py) 