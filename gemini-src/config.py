""" {cell}
## Configuration

This module defines the configuration for the Hermes system using Pydantic,
ensuring that all settings are type-checked and validated at runtime.
The `HermesConfig` class centralizes all parameters, including LLM settings,
RAG parameters, and vector store configurations.

**Key Design Considerations:**
- **Pydantic BaseModel**: Provides strong typing, validation, and clear structure for configuration.
- **Centralization**: All configurable parameters are in one place for ease of management.
- **Default Values**: Sensible defaults are provided, aligning with common best practices for LLM applications.
- **LangChain Compatibility**: The `from_runnable_config` classmethod allows seamless integration with LangChain's `RunnableConfig`.
- **Extensibility**: The structure allows for easy addition of new configuration parameters as the system evolves.

This approach ensures that the application is robust, maintainable, and easy to configure for different environments or experimental setups.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# Import for RunnableConfig if direct type hint is needed, otherwise use 'Any' or forward reference.
# from langchain_core.runnables import RunnableConfig # Example if needed

class LLMConfig(BaseModel):
    """Configuration for the Language Model."""
    provider: str = Field(default="openai", description="The LLM provider (e.g., 'openai', 'anthropic').")
    model_name: str = Field(default="gpt-4o", description="The specific model name to use (e.g., 'gpt-4o', 'claude-3-opus-20240229').")
    temperature: float = Field(default=0.0, description="Sampling temperature for the LLM. Lower values make output more deterministic.", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, description="Maximum number_of_tokens to generate.")
    # It's important to use the custom base_url and api_key if provided by the assignment
    base_url: Optional[str] = Field(default='https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/', description="Custom base URL for the OpenAI API-compatible endpoint.")
    api_key: Optional[str] = Field(default="<YOUR_OPENAI_API_KEY>", description="API key for the LLM provider. Use one provided by Crossover or your own.")

class VectorStoreConfig(BaseModel):
    """Configuration for the Vector Store."""
    provider: str = Field(default="chroma", description="The vector store provider (e.g., 'chroma', 'faiss').")
    persist_directory: Optional[str] = Field(default=".db/chroma_hermes_vs", description="Directory to persist ChromaDB data. If None, it's in-memory.")
    collection_name: str = Field(default="hermes_product_catalog", description="Name of the collection in the vector store.")
    embedding_model_provider: str = Field(default="openai", description="Provider for embedding model, e.g., 'openai'.")
    embedding_model_name: str = Field(default="text-embedding-ada-002", description="Name of the embedding model to use.")
    # Add batch size for embedding creation as per reference-solution-spec.md
    embedding_batch_size: int = Field(default=100, description="Batch size for creating embeddings.")


class RAGConfig(BaseModel):
    """Configuration for Retrieval-Augmented Generation."""
    retrieval_k: int = Field(default=5, description="Number of documents to retrieve for RAG.")
    # category_filter_enabled: bool = Field(default=True, description="Enable category-based pre-filtering for RAG.") # As per reference-solution-spec.md
    # price_filter_enabled: bool = Field(default=False, description="Enable price-range filtering for RAG.") # As per reference-solution-spec.md

class HermesConfig(BaseModel):
    """Main configuration for the Hermes email processing system."""
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    
    # General application settings
    max_concurrent_requests: int = Field(default=5, description="Maximum number of concurrent email processing requests.")
    debug_mode: bool = Field(default=False, description="Enable debug logging and verbose output.")

    @classmethod
    def from_runnable_config(cls, runnable_config: Optional[Dict[str, Any]] = None) -> "HermesConfig":
        """
        Creates a HermesConfig instance from a LangChain RunnableConfig (or a dictionary).
        This allows passing configuration dynamically at runtime if needed.
        
        For this reference solution, we will mostly rely on the default instantiated config,
        but this method provides compatibility.
        """
        if runnable_config and "hermes_config" in runnable_config.get("configurable", {}):
            config_dict = runnable_config["configurable"]["hermes_config"]
            if isinstance(config_dict, cls): # If it's already a HermesConfig instance
                return config_dict
            if isinstance(config_dict, dict):
                 # Attempt to parse if it's a dictionary representation
                try:
                    return cls.model_validate(config_dict)
                except Exception: # Fallback to default if parsing fails
                    # Consider logging a warning here
                    pass # Fall through to default
        return cls() # Return a default config if not found or parsing failed

""" {cell}
### Example Usage (Conceptual)

This section is for illustrative purposes and would typically not be part of the `config.py` file itself,
but rather how you might use it elsewhere in the application.

```python
# from src.config import HermesConfig # Assuming this is run from outside src

# Create a default configuration instance
# default_config = HermesConfig()
# print(f"Default LLM Model: {default_config.llm.model_name}")
# print(f"Vector Store Persist Directory: {default_config.vector_store.persist_directory}")

# To use with LangChain's config system (conceptual):
# from langchain_core.runnables import RunnableLambda, RunnableConfig
#
# def my_configurable_runnable(input_data: str, config: RunnableConfig):
#     hermes_conf = HermesConfig.from_runnable_config(config)
#     # Now use hermes_conf.llm.model_name, etc.
#     print(f"Using LLM: {hermes_conf.llm.model_name} with temp {hermes_conf.llm.temperature}")
#     return f"Processed {input_data} with {hermes_conf.llm.model_name}"
#
# chain = RunnableLambda(my_configurable_runnable)
#
# # Invoke with default config
# # chain.invoke("test")
#
# # Invoke with a custom config
# custom_llm_settings = LLMConfig(model_name="gpt-3.5-turbo", temperature=0.5)
# custom_hermes_config = HermesConfig(llm=custom_llm_settings)
#
# result = chain.invoke(
#     "test_custom",
#     config={"configurable": {"hermes_config": custom_hermes_config.model_dump()}}
# )
# print(result)

# Setting API Key
# Note: The API key should ideally be set via environment variables or a secure secret management system.
# For this assignment, you might set it directly if you are using the provided temporary key.
# Ensure the provided API key is used with the custom base_url.
#
# default_config = HermesConfig()
# if default_config.llm.api_key == "<YOUR_OPENAI_API_KEY>" or not default_config.llm.api_key:
#     print("WARNING: OpenAI API key is not configured in src/config.py or is set to the placeholder.")
#     print("Please update it with the key provided by Crossover or your own key.")
#     # Example: default_config.llm.api_key = "sk-yourActualKey..." (NOT RECOMMENDED FOR PRODUCTION)

# Using the provided OpenAI API key with the custom base URL:
# assignment_config = HermesConfig(
#     llm=LLMConfig(
#         base_url='https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/',
#         api_key='<USE_PROVIDED_API_KEY_HERE_OR_YOUR_OWN>' # Replace with actual key
#     )
# )
# if assignment_config.llm.api_key == '<USE_PROVIDED_API_KEY_HERE_OR_YOUR_OWN>':
#      print("INFO: Remember to replace '<USE_PROVIDED_API_KEY_HERE_OR_YOUR_OWN>' in the example with your actual API key.")

```
This configuration setup provides a solid foundation for managing the application's settings
in a structured and maintainable way.
""" 