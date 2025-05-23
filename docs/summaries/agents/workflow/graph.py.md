# Summary of src/hermes/agents/workflow/graph.py

**File Link:** [`src/hermes/agents/workflow/graph.py`](../../../src/hermes/agents/workflow/graph.py)

This file defines the core workflow of the Hermes agent system using LangGraph's StateGraph. It orchestrates the interaction and flow between the different agents involved in processing customer emails using a structured pipeline approach.

**Workflow Sequence:**

1. **Email Classification:** The `Classifier` node (using `analyze_email_node` wrapper) processes the incoming email to classify its intent and extract relevant information
2. **Product Resolution:** The `Stockkeeper` node (using `resolve_products_node` wrapper) identifies and resolves product mentions in the email against the product catalog
3. **Conditional Routing:** Based on the email's intent and the results of product resolution, the workflow conditionally routes to:
   - `Advisor` node only (for pure product inquiries)
   - `Fulfiller` and `Advisor` nodes (for orders with inquiries)
   - `Fulfiller` node only (for pure orders)
4. **Response Composition:** The `Composer` node brings together the results from the preceding steps to generate the final response

**Key Components:**

- **`route_resolver_result()`**: Implements conditional routing logic based on the classifier's analysis of email intent
- **Wrapper Functions**: Adapt data structures between nodes:
  - `analyze_email_node()`: Converts `OverallState` to `ClassifierInput`
  - `resolve_products_node()`: Extracts classifier output and creates `StockkeeperInput`
  - `process_order_node()`: Complex wrapper that extracts email analysis, stockkeeper output, and promotion specs for the Fulfiller agent
- **Graph Configuration**: Uses `StateGraph` with `OverallState`, `ClassifierInput` as input, and `HermesConfig` as config schema
- **Node Definitions**: Maps each `Nodes` enum value to its corresponding agent function or wrapper
- **Edge Definitions**: Creates the workflow flow with conditional routing after the Stockkeeper

**Error Handling:**
The wrapper functions include comprehensive error handling, checking for required dependencies (e.g., classifier output for stockkeeper, both classifier and stockkeeper outputs for fulfiller) and returning appropriate error responses using the `create_node_response` utility.

**Architecture:**
The file provides the structural backbone for end-to-end customer email processing by coordinating individual agents through a well-defined state machine. The use of wrapper functions ensures proper data transformation between agents while maintaining the integrity of the shared `OverallState` throughout the workflow. 