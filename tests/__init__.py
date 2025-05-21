"""Tests for Hermes agents and pipeline."""

import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))


# Mock OpenAI API calls for testing
def mock_openai():
    """Create a mock patch for OpenAI API calls.
    This allows tests to run without making actual API calls.
    """
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "Mocked AI response"
    mock_client.chat.completions.create.return_value = mock_completion

    # For embeddings
    mock_embedding = MagicMock()
    mock_embedding.data = [MagicMock()]
    mock_embedding.data[0].embedding = [0.1] * 1536  # Mock dimensions
    mock_client.embeddings.create.return_value = mock_embedding

    return patch("openai.OpenAI", return_value=mock_client)
