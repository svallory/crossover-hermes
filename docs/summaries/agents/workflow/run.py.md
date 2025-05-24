# Summary of src/hermes/agents/workflow/run.py

This file, `run.py` (sometimes referred to as `run_workflow.py` in comments), provides the primary entry point for executing the entire Hermes agent workflow. Its main component is the `run_workflow` asynchronous function.

Key components and responsibilities:
-   **Workflow Execution (`run_workflow` function):**
    -   Serves as the main asynchronous function to initiate and run the complete agent pipeline.
    -   Takes initial email data (as `ClassifierInput`) and the system configuration (`HermesConfig`) as input.
-   **Vector Store Initialization:** Critically, it ensures that the `VectorStore` singleton is initialized with the provided `HermesConfig` *before* the workflow graph is invoked. This is essential as agents like the Advisor (Inquiry Responder) and Stockkeeper (for semantic search) depend on the vector store being ready.
-   **Configuration Management for LangGraph:** It prepares the `RunnableConfig` required by LangGraph, embedding the `HermesConfig` within it so that all nodes in the workflow can access system-wide settings.
-   **Workflow Invocation:** It imports the compiled `workflow` (the `StateGraph` instance) from `graph.py` and invokes it asynchronously using `workflow.ainvoke()` with the prepared input state and configuration.
-   **Input and Output Handling:**
    -   The initial state for the workflow is constructed from the `ClassifierInput` (email message, subject, ID).
    -   It returns the final `OverallState` object after the workflow has completed. This state object contains all intermediate results from each agent, the final composed response, and any accumulated errors.
-   **Result Processing and Validation:** It includes logic to handle different potential return types from the LangGraph invocation (e.g., dictionary or `OverallState` instance) and ensures the final output is a validated `OverallState` model.
-   **Logging:** Incorporates informative logging at various stages of setup and execution, aiding in monitoring and debugging the workflow.

Architecturally, `run.py` acts as the operational launcher for the Hermes system. It handles necessary prerequisites like vector store initialization and then delegates the complex orchestration of agent interactions to the LangGraph `workflow` defined in `graph.py`. By abstracting the execution details, it provides a clean and straightforward interface to start processing a customer email. Its handling of configuration and state ensures that all parts of the system operate consistently and have access to necessary data.

[Link to source file](../../../../src/hermes/agents/workflow/run.py) 