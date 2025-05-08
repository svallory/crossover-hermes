# Hermes System Agents

This section details the implementation of the core intelligent agents that form the backbone of the Hermes email processing system. Each agent is a specialized component within a larger LangGraph workflow, responsible for a distinct set of tasks in analyzing customer emails and formulating appropriate responses.

## Agent Architecture Overview

The Hermes system employs a multi-agent architecture, as depicted in the main introduction (`src/__intro__.md`). This design, inspired by `reference-agent-flow.md` and `reference-solution-spec.md`, promotes modularity, separation of concerns, and allows for sophisticated, stateful processing of emails. The primary agents are:

1.  **Email Analyzer Agent (`email_classifier.py`)**: The first point of contact for an incoming email. It performs comprehensive initial analysis.
2.  **Order Processor Agent (`order_processor.py`)**: Handles emails classified as order requests, interacting with inventory and order tools.
3.  **Inquiry Responder Agent (`inquiry_responder.py`)**: Manages product inquiries, primarily using Retrieval-Augmented Generation (RAG) with the product catalog.
4.  **Response Composer Agent (`response_composer.py`)**: The final agent in the chain, responsible for generating the polished, customer-facing email response.

(A `supervisor.py` was mentioned in `reference-solution-spec.md` but the primary flow in `reference-agent-flow.md` details these four core processing agents. If a supervisor is implemented for more complex routing or meta-control, it would also be described here.)

## Agent Implementation Pattern

As per `reference-solution-spec.md#3-agents-nodes`, each agent is typically implemented as a Python function (or a class with a `__call__` method if it needs to maintain internal state beyond the graph state). These functions serve as nodes in the LangGraph `StateGraph`.

**Key characteristics of agent implementation:**

-   **State Interaction**: Each agent function receives the current `HermesState` (defined in `src/state.py`) as input and is expected to return a dictionary containing the updates to the state. For example, the `Email Analyzer Agent` would populate the `email_analysis_output` field in the state.
-   **LLM Interaction**: Agents that require LLM reasoning (e.g., `Email Analyzer`, `Inquiry Responder`, `Response Composer`) will use an LLM instance (configured via `HermesConfig`) along with their specific prompts (from `src/prompts/`).
    -   For tasks requiring structured output from the LLM (like the `EmailAnalysis` Pydantic model), agents will employ mechanisms like LangChain's `create_structured_output_chain` or ensure their prompts guide the LLM to produce parseable JSON.
-   **Tool Usage**: Agents like the `Order Processor` and `Inquiry Responder` will make use of tools (defined in `src/tools/`) to interact with external data (product catalog, inventory) or perform specific actions. They will use the LLM to decide which tools to call and with what arguments, or tools will be called programmatically based on structured data.
-   **Pydantic Models for IO**: Agents will internally work with or produce Pydantic models for complex data structures (e.g., `EmailAnalysis`, `OrderProcessingResult`, `InquiryResponse` as detailed in `reference-agent-flow.md`). This ensures data integrity and clarity.
-   **Error Handling**: Basic error handling and logging should be incorporated within each agent to manage issues during LLM calls or tool execution.

## Workflow and Graph Integration

These agents are connected within the main `StateGraph` defined in `src/pipeline.py`. The `pipeline.py` module will define the nodes (mapping to these agent functions) and the edges (defining the flow of control, including conditional edges based on classification results).

The following files in this directory will provide the specific implementations for each agent node.

```python {cell}
# This is a placeholder Python cell that might be used for initial imports or setup
# when the notebook is assembled for the agents section.
print("Hermes Solution Notebook - Agents Introduction Loaded")
``` 