"""Utility for creating and configuring LangChain LLM clients."""

from typing import Literal

from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai.chat_models.base import ChatOpenAI, BaseChatOpenAI
from pydantic import BaseModel, SecretStr

from ..config import HermesConfig
from hermes.utils.logger import logger, get_agent_logger


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
    if isinstance(llm, BaseChatOpenAI):
        return llm.with_structured_output(
            schema=schema,
            method="json_schema",
            tools=tools,
            strict=True,
        )

    elif isinstance(llm, ChatGoogleGenerativeAI):
        model_supports_tool_choice = lambda model: (
            "gemini-1.5-pro" in model
            or "gemini-1.5-flash" in model
            or "gemini-2.5" in model
        )

        tool_choice = schema.__name__ if model_supports_tool_choice(llm.model) else None

        # Add a parser to extract the arguments of the schema tool call into an instance of the schema.
        parser = PydanticToolsParser(tools=[schema], first_tool_only=True)

        try:
            # Bind all tools (user tools + schema tool)
            # and set tool_choice to force schema output.
            # Include ls_structured_output_format for LangSmith if supported.
            bound_llm = llm.bind_tools(
                tools=list(tools) + [schema],
                tool_choice=tool_choice,
                ls_structured_output_format={
                    "kwargs": {"method": "function_calling"},
                    "schema": convert_to_openai_tool(schema),
                },
            )
        except Exception as e:
            logger.warning(
                get_agent_logger(
                    "Utils",
                    f"Gemini bind_tools with ls_structured_output_format failed with {type(e).__name__}: {e}. Falling back.",
                )
            )
            # Fallback without ls_structured_output_format
            bound_llm = llm.bind_tools(
                tools=list(tools) + [schema],
                tool_choice=tool_choice,
            )

        return bound_llm | parser

    raise ValueError(
        f"Unsupported LLM type: {type(llm)}. Only ChatOpenAI and ChatGoogleGenerativeAI are supported."
    )


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

    # Determine the model name and ensure it's set
    if model_strength == "weak":
        model_name = config.llm_weak_model_name
        if not model_name:
            raise ValueError(
                f"LLM weak model name not set in HermesConfig for provider {config.llm_provider}."
            )
    else:  # Defaults to strong if model_strength is None or "strong"
        model_name = config.llm_strong_model_name
        if not model_name:
            raise ValueError(
                f"LLM strong model name not set in HermesConfig for provider {config.llm_provider}."
            )

    if config.llm_provider == "OpenAI":
        if not config.llm_api_key:
            # OpenAI client will raise AuthenticationError if key is missing or invalid
            # but we can give a more specific warning/error earlier.
            raise ValueError(
                "OpenAI API key is not set in HermesConfig or environment for OpenAI provider."
            )
        llm = ChatOpenAI(
            model=model_name,  # Now guaranteed to be a string
            api_key=SecretStr(config.llm_api_key),
            base_url=config.llm_provider_url,
            temperature=temperature,
        )

    elif config.llm_provider == "Gemini":
        if not config.llm_api_key:
            # Google client will also raise an error, but a preemptive check is good.
            raise ValueError(
                "Gemini API key is not set in HermesConfig or environment for Gemini provider."
            )
        llm = ChatGoogleGenerativeAI(
            model=model_name,  # Now guaranteed to be a string
            google_api_key=config.llm_api_key,
            base_url=config.llm_provider_url,
            temperature=temperature,
        )
    else:
        # This case should be caught by the initial check, but as a safeguard:
        raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")

    return _bind_tools_with_structured_output(llm, schema, tools)
