"""Environment configuration utilities for the Hermes application.
Import this module first to configure environment variables before other imports.
"""

import logging
import os

logger = logging.getLogger(__name__)


def configure_environment():
    """Configure environment variables for optimal operation.
    Call this function before importing other modules.
    """
    # No longer need to disable tokenizers parallelism since we are using OpenAI embeddings exclusively

    # Add any other environment setup here

    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY environment variable not set. You must provide it when initializing the vector store."
        )

    return True


# Auto-configure when this module is imported
configure_environment()
