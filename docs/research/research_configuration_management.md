# Research: Configuration Management in LangGraph

## Question
Should we use `RunnableConfig` from `langchain_core.runnables` for the configuration? What parameters should be configurable vs. hardcoded? How should we structure the configuration for different components?

## Research Notes

### Configuration in data-enrichment Example

The data-enrichment example uses a dedicated Configuration class with RunnableConfig integration:

```python
class Configuration(BaseModel):
    """Configuration for the graph."""

    prompt: str = MAIN_PROMPT
    """The prompt to use for the enrichment agent."""

    max_loops: int = 5
    """The maximum number of loops to run."""

    @classmethod
    def from_runnable_config(
        cls, runnable_config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Get configuration from runnable config."""
        if runnable_config is None:
            return cls()
        return cls(
            **{
                k: v
                for k, v in runnable_config.get("configurable", {}).items()
                if k in cls.__fields__
            }
        )
```

Key features:
- Uses Pydantic `BaseModel` for structural validation
- Includes default values for parameters
- Has a `from_runnable_config` method to extract values from `RunnableConfig`
- Used in node functions via `Configuration.from_runnable_config(config)`

The configuration is then referenced in nodes:

```python
def route_after_checker(
    state: State, config: RunnableConfig
) -> Literal["__end__", "call_agent_model"]:
    """Schedule the next node after the checker's evaluation."""
    configurable = Configuration.from_runnable_config(config)
    # Use configuration to make decisions
    if state.loop_step < configurable.max_loops:
        # Logic using config values
        ...
```

### RunnableConfig Usage

The `RunnableConfig` from `langchain_core.runnables` has several aspects:

1. **Standard fields**: Contains standard fields like `callbacks`, `tags`, etc.
2. **Configurable field**: Has a special `configurable` field that can be used for custom configuration
3. **Passing to graph**: Can be passed to the graph during invocation
4. **Accessing in nodes**: Available as an optional second argument to node functions

Using `configurable` field:
```python
config = {"configurable": {"max_loops": 10, "prompt": custom_prompt}}
result = graph.invoke(input_data, config=config)
```

### Best Practices for Configuration

From reviewing various examples and documentation:

1. **Use a dedicated Configuration class**:
   - Creates a clear interface for what can be configured
   - Enables validation through Pydantic
   - Centralizes configuration logic

2. **Extract from RunnableConfig**:
   - Use a helper method to extract configuration from RunnableConfig
   - Makes it easier to access in node functions

3. **Default Values**:
   - Provide sensible defaults for all configuration parameters
   - Ensures the application works even without explicit configuration

4. **Configuration Granularity**:
   - Have both global configuration and component-specific configuration
   - For multi-agent systems, each agent can have its own configuration section

5. **Dynamic vs. Static Configuration**:
   - Some parameters should be configurable at runtime
   - Others might be better as environment variables or constants

### Parameters to Consider for Configuration

Based on the Hermes project needs:

1. **Model Configuration**:
   - Model providers and model names for each agent
   - Temperature and other model parameters
   - API keys (though better as environment variables)

2. **Agent Behavior**:
   - System prompts for each agent
   - Maximum loops/recursion limits
   - Thresholds for confidence scores

3. **Tool Configuration**:
   - Database connection parameters
   - Vector store settings
   - Email templates and formatting options

4. **Runtime Behaviors**:
   - Debug flags
   - Logging levels
   - Performance monitoring options

5. **Graph Structure Parameters**:
   - Timeouts
   - Retry policies
   - Human-in-the-loop settings

## Decision
We should use `RunnableConfig` from `langchain_core.runnables` for configuration, along with a structured hierarchy of Pydantic `BaseModel` classes for both global and agent-specific configurations. We'll implement a helper method similar to the `from_runnable_config` pattern in the data-enrichment example to extract configuration values.

## Justification
This approach provides several advantages for our Hermes implementation:

1. **Structured Type Validation**: Using Pydantic models ensures that configuration values are properly validated at runtime, preventing unexpected behavior from misconfiguration. This is particularly important for our multi-agent system where configuration errors could propagate.

2. **Hierarchical Configuration**: Our application needs both global settings and agent-specific settings. A structured hierarchy of configuration classes allows us to organize these logically while maintaining type safety. For example:
   ```python
   class HermesConfig(BaseModel):
       max_retries: int = 3
       classifier_config: ClassifierConfig
       fulfiller_config: FulfillerConfig
       response_generator_config: ResponseGeneratorConfig
   ```

3. **Runtime Flexibility**: The `RunnableConfig` pattern allows us to modify behavior at runtime without redeploying code. This is valuable for:
   - Testing different LLM temperatures or models
   - Adjusting confidence thresholds
   - Enabling/disabling debug features

4. **Centralized Defaults**: By defining sensible defaults in our configuration classes, we ensure that the system works out-of-the-box while still allowing customization. This makes both development and deployment simpler.

5. **Clear Documentation**: A structured configuration approach with classes and docstrings serves as self-documenting code, making it easier for others to understand what can be configured.

6. **Separation of Concerns**: This pattern cleanly separates configuration management from core logic, making the code more maintainable and testable.

For our Hermes implementation, we'll make the following configurable at runtime:
- Model settings (provider, model name, temperature) for each agent
- Agent-specific behavior parameters (confidence thresholds, max iterations)
- RAG vector store configuration (model, chunk size, etc.)
- Logging and debugging flags

Environment-specific settings like API keys and resource paths should be handled through environment variables rather than `RunnableConfig` for security and separation of deployment concerns. 