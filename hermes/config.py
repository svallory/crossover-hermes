import os
from typing import Literal, cast, List, Self

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, model_validator

from hermes.model.promotions import PromotionSpec


# Load environment variables from .env file
load_dotenv()

# Set LangSmith environment variables if tracing is enabled
langsmith_tracing_str = os.getenv("LANGSMITH_TRACING", "")
LANGSMITH_TRACING = langsmith_tracing_str.lower() in ("true", "1", "t", "yes", "y")

if LANGSMITH_TRACING:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"

# Define defaults that can be overridden by environment variables
_DEFAULT_CONFIG = {
    "LLM_PROVIDER": "Gemini",
    "INPUT_SPREADSHEET_ID": "14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U",
    "OUTPUT_SPREADSHEET_NAME": "Hermes Output",
    "OUTPUT_CSV": "true",
    "HERMES_PROCESSING_LIMIT": 0,
    "CHROMA_DB_PATH": "./chroma_db",
    "CHROMA_COLLECTION_NAME": "product_catalog",
    "CHROMA_EMBEDDING_MODEL": "text-embedding-3-small",
    "CHROMA_EMBEDDING_DIM": 1536,
    "OPENAI": {
        "STRONG_MODEL": "gpt-4.1",
        "WEAK_MODEL": "gpt-4.1-mini",
    },
    "GEMINI": {
        "STRONG_MODEL": "gemini-2.5-flash-preview-04-17",
        "WEAK_MODEL": "gemini-1.5-flash",
    },
}


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
            Literal["OpenAI", "Gemini"],
            os.getenv("LLM_PROVIDER", _DEFAULT_CONFIG["LLM_PROVIDER"]),
        )
    )

    llm_api_key: str | None = None

    llm_provider_url: str | None = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER_URL") or None
    )

    # Model configurations
    llm_strong_model_name: str | None = Field(default=None)
    llm_weak_model_name: str | None = Field(default=None)

    embedding_model_name: str = Field(
        default_factory=lambda: os.getenv("CHROMA_EMBEDDING_MODEL")
        or _DEFAULT_CONFIG["CHROMA_EMBEDDING_MODEL"]
    )
    chroma_embedding_dim: int = Field(
        default_factory=lambda: int(
            os.getenv("CHROMA_EMBEDDING_DIM") or _DEFAULT_CONFIG["CHROMA_EMBEDDING_DIM"]
        )
    )
    chroma_db_path: str = Field(
        default_factory=lambda: os.getenv("CHROMA_DB_PATH")
        or _DEFAULT_CONFIG["CHROMA_DB_PATH"]
    )
    chroma_collection_name: str = Field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION_NAME")
        or _DEFAULT_CONFIG["CHROMA_COLLECTION_NAME"]
    )
    input_spreadsheet_id: str = Field(
        default_factory=lambda: os.getenv("INPUT_SPREADSHEET_ID")
        or _DEFAULT_CONFIG["INPUT_SPREADSHEET_ID"]
    )
    output_spreadsheet_id: str | None = Field(
        default=None,
        description="Google Spreadsheet ID for output results. If None, defaults to input_spreadsheet_id or a dedicated sheet name if CSV is not used.",
    )
    output_spreadsheet_name: str = Field(
        default_factory=lambda: os.getenv("OUTPUT_SPREADSHEET_NAME")
        or _DEFAULT_CONFIG["OUTPUT_SPREADSHEET_NAME"]
    )
    hermes_processing_limit: int = Field(
        default_factory=lambda: int(
            os.getenv("HERMES_PROCESSING_LIMIT")
            or _DEFAULT_CONFIG["HERMES_PROCESSING_LIMIT"]
        )
    )

    @model_validator(mode="after")
    def set_provider_specific_defaults(self) -> Self:
        PROVIDER = self.llm_provider.upper()

        if not self.llm_provider_url:
            self.llm_provider_url = os.getenv("LLM_PROVIDER_URL") or None

        if not self.llm_api_key:
            self.llm_api_key = os.getenv(f"{PROVIDER}_API_KEY") or None

        if not self.llm_strong_model_name:
            self.llm_strong_model_name = (
                os.getenv(f"{PROVIDER}_STRONG_MODEL")
                or _DEFAULT_CONFIG[PROVIDER]["STRONG_MODEL"]
            )

        if not self.llm_weak_model_name:
            self.llm_weak_model_name = (
                os.getenv(f"{PROVIDER}_WEAK_MODEL")
                or _DEFAULT_CONFIG[PROVIDER]["WEAK_MODEL"]
            )

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
