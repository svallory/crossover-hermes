# @title get_llm_client
"""
Utility for creating and configuring LangChain LLM clients.
"""
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from .config import HermesConfig

def get_llm_client(config: HermesConfig, temperature: float) -> BaseChatModel:
    """
    Initializes and returns an LLM client based on the provided configuration.

    Args:
        config: The HermesConfig instance containing LLM settings.
        temperature: The specific temperature to use for this LLM client instance.

    Returns:
        An instance of a LangChain chat model (e.g., ChatOpenAI, ChatGoogleGenerativeAI).

    Raises:
        ValueError: If the model name in the config is not recognized or supported,
                    or if the API key is missing when required.
    """
    model_name = config.llm_model_name
    api_key = config.llm_api_key

    if not model_name:
        raise ValueError("LLM model name is not configured in HermesConfig.")

    # More robust model detection based on model name prefixes
    gemini_prefixes = ["gemini-", "google/"]
    openai_prefixes = ["gpt-", "text-davinci-", "openai/"]
    
    is_google_model = any(model_name.startswith(prefix) for prefix in gemini_prefixes)
    is_openai_model = any(model_name.startswith(prefix) for prefix in openai_prefixes)
    
    # Fallback to substring matching only if no prefix match
    if not is_google_model and not is_openai_model:
        model_name_lower = model_name.lower()
        is_google_model = "gemini" in model_name_lower
        is_openai_model = any(substr in model_name_lower for substr in ["gpt", "davinci", "openai"])

    if is_google_model:
        # ChatGoogleGenerativeAI expects 'google_api_key'.
        # Our config.llm_api_key is loaded from GEMINI_API_KEY.
        # It will also try to load GOOGLE_API_KEY from env if not provided.
        if not api_key:
            print("Warning: Gemini API key not explicitly provided in HermesConfig. ChatGoogleGenerativeAI will attempt to use GOOGLE_API_KEY from environment.")
        return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key, 
                temperature=temperature
            )
    elif is_openai_model:
        # For OpenAI models, the parameter is 'openai_api_key'.
        # It will also try to load OPENAI_API_KEY from env if not provided.
        if not api_key:
            print("Warning: OpenAI API key not explicitly provided in HermesConfig. ChatOpenAI will attempt to use OPENAI_API_KEY from environment.")
        return ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                # Use the custom base URL if provided in the configuration.
                openai_api_base=config.llm_base_url, 
                temperature=temperature
            )
    else:
        # Fallback or error for unrecognized model families
        # Defaulting to ChatOpenAI might be risky if the model_name is not an OpenAI model.
        # Raising an error might be safer.
        raise ValueError(
            f"Could not determine LLM provider for model name: '{model_name}'. "
            f"Supported model families are Gemini (with prefix 'gemini-' or 'google/gemini') "
            f"and GPT (with prefix 'gpt-', 'text-davinci-', or 'openai/')."
        ) 