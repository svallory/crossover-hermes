import os
from typing import Literal, TypeVar, cast, List, Self

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, model_validator

from hermes.model.promotions import PromotionSpec


def load_app_env_vars():
    """Load environment variables from .env file and set LangSmith variables if tracing is enabled."""
    load_dotenv()  # Load from .env file in the current directory or parent directories

    # Set LangSmith environment variables if tracing is enabled
    langsmith_tracing_str = os.getenv("LANGSMITH_TRACING", "False")
    LANGSMITH_TRACING = langsmith_tracing_str.lower() in ("true", "1", "t")

    if LANGSMITH_TRACING:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_TRACING"] = (
            "true"  # Redundant with LANGCHAIN_TRACING_V2 but set for clarity
        )

        # Ensure other LangSmith vars are also propagated if needed
        for var_suffix in ["API_KEY", "ENDPOINT", "PROJECT"]:
            lc_var = f"LANGCHAIN_{var_suffix}"
            ls_var = f"LANGSMITH_{var_suffix}"
            if os.getenv(lc_var) and not os.getenv(ls_var):
                os.environ[ls_var] = str(os.getenv(lc_var))
            elif os.getenv(ls_var) and not os.getenv(lc_var):
                os.environ[lc_var] = str(os.getenv(ls_var))

    # For other variables like OPENAI_API_KEY, GEMINI_API_KEY, etc.,
    # Pydantic models will attempt to read them directly from os.environ.
    # load_dotenv() ensures they are available if defined in a .env file.


# Call it at module level so .env is loaded when config.py is imported
load_app_env_vars()

# Define defaults that can be overridden by environment variables
DEFAULT_LLM_PROVIDER: Literal["OpenAI", "Gemini"] = "Gemini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

# Strong and weak model defaults
DEFAULT_OPENAI_STRONG_MODEL = "gpt-4.1"
DEFAULT_OPENAI_WEAK_MODEL = "gpt-4.1-mini"
DEFAULT_GEMINI_STRONG_MODEL = "gemini-2.5-flash-preview-04-17"
DEFAULT_GEMINI_WEAK_MODEL = "gemini-1.5-flash"

DEFAULT_OPENAI_BASE_URL = (
    "https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/"
)
DEFAULT_INPUT_SPREADSHEET_ID = "14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U"
DEFAULT_OUTPUT_SPREADSHEET_NAME = "Hermes - Classifier agent Test Output"
DEFAULT_VECTOR_STORE_PATH = "./chroma_db"
DEFAULT_CHROMA_COLLECTION_NAME = "hermes_product_catalog"

# Define a TypeVar for the 'from_runnable_config' classmethod return type
T = TypeVar("T", bound="HermesConfig")


class HermesConfig(BaseModel):
    """Central configuration for the Hermes application.
    Values are sourced from environment variables, with defaults provided.
    """

    promotion_specs: List[PromotionSpec] = Field(
        default_factory=list,
        description="List of promotion specifications for the application",
    )
    llm_provider: Literal["OpenAI", "Gemini"] = Field(
        default_factory=lambda: cast(
            Literal["OpenAI", "Gemini"], os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
        )
    )
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    # Model configurations
    llm_strong_model_name: str = Field(
        default=DEFAULT_OPENAI_STRONG_MODEL
        if DEFAULT_LLM_PROVIDER == "OpenAI"
        else DEFAULT_GEMINI_STRONG_MODEL
    )
    llm_weak_model_name: str = Field(
        default=DEFAULT_OPENAI_WEAK_MODEL
        if DEFAULT_LLM_PROVIDER == "OpenAI"
        else DEFAULT_GEMINI_WEAK_MODEL
    )

    embedding_model_name: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    )
    openai_api_key: str | None = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY") or None
    )
    openai_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
    )

    vector_store_path: str = Field(
        default_factory=lambda: os.getenv(
            "VECTOR_STORE_PATH", DEFAULT_VECTOR_STORE_PATH
        )
    )
    chroma_collection_name: str = Field(
        default_factory=lambda: os.getenv(
            "CHROMA_COLLECTION_NAME", DEFAULT_CHROMA_COLLECTION_NAME
        )
    )
    input_spreadsheet_id: str = Field(
        default_factory=lambda: os.getenv(
            "INPUT_SPREADSHEET_ID", DEFAULT_INPUT_SPREADSHEET_ID
        )
    )
    output_spreadsheet_id: str | None = Field(
        default=None,
        description="Google Spreadsheet ID for output results. If None, defaults to input_spreadsheet_id or a dedicated sheet name if CSV is not used.",
    )
    output_spreadsheet_name: str = Field(
        default_factory=lambda: os.getenv(
            "OUTPUT_SPREADSHEET_NAME", DEFAULT_OUTPUT_SPREADSHEET_NAME
        )
    )

    @model_validator(mode="after")
    def set_provider_specific_defaults(self) -> Self:
        if self.llm_provider == "OpenAI":
            if self.llm_api_key is None:
                self.llm_api_key = os.getenv("OPENAI_API_KEY") or None
            if self.llm_base_url is None:
                self.llm_base_url = os.getenv(
                    "OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL
                )

            # Set strong model
            if self.llm_strong_model_name is None:
                env_strong_model = os.getenv("OPENAI_STRONG_MODEL")
                self.llm_strong_model_name = (
                    env_strong_model
                    if env_strong_model
                    else DEFAULT_OPENAI_STRONG_MODEL
                )

            # Set weak model
            if self.llm_weak_model_name is None:
                env_weak_model = os.getenv("OPENAI_WEAK_MODEL")
                self.llm_weak_model_name = (
                    env_weak_model if env_weak_model else DEFAULT_OPENAI_WEAK_MODEL
                )

        elif self.llm_provider == "Gemini":
            if self.llm_api_key is None:
                self.llm_api_key = os.getenv("GEMINI_API_KEY") or None

            # Set strong model
            if self.llm_strong_model_name is None:
                env_strong_model = os.getenv("GEMINI_STRONG_MODEL")
                self.llm_strong_model_name = (
                    env_strong_model
                    if env_strong_model
                    else DEFAULT_GEMINI_STRONG_MODEL
                )

            # Set weak model
            if self.llm_weak_model_name is None:
                env_weak_model = os.getenv("GEMINI_WEAK_MODEL")
                self.llm_weak_model_name = (
                    env_weak_model if env_weak_model else DEFAULT_GEMINI_WEAK_MODEL
                )

        # Ensure API keys are None if they are empty strings
        if self.llm_api_key == "":
            self.llm_api_key = None
        if self.openai_api_key == "":
            self.openai_api_key = None

        return self

    def as_runnable_config(self) -> RunnableConfig:
        return {"configurable": {"hermes_config": self}}

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig | None = None) -> Self:
        """Creates a HermesConfig instance from a LangChain RunnableConfig (or a dictionary).
        This allows LangGraph components to access a structured configuration.

        Args:
            config: A dictionary-like object, typically from LangChain's config system.

        Returns:
            An instance of HermesConfig.

        """
        if config is None:
            return cls()

        hermes_config_params = config.get("configurable", {}).get("hermes_config", {})

        if isinstance(hermes_config_params, cls):
            return hermes_config_params

        if isinstance(hermes_config_params, dict):
            # If hermes_config_params is a dict, it might be an already instantiated
            # HermesConfig that was dict()-serialized, or just parameters.
            # We prioritize using its values.
            # The default_factory in Pydantic fields will fetch from env if not provided here.
            return cls(**hermes_config_params)

        return cls()
