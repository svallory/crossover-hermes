# Summary of src/hermes/config.py

This file, `config.py`, defines the `HermesConfig` Pydantic model, which serves as the centralized configuration hub for the Hermes application. It consolidates all application-level settings, sourcing them from environment variables with sensible defaults. This module also includes logic to load `.env` files and configure LangSmith tracing if enabled.

Key components and responsibilities:
-   **`load_app_env_vars()` function**:
    -   **Purpose**: Loads environment variables from a `.env` file located in the current or parent directories.
    -   **LangSmith Tracing**: Checks the `LANGSMITH_TRACING` environment variable. If true, it sets `LANGCHAIN_TRACING_V2` to `"true"` and ensures other `LANGSMITH_*` variables (like `API_KEY`, `ENDPOINT`, `PROJECT`) are synchronized with their `LANGCHAIN_*` counterparts. This function is called at the module level to ensure environment variables are loaded upon import of `config.py`.

-   **Default Configuration Values**: Defines various default constants for LLM providers, model names, API URLs, Google Sheet IDs, and vector store paths (e.g., `DEFAULT_LLM_PROVIDER`, `DEFAULT_OPENAI_STRONG_MODEL`, `DEFAULT_INPUT_SPREADSHEET_ID`).

-   **`HermesConfig(BaseModel)` Pydantic Model**:
    -   **Purpose**: The core class for managing all application configurations. It uses Pydantic for data validation and type hinting, sourcing values from environment variables or falling back to predefined defaults.
    -   **Key Fields**:
        -   `promotion_specs` (List[`PromotionSpec`]): A list of promotion rules, defaulting to an empty list.
        -   `llm_provider` (Literal["OpenAI", "Gemini"]): The primary LLM provider to use, defaults to `DEFAULT_LLM_PROVIDER`.
        -   `llm_api_key` (Optional[str]): API key for the selected `llm_provider`.
        -   `llm_base_url` (Optional[str]): Base URL for the selected `llm_provider` (if applicable).
        -   `llm_strong_model_name`, `llm_weak_model_name` (Optional[str]): Specific model names for "strong" and "weak" capabilities for the selected `llm_provider`.
        -   `llm_model_name` (Optional[str]): A general model name, often defaulting to the strong model if not set (for backward compatibility).
        -   `embedding_model_name` (str): Name of the embedding model to use (e.g., for vector store).
        -   `openai_api_key` (Optional[str]), `openai_base_url` (str): Specific OpenAI API key and base URL.
        -   `vector_store_path` (str): Filesystem path for the persistent vector store (e.g., ChromaDB).
        -   `chroma_collection_name` (str): Name of the collection within ChromaDB.
        -   `input_spreadsheet_id` (str): Google Spreadsheet ID for input data.
        -   `output_spreadsheet_id` (Optional[str]): Google Spreadsheet ID for output data.
        -   `output_spreadsheet_name` (str): Default name for the output spreadsheet if created.
    -   **`@model_validator(mode="after") set_provider_specific_defaults(self) -> Self`**:
        -   A Pydantic model validator that runs after initial model creation.
        -   **Logic**: Based on the chosen `llm_provider` ("OpenAI" or "Gemini"):
            -   It sets the appropriate `llm_api_key`, `llm_base_url` (for OpenAI), `llm_strong_model_name`, and `llm_weak_model_name` by first checking environment variables specific to that provider (e.g., `OPENAI_API_KEY`, `GEMINI_STRONG_MODEL`) and then falling back to the module-level default constants if the environment variables are not set.
            -   It also sets `llm_model_name` for backward compatibility, typically defaulting to the strong model name for the provider.
            -   Ensures that API key fields are `None` if they are loaded as empty strings.
    -   **`as_runnable_config(self) -> RunnableConfig`**: Converts the `HermesConfig` instance into a dictionary format compatible with LangChain's `RunnableConfig`, specifically nesting it under `{"configurable": {"hermes_config": self}}`. This allows the configuration to be easily passed into and used by LangChain runnables and LangGraph components.
    -   **`@classmethod from_runnable_config(cls, config: RunnableConfig | None = None) -> Self`**: 
        -   A class method to reconstruct a `HermesConfig` instance from a LangChain `RunnableConfig` object (or a dictionary that might represent it).
        -   This allows LangGraph components or other parts of a LangChain pipeline to easily retrieve and use the structured `HermesConfig` from the broader runnable configuration context.
        -   It handles cases where the config might be `None`, already a `HermesConfig` instance, or a dictionary of parameters.

Architecturally, `config.py` centralizes all application settings into a single, type-safe, and validated Pydantic model (`HermesConfig`). This approach significantly improves maintainability and reduces the risk of configuration errors. By loading settings from environment variables (optionally sourced from `.env` files) with clear defaults, it allows for flexible deployment across different environments. The integration with LangSmith tracing and LangChain's `RunnableConfig` makes it well-suited for use within the LangChain ecosystem, ensuring that configurations are consistently managed and accessible throughout the Hermes agentic workflow.

[Link to source file](../../../src/hermes/config.py) 