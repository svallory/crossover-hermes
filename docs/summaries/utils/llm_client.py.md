# Summary of src/hermes/utils/llm_client.py

This module, `llm_client.py`, located within the `hermes.utils` package, provides a centralized utility function for creating and configuring LangChain Large Language Model (LLM) clients. Its primary role is to abstract the instantiation details of different LLM providers (OpenAI, Google Generative AI) and allow other parts of the Hermes system (like the agents) to easily obtain an LLM client based on the application's global configuration (`HermesConfig`).

Key components and responsibilities:
-   **`get_llm_client(config: HermesConfig, model_strength: Literal["weak", "strong"], temperature: float = 0.0) -> BaseChatModel`**:
    -   **Purpose**: This is the main function of the module. It initializes and returns a LangChain chat model instance (`BaseChatModel` or a more specific type like `ChatOpenAI` or `ChatGoogleGenerativeAI`).
    -   **Parameters**:
        -   `config` (`HermesConfig`): An instance of the Hermes application's configuration object, which contains settings like API keys, model names, and the preferred LLM provider.
        -   `model_strength` (Literal["weak", "strong"]): Specifies the desired capability or size of the model to be used. The `HermesConfig` is expected to map these abstract strength levels to concrete model names for the selected provider (e.g., "weak" might map to "gpt-3.5-turbo" and "strong" to "gpt-4" for OpenAI).
        -   `temperature` (float, default: 0.0): Controls the randomness/creativity of the LLM's output. A value of 0.0 typically results in more deterministic and focused outputs.
    -   **Logic**:
        1.  Determines the LLM provider from `config.llm_provider` (e.g., "openai" or "google").
        2.  Based on the provider:
            -   **OpenAI**: 
                -   Retrieves the appropriate OpenAI model name from `config.openai_weak_model_name` or `config.openai_strong_model_name` based on `model_strength`.
                -   Validates that `config.openai_api_key` and the chosen model name are set, raising a `ValueError` if not.
                -   Instantiates and returns a `ChatOpenAI` client with the specified model name, API key, and temperature.
            -   **Google Generative AI**: 
                -   Retrieves the appropriate Google model name from `config.google_weak_model_name` or `config.google_strong_model_name`.
                -   Validates that `config.google_api_key` and the model name are set, raising a `ValueError` if not.
                -   Instantiates and returns a `ChatGoogleGenerativeAI` client with the model name, API key (`google_api_key`), and temperature. It also sets `convert_system_message_to_human=True` which can be important for how system prompts are handled by Google models.
        3.  Raises a `ValueError` if the `config.llm_provider` is not recognized (neither "openai" nor "google").
    -   **Return Value**: An instance of a LangChain chat model, configured and ready to be used by an agent.

Architecturally, `llm_client.py` promotes a clean separation of concerns by decoupling agent logic from the specifics of LLM client instantiation. It centralizes LLM configuration, making it easy to switch between providers or update model names across the application by modifying only the `HermesConfig` and this utility. The use of abstract `model_strength` allows agents to request models based on their needs (e.g., a simple classification task might use a "weak" model for cost/speed, while complex reasoning might require a "strong" model) without being hardcoded to specific model identifiers. The validation checks ensure that the application fails fast if critical configuration (like API keys) is missing, improving debuggability.

[Link to source file](../../../src/hermes/utils/llm_client.py) 