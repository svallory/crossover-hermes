# Summary of src/hermes/agents/workflow/graph.py

**File Link:** [`src/hermes/agents/workflow/graph.py`](/src/hermes/agents/workflow/graph.py)

This file defines the core workflow of the Hermes agent system using LangGraph's StateGraph. It orchestrates the interaction and flow between the different agents involved in processing customer emails. The main sequence of operations is:

1.  **Email Analysis:** The `analyze_email` node (using `analyze_email_node` wrapper) processes the incoming email to classify its intent and extract relevant information.
2.  **Product Resolution:** The `resolve_product_mentions` node (using `resolve_products_node` wrapper) identifies and resolves product mentions in the email against the product catalog.
3.  **Conditional Routing:** Based on the email's intent and the results of product resolution, the workflow conditionally routes the process to either the Fulfiller agent (`process_order_node`) for order-related tasks, the Advisor agent (`respond_to_inquiry_node`) for inquiries, or both.
4.  **Response Composition:** The `compose_response` node brings together the results from the preceding steps to generate the final response to the customer.

The file sets up the nodes for each agent function and defines the edges (transitions) that dictate the flow based on the state of the process. It includes wrapper functions (`analyze_email_node`, `resolve_products_node`, `process_order_node`) to adapt the data structure passed between nodes to match the expected input of the underlying agent functions, primarily converting or extracting necessary information from the shared `OverallState`. The `route_resolver_result` function implements the conditional logic for routing after product resolution.

Overall, `graph.py` provides the structural backbone for how customer emails are processed end-to-end within the Hermes system by coordinating the activities of the individual agents. 