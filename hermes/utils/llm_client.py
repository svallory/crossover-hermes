"""Utility for creating and configuring LangChain LLM clients."""

from typing import Literal

from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticToolsParser
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr

from ..config import HermesConfig  # Relative import


def _model_supports_tool_choice(model: str) -> bool:
    return (
        "openai" in model
        or "gemini-1.5-pro" in model
        or "gemini-1.5-flash" in model
        or "gemini-2" in model
    )


def _bind_tools_with_structured_output(
    llm: ChatOpenAI | ChatGoogleGenerativeAI,
    schema: type[BaseModel],
    tools: list[BaseTool] = [],
) -> Runnable:
    """
    Combines the functionality of bind_tools and with_structured_output for LangChain models.

    This helper works around the limitation that bind_tools and with_structured_output
    cannot be chained together since both return Runnables.

    Args:
        llm: The base chat model (ChatOpenAI or ChatGoogleGenerativeAI)
        schema: The Pydantic BaseModel class for structured output
        tools: List of tools to bind to the model

    Returns:
        A Runnable that has both tools bound and structured output configured

    Raises:
        ValueError: If the LLM type is not supported
    """
    # Handle ChatOpenAI
    if not isinstance(llm, ChatOpenAI) and not isinstance(llm, ChatGoogleGenerativeAI):
        raise ValueError(
            f"Unsupported LLM type: {type(llm)}. Only ChatOpenAI and ChatGoogleGenerativeAI are supported."
        )

    model_name = getattr(llm, "model", getattr(llm, "model_name", ""))

    # Convert schema to a tool
    output_schema = convert_to_openai_tool(schema)

    # For OpenAI, we can use tool_choice to force calling the structured output tool
    # But not all Gemini models support tool_choice
    tool_choice = (
        output_schema["name"] if _model_supports_tool_choice(model_name) else None
    )

    # Create all tools list (user tools + schema tool)
    all_tools = list(tools) + [schema]

    # Use PydanticToolsParser since we only accept BaseModel schemas
    parser = PydanticToolsParser(tools=[schema], first_tool_only=True)

    try:
        # Bind all tools with tool_choice set to our schema tool
        llm_with_tools = llm.bind_tools(
            tools=all_tools,
            tool_choice=tool_choice,
            ls_structured_output_format={
                "kwargs": {"method": "function_calling"},
                "schema": output_schema,
            },
        )
    except Exception:
        # Fallback without ls_structured_output_format
        llm_with_tools = llm.bind_tools(all_tools, tool_choice=tool_choice)

    return llm_with_tools | parser


def get_llm_client(
    config: HermesConfig,
    schema: type[BaseModel],
    model_strength: Literal["weak", "strong"] | None = "strong",
    temperature: float = 0.0,
    tools: list[BaseTool] = [],
) -> Runnable:
    """Initializes and returns an LLM client based on the provided configuration.

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
        raise ValueError(
            "The llm_provider in HermesConfig must be 'OpenAI' or 'Gemini'."
        )

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
            f"LLM model name for {model_strength or 'default'} strength is not configured for {config.llm_provider} in HermesConfig."
        )

    if config.llm_provider == "OpenAI":
        if not config.llm_api_key:
            # OpenAI client will raise AuthenticationError if key is missing or invalid
            # but we can give a more specific warning/error earlier.
            raise ValueError(
                "OpenAI API key is not set in HermesConfig or environment for OpenAI provider."
            )
        return _bind_tools_with_structured_output(
            ChatOpenAI(
                model=model_name,
                api_key=SecretStr(config.llm_api_key),
                base_url=config.llm_base_url,  # base_url is specific to OpenAI in our config
                temperature=temperature,
            ),
            schema,
            tools,
        )
    elif config.llm_provider == "Gemini":
        if not config.llm_api_key:
            # Google client will also raise an error, but a preemptive check is good.
            raise ValueError(
                "Gemini API key is not set in HermesConfig or environment for Gemini provider."
            )
        return _bind_tools_with_structured_output(
            ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=config.llm_api_key,
                temperature=temperature,
                type=schema,
            ),
            schema,
            tools,
        )
    else:
        # This case should be caught by the initial check, but as a safeguard:
        raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")
