# Summary of src/hermes/agents/workflow/run_workflow.py

**File Link:** [`src/hermes/agents/workflow/run_workflow.py`](/src/hermes/agents/workflow/run_workflow.py)

This file contains the `run_workflow` asynchronous function, which serves as the main entry point for initiating and executing the Hermes agent workflow. Its primary responsibilities include initializing the global `VectorStore` instance, preparing the necessary configuration (`RunnableConfig`) for the LangGraph workflow based on the provided `HermesConfig`, invoking the `workflow` graph with the initial input state (`ClassifierInput`), and returning the final `OverallState` after the graph execution completes.

Architecturally, this file is the operational core that orchestrates the agent interactions defined by the workflow graph. It abstracts the details of workflow execution and configuration, providing a simple function call to start the entire email processing sequence. The initialization of the `VectorStore` here ensures that the knowledge base is ready before any agent that might require it begins processing.

**Purpose and Responsibilities:**

-   **Workflow Execution:** The main function `run_workflow` takes the initial email input (`ClassifierInput`) and the system configuration (`HermesConfig`). It prepares the necessary configuration for the LangGraph and invokes the compiled `workflow` (imported from `graph.py`).
-   **Vector Store Initialization:** It ensures the singleton `VectorStore` is initialized using the provided configuration before starting the workflow, as the vector store is likely used by one or more agents during the process.
-   **Input and Output Handling:** It accepts the initial `ClassifierInput` and returns the final `OverallState` after the workflow has completed, containing all intermediate results and the final output.
-   **Entry Point:** This file serves as the high-level interface for starting an email processing task within the Hermes system.

In summary, `run_workflow.py` is responsible for setting up the environment (like initializing the vector store) and triggering the execution of the main agent workflow, handling the initial input and returning the final aggregated state. 