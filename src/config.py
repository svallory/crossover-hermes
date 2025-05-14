from dotenv import load_dotenv
import os

load_dotenv(override=True)

""" {cell}
## Configuration

This module defines the configuration settings for the Hermes application.
We use Pydantic for robust type validation and to ensure that all necessary
configuration parameters are provided and correctly formatted.

The `HermesConfig` class centralizes all settings, including:
- Language model parameters (e.g., model name, API key, base URL).
- Vector store configurations (e.g., path, embedding model, collection name).
- Output spreadsheet configuration.

A key design choice here is the inclusion of the `from_runnable_config` classmethod.
This allows for seamless integration with LangChain's `RunnableConfig`, enabling
configurations to be passed through the LangGraph execution flow effectively.
This promotes a clean separation of configuration management from the core
application logic, enhancing maintainability and flexibility.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class HermesConfig(BaseModel):
    """
    Central configuration for the Hermes application.
    """
    # FIXME: This does not adapt based on the LLM provider
    llm_api_key: Optional[str] = Field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY"),
        description="Gemini API key, if not set as an environment variable."
    )
    
    # The assignment provides a specific base URL for OpenAI API calls:
    # https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/
    # This should be set as OPENAI_BASE_URL in .env or passed directly when using the provided API key
    llm_base_url: Optional[str] = Field(
        default_factory=lambda: os.environ.get("OPENAI_BASE_URL"),
        description="Custom base URL for the OpenAI API. The assignment requires using https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/ with the provided API key."
    )
    
    # LLM Configuration
    llm_model_name: str = Field(
        default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-pro"),
        description="The name of the language model to use."
    )

    # Vector Store Configuration
    vector_store_path: str = Field(
        default="./chroma_db", 
        description="Path to the ChromaDB vector store persistence directory."
    )
    embedding_model_name: str = Field(
        default="text-embedding-ada-002", 
        description="Name of the embedding model to use for RAG."
    )
    chroma_collection_name: str = Field(
        default="hermes_product_catalog", 
        description="Name of the collection within ChromaDB."
    )

    
    # Output Configuration
    output_spreadsheet_name: str = Field(
        default="Hermes - AI Processed Emails", 
        description="Name for the output Google Spreadsheet."
    )

    @classmethod
    def from_runnable_config(cls, config: Optional[Dict[str, Any]] = None) -> "HermesConfig":
        """
        Creates a HermesConfig instance from a LangChain RunnableConfig (or a dictionary).
        This allows LangGraph components to access a structured configuration.
        
        Args:
            config: A dictionary-like object, typically from LangChain's config system.
        
        Returns:
            An instance of HermesConfig.
        """
        if config is None:
            return cls()  # Return with default values if no config is passed
        
        # Extract hermes_config from the configurable section if it exists
        hermes_config_params = config.get("configurable", {}).get("hermes_config", {})
        
        # If hermes_config is an instance of HermesConfig, return it directly
        if isinstance(hermes_config_params, cls):
            return hermes_config_params
        
        # If it's a dictionary, filter for known fields and initialize
        if isinstance(hermes_config_params, dict):
            known_fields = cls.model_fields.keys()
            filtered_config = {k: v for k, v in hermes_config_params.items() if k in known_fields}
            return cls(**filtered_config)
        
        # If no valid hermes_config found, return default instance
        return cls()

""" {cell}
### Configuration Implementation Notes

The `HermesConfig` class centralizes all configuration parameters for the Hermes system. Some key design choices:

1. **Parameter Organization**: Parameters are logically grouped by their purpose (LLM, vector store, output, etc.).

2. **Default Values**: All parameters have sensible defaults, making the configuration usable out-of-the-box.

3. **Documentation**: Each parameter has a description field, enhancing code readability and aiding users.

4. **LangChain Integration**: The `from_runnable_config` method enables seamless integration with LangChain's configuration system, supporting scenarios where:
   - No configuration is provided (`config=None`)
   - A HermesConfig instance is directly passed via configurable
   - Configuration parameters are passed as a dictionary

This design balances flexibility with usability, making it easy to customize the system behavior while providing reasonable defaults.
""" 