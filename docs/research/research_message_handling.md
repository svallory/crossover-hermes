# Research: Message Handling in LangGraph

## Question
Should we use langchain_core.messages (AIMessage, HumanMessage, ToolMessage) as in data-enrichment? How should we handle tool calls and responses in the message history?

## Research Notes

### Message Handling in data-enrichment Example
The data-enrichment example uses langchain_core.messages for message handling:

```python
@dataclass(kw_only=True)
class State(InputState):
    """A graph's State defines the structure of data to be passed between nodes"""
    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)
    loop_step: Annotated[int, operator.add] = field(default=0)
```

Key features:
- Uses `BaseMessage` from langchain_core.messages
- Includes various message types like HumanMessage, AIMessage, ToolMessage, etc.
- Uses the `add_messages` reducer to correctly handle message updates
- Simplifies integration with LangChain components

### Message Types in LangChain

LangChain offers various message types:
- **HumanMessage**: Messages from the user
- **AIMessage**: Responses from the LLM
- **SystemMessage**: Instructions or context for the LLM
- **ToolMessage**: Results from a tool call
- **FunctionMessage**: Legacy version of ToolMessage

These message types help structure the conversation and enable proper handling of different message sources and purposes.

### Tool Calls and Responses

The data-enrichment example shows a standardized way to handle tool calls and responses:

1. **AIMessage with tool_calls**: When the LLM decides to call a tool, it returns an AIMessage with tool_calls
2. **ToolMessage**: After executing a tool, results are returned as ToolMessage with matching tool_call_id 
3. **Error Handling**: The example uses status="error" in ToolMessage for unsatisfactory responses

From the web search, I found:

- **Standardized Representation**: LangChain has standardized tool calls through the AIMessage.tool_calls property which is consistent across different LLM providers
- **Tool Call Structure**: Tool calls include a name, arguments dict, and an optional identifier
- **RemoveMessage**: A special message type for managing chat history in LangGraph that doesn't correspond to any roles
- **Error Handling**: LangGraph provides mechanisms for handling tool calling errors through patterns like:
  - Using status="error" in ToolMessage
  - Removing failed tool call attempts from history using RemoveMessage
  - Fallback strategies for when tool calls fail

### Message Handling Best Practices

From examining multiple sources, these best practices emerge:

1. **Use Standard Message Types**: Use HumanMessage, AIMessage, SystemMessage, ToolMessage from langchain_core.messages
2. **Proper Message Sequences**: Ensure valid message sequences (AIMessage with tool calls should be followed by ToolMessage)
3. **Error Handling**: Implement tool error handling with clear patterns for recovery
4. **Message History Management**:
   - Use add_messages reducer for message accumulation
   - Consider message trimming for long conversations
   - Employ RemoveMessage for cleaning up history when needed

## Decision
We should implement message handling using langchain_core.messages (AIMessage, HumanMessage, ToolMessage, SystemMessage) combined with the add_messages reducer as demonstrated in the data-enrichment example. For tool calls, we'll use the standardized pattern where AIMessages contain tool_calls and ToolMessages return the results with matching tool_call_ids.

## Justification
Using langchain_core.messages with the add_messages reducer provides several significant advantages:

1. **Standardization**: This approach follows LangChain's standardized message format, ensuring compatibility with different LLM providers and making our code more maintainable.

2. **Tool Call Integration**: The tool_calls attribute on AIMessage and ToolMessage pattern works seamlessly with LangChain's tools system, making it easy to implement the tools required for email classification and response generation.

3. **Error Recovery**: The pattern allows for sophisticated error handling, such as detecting failed tool calls and implementing fallback strategies. This is crucial for a robust production system.

4. **Memory Management**: Using add_messages reducer properly handles message IDs and updates, which is essential for implementing features like human-in-the-loop interactions where messages may need to be modified or removed.

5. **Future-Proofing**: This approach aligns with LangChain's architecture and will be more compatible with future updates and features, reducing technical debt. 