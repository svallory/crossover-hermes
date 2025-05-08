# Research: State Management in LangGraph

## Question
Should we use dataclasses with annotated fields like in data-enrichment/state.py or TypedDict (used in agent-flow.md)? How should we handle state transitions and reducers for complex states?

## Research Notes

### State Management in data-enrichment Example
The data-enrichment example uses dataclasses for state management with the following pattern:

```python
@dataclass(kw_only=True)
class InputState:
    """Input state defines the interface between the graph and the user (external API)."""
    topic: str
    extraction_schema: dict[str, Any]
    info: Optional[dict[str, Any]] = field(default=None)

@dataclass(kw_only=True)
class State(InputState):
    """A graph's State defines the structure of data to be passed between nodes"""
    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)
    loop_step: Annotated[int, operator.add] = field(default=0)

@dataclass(kw_only=True)
class OutputState:
    """The response object for the end user."""
    info: dict[str, Any]
```

Key features:
- Uses Python's dataclasses for clear typing
- Uses annotations to define reducers (e.g., `add_messages` and `operator.add`)
- Separates input, internal, and output states
- Inheritance is used to extend the input state

### State Management in agent-flow.md
The agent-flow.md document uses TypedDict for state management:

```python
class HermesState(TypedDict):
    email_id: str
    email_subject: str
    email_body: str
    email_analysis: dict
    order_result: Optional[dict]
    inquiry_result: Optional[dict]
    final_response: str
```

Key features:
- Uses TypedDict for a dictionary-like state structure
- More lightweight than dataclasses
- No built-in reducer mechanisms
- All state fields in a single class

### LangGraph State Management Features

#### Reducers in LangGraph
According to the LangGraph documentation, reducers are key to understanding how updates from nodes are applied to the `State`. Each key in the `State` has its own independent reducer function. If no reducer function is explicitly specified then it is assumed that all updates to that key should override it.

For TypedDict, reducers can be specified using the `Annotated` type:

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class State(TypedDict):
    foo: int
    bar: Annotated[list[str], add]
```

In this example, updates to the `bar` key will be combined with the existing value using the `add` operator rather than simply overwriting it.

#### MessagesState in LangGraph
LangGraph provides a predefined `MessagesState` that includes a single `messages` key with the `add_messages` reducer. This can be extended to include additional fields:

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    documents: list[str]
```

#### State Schemas in LangGraph JS
LangGraph JS provides the `Annotation` function for defining graph state, which is the recommended approach for new `StateGraph` graphs:

```javascript
const GraphAnnotation = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (currentState, updateValue) => currentState.concat(updateValue),
    default: () => [],
  })
});
```

#### Multiple State Schemas
LangGraph supports defining different state schemas for different parts of the graph. This allows internal nodes to pass information that is not required in the graph's input/output. It also supports defining explicit input and output schemas that are subsets of the internal schema.

#### State Transitions
State transitions in LangGraph can be managed using:
1. **Normal Edges**: Direct transitions from one node to the next
2. **Conditional Edges**: Routes based on the output of a routing function
3. **Command**: Combines state updates and routing in a single function

For complex state transitions, the `Command` class is particularly useful as it allows for both updating state and controlling flow in a single function.

## Decision
For the Hermes project, we will use **dataclasses with annotated fields** similar to the data-enrichment example, with some modifications to better suit our multi-agent architecture.

## Justification
After reviewing both approaches and the LangGraph documentation, dataclasses with annotated fields offer several advantages for our use case:

1. **Type Safety**: Dataclasses provide stronger type checking during development compared to TypedDict, which will help prevent errors in our multi-agent system where state is passed between different specialized agents.

2. **Built-in Reducer Support**: The `Annotated` type combined with dataclasses makes it clearer how state updates are handled, which is crucial for our email processing workflow where we need to accumulate messages and maintain conversation history.

3. **Separation of Concerns**: The pattern of separating InputState, State, and OutputState provides a cleaner interface between our graph and external systems, which aligns well with our supervisor architecture where different agents need access to different parts of the state.

4. **Inheritance and Composability**: Dataclasses allow us to use inheritance to extend state definitions, which supports our modular agent design where different agents may need to extend the base state with agent-specific fields.

5. **Default Values**: Dataclasses make it easier to define default values for state fields, which simplifies the initialization of our graph and reduces the chance of errors from missing fields.

For state transitions, we will use a combination of conditional edges and the `Command` class. Conditional edges will be used for the supervisor agent to route to specialized agents, while the `Command` class will be used by the specialized agents to both update the state and return control to the supervisor.

This approach balances type safety, code clarity, and flexibility, which is essential for our complex email processing workflow with multiple specialized agents. 