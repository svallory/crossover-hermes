"""
Utility for creating and configuring LangChain LLM clients.
"""

from typing import Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr
from ..config import HermesConfig  # Relative import


def get_llm_client(
    config: HermesConfig,
    model_strength: Optional[Literal["weak", "strong"]] = "weak",
    temperature: float = 0.0,
) -> BaseChatModel:
    """
    Initializes and returns an LLM client based on the provided configuration.

    Args:
        config: The HermesConfig instance containing LLM settings.
        model_strength: Whether to use the 'weak' or 'strong' model as defined in config.
                      Defaults to 'strong'.
        temperature: The specific temperature to use for this LLM client instance.
                     Defaults to 0.0 for deterministic outputs.

    Returns:
        An instance of a LangChain chat model (e.g., ChatOpenAI, ChatGoogleGenerativeAI).

    Raises:
        ValueError: If the llm_api_key is not set for the chosen provider.
        ValueError: If the model name in the config is not set for the chosen provider.
        ValueError: If the llm_provider in HermesConfig is not 'OpenAI' or 'Gemini'.
    """
    if not config.llm_provider or config.llm_provider not in ["OpenAI", "Gemini"]:
        raise ValueError("The llm_provider in HermesConfig must be 'OpenAI' or 'Gemini'.")

    # Determine which model to use based on model_strength
    model_name = None
    if model_strength == "strong":
        model_name = config.llm_strong_model_name
    elif model_strength == "weak":
        model_name = config.llm_weak_model_name
    else:
        # Use model_name for backward compatibility
        model_name = config.llm_model_name

    if not model_name:
        raise ValueError(
            f"LLM model name for {model_strength} strength is not configured for {config.llm_provider} in HermesConfig."
        )

    if config.llm_provider == "OpenAI":
        if not config.llm_api_key:
            # OpenAI client will raise AuthenticationError if key is missing or invalid
            # but we can give a more specific warning/error earlier.
            raise ValueError("OpenAI API key is not set in HermesConfig or environment for OpenAI provider.")
        return ChatOpenAI(
            model=model_name,
            api_key=SecretStr(config.llm_api_key),
            base_url=config.llm_base_url,  # base_url is specific to OpenAI in our config
            temperature=temperature,
        )
    elif config.llm_provider == "Gemini":
        if not config.llm_api_key:
            # Google client will also raise an error, but a preemptive check is good.
            raise ValueError("Gemini API key is not set in HermesConfig or environment for Gemini provider.")
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=config.llm_api_key, temperature=temperature)
    else:
        # This case should be caught by the initial check, but as a safeguard:
        raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")
