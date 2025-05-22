# Hermes Workflow Implementation

Hermes uses LangGraph, a library built on top of LangChain, to implement a directed workflow for processing customer emails. This document details the implementation of this workflow.

!toc(minlevel=1 maxlevel=3)

## Workflow Architecture

### StateGraph

The core of the workflow is a `StateGraph` object that manages the flow of data between agents:

```python
# Build the graph
graph_builder = StateGraph(OverallState, input=ClassifierInput, config_schema=HermesConfig)

# Add nodes with the agent functions
graph_builder.add_node(Nodes.CLASSIFIER, analyze_email_node)
graph_builder.add_node(Nodes.STOCKKEEPER, resolve_products_node)
graph_builder.add_node(Nodes.FULFILLER, process_order_node)
graph_builder.add_node(Nodes.ADVISOR, respond_to_inquiry)
graph_builder.add_node(Nodes.COMPOSER, compose_response)

# Add edges
graph_builder.add_edge(START, Nodes.CLASSIFIER)
graph_builder.add_edge(Nodes.CLASSIFIER, Nodes.STOCKKEEPER)

# Add conditional routing
graph_builder.add_conditional_edges(
    Nodes.STOCKKEEPER,
    route_resolver_result,
    [Nodes.FULFILLER, Nodes.ADVISOR]
)
graph_builder.add_edge(Nodes.FULFILLER, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.ADVISOR, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.COMPOSER, END)

# Compile the workflow
workflow = graph_builder.compile()
```

### Conditional Routing

The workflow uses conditional routing to direct processing based on email intent:

```python
def route_resolver_result(
    state: OverallState,
) -> list[Hashable] | Hashable:
    """Route after product resolution based on email intents."""
    classifier = state.classifier

    if classifier is not None:
        analysis = classifier.email_analysis

        return (
            # If primary intent is inquiry, go to advisor only
            Nodes.ADVISOR
            if analysis.primary_intent == "product inquiry"
            # If it has both order and inquiry, process both
            else [Nodes.FULFILLER, Nodes.ADVISOR]
            if analysis.has_inquiry()
            # If order only, go to fulfiller only
            else Nodes.FULFILLER
        )

    return END
```

## State Management

### OverallState

The workflow uses an `OverallState` model to track progress:

```python
class OverallState(BaseModel):
    """Overall state that can contain any combination of analysis, processing, and response."""

    email_id: str
    subject: str | None = None
    message: str

    # Agent outputs
    classifier: ClassifierOutput | None = None
    stockkeeper: StockkeeperOutput | None = None
    fulfiller: FulfillerOutput | None = None
    advisor: AdvisorOutput | None = None
    composer: ComposerOutput | None = None
    
    # Error tracking
    errors: Annotated[dict[Agents, Error], merge_errors] = Field(default_factory=dict)
```

### State Transformations

As the workflow progresses, each agent adds its output to the state:

1. **Classifier** analyzes the email and adds `classifier` to the state
2. **Stockkeeper** resolves products and adds `stockkeeper` to the state
3. **Fulfiller** processes orders and adds `fulfiller` to the state 
4. **Advisor** answers inquiries and adds `advisor` to the state
5. **Composer** creates a response and adds `composer` to the state

## Execution

The workflow is executed using the `run_workflow` function:

```python
async def run_workflow(
    input_state: ClassifierInput,
    hermes_config: HermesConfig,
) -> OverallState:
    """Run the workflow with the given input state and configuration."""
    
    # Initialize the vector store
    VectorStore(hermes_config=hermes_config)

    # Prepare the runnable config
    config: dict[str, dict[str, Any]] = {
        "configurable": {
            "hermes_config": hermes_config,
        }
    }
    runnable_config: RunnableConfig = config

    # Run the workflow
    result = await workflow.ainvoke(input_state, config=runnable_config)
    
    # Convert the result to an OverallState
    if isinstance(result, dict):
        final_state = OverallState.model_validate(result)
    else:
        final_state = result

    return final_state
```

## Configuration

The workflow accepts a `HermesConfig` object that is passed to all agents:

1. The config is converted to a RunnableConfig dictionary
2. This config is passed to the workflow during execution
3. Each agent extracts the config using `HermesConfig.from_runnable_config()`

## Error Handling

The workflow includes comprehensive error handling:

1. Each agent function is wrapped to catch exceptions
2. Errors are added to the `errors` dictionary in `OverallState`
3. The workflow continues even if one agent fails
4. A utility function `create_node_response` standardizes error reporting

## Parallel Processing

The conditional routing allows multiple agents to run in parallel branches:

1. For emails with both order and inquiry components, both Fulfiller and Advisor process simultaneously
2. Their results are merged back in the state for the Composer

## Tracing and Monitoring

The workflow supports tracing through LangChain's tracing mechanisms:

1. Agents are decorated with `@traceable` for monitoring
2. The workflow is registered in `langgraph.json` for easy visualization

## Output Processing

After workflow completion, the main application processes the workflow result:

1. Extract email classification
2. Extract order status
3. Extract response text
4. Format output for CSV or Google Sheets

This structured approach ensures a maintainable, flexible system that can be easily extended with new agents or modified routing logic as requirements evolve. 