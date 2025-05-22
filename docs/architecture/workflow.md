# Hermes Workflow

This document details the workflow system used in Hermes to orchestrate agent interactions.

## Overview

Hermes uses LangGraph's `StateGraph` to define and manage the workflow between agents. The workflow is responsible for:

1. Coordinating agent execution in the proper sequence
2. Managing state transitions and conditional branching
3. Aggregating and storing the outputs from each agent
4. Handling errors that occur during processing

## Key Components

### OverallState

The `OverallState` model (in `states.py`) serves as the central data structure for the workflow. It:

- Contains the original email details (ID, subject, message)
- Stores outputs from each agent as they complete processing
- Tracks errors encountered during processing

This design allows subsequent agents to access results from preceding ones and facilitates the flow of information.

### Workflow Graph

The workflow graph (in `graph.py`) defines the nodes and edges of the agent workflow:

1. **Nodes**:
   - `analyze_email` - Classifier agent
   - `resolve_product_mentions` - Stockkeeper agent
   - `process_order` - Fulfiller agent (conditional)
   - `respond_to_inquiry` - Advisor agent (conditional)
   - `compose_response` - Composer agent

2. **Edges and Routing**:
   - All emails start with Classifier → Stockkeeper
   - After Stockkeeper, the `route_resolver_result` function determines:
     - If email has inquiry segments: route to Advisor
     - If email has order segments: route to Fulfiller
     - If both: route to both in parallel
   - All paths converge at the Composer node for final response generation

3. **Wrapper Functions**:
   - Each agent has a wrapper function to adapt the `OverallState` to the agent's expected input format
   - For example, `analyze_email_node` extracts the relevant information from `OverallState` to pass to `analyze_email`

### Workflow Execution

The workflow is executed through the `run_workflow` function (in `workflow.py` or `run_workflow.py`), which:

1. Initializes the vector store singleton
2. Prepares the LangGraph configuration based on `HermesConfig`
3. Invokes the workflow with the initial email input
4. Returns the final `OverallState` containing all intermediate and final outputs

## Error Handling

The workflow includes error tracking mechanisms:

- Each agent node can return an error as part of its output
- Errors are stored in the `errors` dictionary of `OverallState`
- This allows the workflow to continue even if one agent encounters an error
- The Composer agent can generate appropriate fallback responses for error cases

## Diagram

The workflow can be visualized as follows:

```
Start
  │
  ▼
Classifier (analyze_email)
  │
  ▼
Stockkeeper (resolve_product_mentions)
  │
  ├─────────┬─────────┐
  │         │         │
  ▼         ▼         ▼
Advisor    Fulfiller  Both
(inquiry)  (order)    (parallel)
  │         │         │
  │         │         │
  └─────────┴─────────┘
            │
            ▼
Composer (compose_response)
            │
            ▼
           End
``` 