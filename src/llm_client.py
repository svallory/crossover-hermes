"""
Utility for creating and configuring LangChain LLM clients.
"""
from typing import Union

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from .config import HermesConfig

def get_llm_client(config: HermesConfig, temperature: float) -> Union[ChatOpenAI, ChatGoogleGenerativeAI]:
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

    # Convert model_name to lowercase for case-insensitive matching
    model_name_lower = model_name.lower()

    if "gemini" in model_name_lower:
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
    elif "gpt" in model_name_lower:
        # For OpenAI models, the parameter is 'openai_api_key'.
        # It will also try to load OPENAI_API_KEY from env if not provided.
        if not api_key:
             print("Warning: OpenAI API key not explicitly provided in HermesConfig. ChatOpenAI will attempt to use OPENAI_API_KEY from environment.")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            # If llm_base_url were still in config, it would be:
            # openai_api_base=config.llm_base_url, 
            temperature=temperature
        )
    else:
        # Fallback or error for unrecognized model families
        # Defaulting to ChatOpenAI might be risky if the model_name is not an OpenAI model.
        # Raising an error might be safer.
        raise ValueError(
            f"Could not determine LLM provider for model name: '{model_name}'. "
            f"Supported model names should contain 'gemini' or 'gpt'."
        ) 