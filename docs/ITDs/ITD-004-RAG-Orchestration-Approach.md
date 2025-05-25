# ITD-004: RAG Orchestration Approach for Hermes PoC

**Date:** 2024-07-26
**Updated:** 2024-12-XX (Implementation Review)
**Author:** Gemini Assistant
**Status:** Implemented

## 1. Context

Task 3 (Handle Product Inquiry) requires implementing a Retrieval-Augmented Generation (RAG) system within a multi-agent workflow. This involves:
1.  Taking a customer's email inquiry processed by the Classifier agent.
2.  Embedding the inquiry text (using OpenAI `text-embedding-3-small`, per ITD-002).
3.  Searching the product vector database (ChromaDB, per ITD-001) for relevant product information.
4.  Constructing a prompt for the LLM (GPT-4o) that includes the original inquiry and the retrieved product context.
5.  Generating a final response based on the inquiry and context.
6.  Coordinating with other agents (Stockkeeper, Fulfiller, Composer) in a unified workflow.

We need to decide how to orchestrate these steps and the overall multi-agent workflow: use a dedicated framework/library or implement the logic directly.

## 2. Requirements

*   **Multi-Agent Workflow:** Must orchestrate multiple specialized agents (Classifier, Stockkeeper, Fulfiller, Advisor, Composer) in a coordinated sequence.
*   **Conditional Routing:** Support conditional paths based on email classification (order vs inquiry vs hybrid).
*   **State Management:** Maintain comprehensive state across multiple agent interactions.
*   **Error Handling:** Provide robust error isolation and recovery across agent boundaries.
*   **Parallel Execution:** Enable concurrent execution of Fulfiller and Advisor agents for hybrid emails.
*   **Integration:** Work smoothly with the chosen components: ChromaDB, OpenAI client, product catalog tools.
*   **Observability:** Allow clear visibility and control over each workflow step for debugging and monitoring.
*   **Maintainability:** Code should be easy to understand, modify, and extend with additional agents.
*   **Professional Scalability:** Architecture should support future production deployment and scaling needs.

## 3. Options Considered

1.  **Custom Implementation:**
    *   **Method:** Write Python code to explicitly coordinate agent sequence: call each agent function in order, manage state passing, implement conditional routing logic manually.
    *   **Pros:** Full control over every step, maximum transparency, no additional framework dependencies, potentially simpler for a single linear workflow.
    *   **Cons:** Significant boilerplate for multi-agent coordination, complex state management across agents, manual error handling, difficult to implement conditional routing and parallel execution, less reusable for workflow variations.

2.  **LangGraph Framework:**
    *   **Method:** Use LangGraph's `StateGraph` to define agents as nodes, implement conditional routing with `add_conditional_edges`, manage state with Pydantic models, leverage built-in error handling and observability.
    *   **Pros:** Purpose-built for agent workflows, excellent state management, built-in conditional routing, parallel execution support, integrated error handling, LangSmith observability, professional workflow patterns, future-proof architecture.
    *   **Cons:** Introduces LangGraph dependency, requires learning LangGraph concepts and patterns, slightly more complex initial setup compared to simple sequential calls.

3.  **Generic Workflow Engines (Celery, Airflow, etc.):**
    *   **Method:** Use general-purpose workflow orchestration tools to coordinate agent execution.
    *   **Pros:** Mature workflow management, enterprise-grade features.
    *   **Cons:** Overkill for agent coordination, not designed for LLM/agent-specific patterns, complex setup, heavy infrastructure requirements.

## 4. Comparison

| Feature                      | Custom Implementation     | LangGraph                              | Generic Workflow Engines |
| :--------------------------- | :------------------------ | :------------------------------------- | :----------------------- |
| **Multi-Agent Coordination** | Manual (High Complexity)  | **Excellent (Built-in)**               | Good (Generic)           |
| **Conditional Routing**      | Manual Implementation     | **Built-in (`add_conditional_edges`)** | Possible (Complex)       |
| **State Management**         | Manual (Error-prone)      | **Excellent (Pydantic Models)**        | Basic                    |
| **Parallel Execution**       | Complex to Implement      | **Built-in Support**                   | Good                     |
| **Error Isolation**          | Manual                    | **Built-in**                           | Good                     |
| **Observability**            | None                      | **LangSmith Integration**              | Varies                   |
| **Learning Curve**           | Low (Basic Python)        | Medium (LangGraph Concepts)            | High (Infrastructure)    |
| **Agent-Specific Features**  | None                      | **Purpose-built for Agents**           | None                     |
| **Production Readiness**     | Requires Significant Work | **Production-ready**                   | High (Overkill)          |
| **Development Velocity**     | Slow (Manual Everything)  | **Fast (Pre-built Patterns)**          | Slow (Setup Overhead)    |

## 5. Decision

**Option 2: LangGraph Framework** is selected for orchestrating the RAG pipeline and overall multi-agent workflow.

## 6. Rationale

For the complex multi-agent workflow required by Hermes, LangGraph provides the optimal balance of functionality, maintainability, and professional architecture:

*   **Agent-Native Design:** LangGraph is purpose-built for agent workflows, providing patterns and abstractions specifically designed for multi-agent coordination rather than generic task orchestration.

*   **Sophisticated State Management:** The `OverallState` Pydantic model enables type-safe state passing between agents, automatic validation, and clear data contracts. This eliminates the error-prone manual state management required in custom implementations.

*   **Built-in Conditional Routing:** The `add_conditional_edges` functionality enables clean implementation of email classification routing:
    ```python
    # Route after product resolution based on email intents
    return (
        Nodes.ADVISOR if analysis.primary_intent == "product inquiry"
        else [Nodes.FULFILLER, Nodes.ADVISOR] if analysis.has_inquiry()
        else Nodes.FULFILLER
    )
    ```

*   **Parallel Execution Support:** LangGraph naturally handles parallel agent execution for hybrid emails that require both order processing (Fulfiller) and inquiry handling (Advisor), significantly improving performance and user experience.

*   **Professional Error Handling:** Built-in error isolation ensures that failures in one agent don't cascade to others, with comprehensive error tracking in the workflow state.

*   **Observability and Debugging:** Integration with LangSmith provides professional workflow monitoring, execution traces, and debugging capabilities essential for production deployments.

*   **Future-Proof Architecture:** LangGraph's patterns scale naturally to more complex agent interactions, additional agents, and production deployment requirements.

The implementation demonstrates these benefits with a clean, maintainable architecture:

```python
# Clean agent workflow definition
graph_builder = StateGraph(OverallState, input=ClassifierInput, config_schema=HermesConfig)
graph_builder.add_node(Nodes.CLASSIFIER, analyze_email_node)
graph_builder.add_node(Nodes.STOCKKEEPER, resolve_products_node)
graph_builder.add_node(Nodes.FULFILLER, process_order_node)
graph_builder.add_node(Nodes.ADVISOR, respond_to_inquiry)
graph_builder.add_node(Nodes.COMPOSER, compose_response)

# Conditional routing based on email classification
graph_builder.add_conditional_edges(
    Nodes.STOCKKEEPER,
    route_resolver_result,
    [Nodes.FULFILLER, Nodes.ADVISOR],
)
```

While custom implementation might appear simpler for basic use cases, the complexity of multi-agent coordination, conditional routing, parallel execution, and error handling makes LangGraph's specialized patterns and built-in functionality invaluable for building a robust, maintainable system.

## 7. Implementation Details

*   **Workflow Framework:** LangGraph `StateGraph` with typed state management
*   **State Model:** `OverallState` Pydantic model for comprehensive state tracking
*   **Agent Nodes:** Five specialized agents (Classifier, Stockkeeper, Fulfiller, Advisor, Composer)
*   **Conditional Routing:** Dynamic routing based on email classification and intent analysis
*   **Parallel Execution:** Concurrent Fulfiller and Advisor processing for hybrid emails
*   **Error Handling:** Per-agent error isolation with centralized error tracking
*   **Configuration:** `HermesConfig` schema for consistent configuration across agents
*   **Entry Point:** `run_workflow()` function with vector store initialization
*   **Integration:** Seamless integration with ChromaDB, OpenAI, and catalog tools

## 8. Architecture Benefits

*   **Separation of Concerns:** Each agent focuses on its specialized task without workflow complexity
*   **Type Safety:** Pydantic models ensure data contract consistency across agent boundaries
*   **Scalability:** Built-in support for scaling to additional agents and more complex routing
*   **Testability:** Individual agents can be tested independently of workflow orchestration
*   **Maintainability:** Clear workflow visualization and standardized agent patterns
*   **Production Readiness:** Professional workflow management suitable for production deployment

## 9. Next Steps

*   ~~Add `langgraph` to the project's dependencies.~~ ✅ Complete
*   ~~Define the `OverallState` Pydantic model for comprehensive state management.~~ ✅ Complete
*   ~~Implement each agent as a LangGraph node with proper input/output handling.~~ ✅ Complete
*   ~~Configure conditional routing logic based on email classification.~~ ✅ Complete
*   ~~Implement parallel execution for Fulfiller and Advisor agents.~~ ✅ Complete
*   ~~Integrate error handling and state accumulation across agents.~~ ✅ Complete
*   ~~Test end-to-end workflow with sample emails from diverse scenarios.~~ ✅ Complete