# Hermes LLM Integration

Hermes is designed to work with multiple LLM providers and models, with a flexible configuration system that allows easy switching between providers. This document details how LLMs are integrated into the system.

## LLM Providers

Hermes supports two primary LLM providers:

1. **OpenAI** (`llm_provider="OpenAI"`)
   - Strong model: `gpt-4.1` (default)
   - Weak model: `gpt-4o-mini` (default)

2. **Google Gemini** (`llm_provider="Gemini"`)
   - Strong model: `gemini-2.5-flash-preview-04-17` (default)
   - Weak model: `gemini-1.5-flash` (default)

## Configuration System

The `HermesConfig` class centralizes all LLM configuration:

```python
class HermesConfig(BaseModel):
    llm_provider: Literal["OpenAI", "Gemini"] = Field(...)
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    
    # Model configurations
    llm_strong_model_name: str | None = None
    llm_weak_model_name: str | None = None
    llm_model_name: str | None = None  # For backward compatibility
    
    # Embedding model for vector search
    embedding_model_name: str = Field(...)
    
    # Additional configuration omitted for brevity
```

## LLM Client Factory

The `get_llm_client` function creates appropriate LLM clients based on configuration:

```python
def get_llm_client(
    config: HermesConfig,
    model_strength: Literal["weak", "strong"] | None = "weak",
    temperature: float = 0.0,
) -> BaseChatModel:
    """Initializes and returns an LLM client based on the provided configuration."""
    
    # Determine which model to use based on model_strength
    model_name = None
    if model_strength == "strong":
        model_name = config.llm_strong_model_name
    elif model_strength == "weak":
        model_name = config.llm_weak_model_name
    else:
        model_name = config.llm_model_name
        
    # Create the appropriate client based on provider
    if config.llm_provider == "OpenAI":
        return ChatOpenAI(
            model=model_name,
            api_key=SecretStr(config.llm_api_key),
            base_url=config.llm_base_url,
            temperature=temperature,
        )
    elif config.llm_provider == "Gemini":
        return ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=config.llm_api_key, 
            temperature=temperature
        )
```

## Tiered Model Strategy

Hermes employs a tiered approach to model usage:

1. **Strong Models**: Used for tasks requiring deep understanding and complex reasoning:
   - Final response composition
   - Detailed inquiry responses
   - Complex processing tasks

2. **Weak Models**: Used for simpler, more structured tasks:
   - Initial email classification
   - Basic information extraction
   - Structured parsing

This approach optimizes for both performance and cost, using more powerful (and typically more expensive) models only where necessary.

## Integration in Agents

Each agent specifies its model strength requirement when creating a client:

```python
# Example from the Email Analyzer agent
llm = get_llm_client(config=hermes_config, model_strength="weak", temperature=0.0)

# Example from the Response Composer agent
llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.7)
```

## Prompt Handling

Prompts are centralized and loaded from template files:

```python
# Example prompt loading
analyzer_prompt = get_prompt("classifier")
analysis_chain = analyzer_prompt | llm
```

## Vector Embeddings

For RAG capabilities, Hermes uses embedding models:

1. Default embedding model: `text-embedding-3-small`
2. The embedding model powers the vector store used for semantic search

## Configuration Propagation

The LLM configuration flows through the system:

1. `HermesConfig` is created at application startup
2. Config is converted to a `RunnableConfig` for LangGraph
3. Agents extract the config using `HermesConfig.from_runnable_config()`
4. Each agent creates its own LLM client with the appropriate strength

## Environment Variables

LLM configuration can be set via environment variables:

```
# Provider selection
LLM_PROVIDER=OpenAI

# API keys
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here

# Model selection
OPENAI_STRONG_MODEL=gpt-4.1
OPENAI_WEAK_MODEL=gpt-4o-mini
GEMINI_STRONG_MODEL=gemini-2.5-flash-preview-04-17
GEMINI_WEAK_MODEL=gemini-1.5-flash

# Embedding model
EMBEDDING_MODEL=text-embedding-3-small
```

## Advantages of This Approach

1. **Provider Flexibility**: Easy switching between OpenAI and Google models
2. **Cost Optimization**: Using weaker models for simpler tasks reduces costs
3. **Performance Optimization**: Using stronger models for complex tasks improves quality
4. **Configuration Centralization**: All LLM settings in one place
5. **Environment Override**: Easy configuration through environment variables

This flexible LLM integration allows Hermes to adapt to changing requirements and take advantage of improvements in model capabilities over time. 