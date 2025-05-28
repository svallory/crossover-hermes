"""Integration tests for tool error handling in the workflow."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pydantic import ValidationError

from hermes.agents.composer.agent import run_composer
from hermes.agents.composer.models import ComposerInput, ComposerOutput
from hermes.agents.classifier.models import ClassifierOutput, EmailAnalysis
from hermes.model.email import CustomerEmail
from hermes.config import HermesConfig
from hermes.utils.tool_error_handler import ToolCallError


@pytest.fixture
def mock_email():
    """Create a mock customer email."""
    return CustomerEmail(
        email_id="TEST001",
        subject="Looking for a work bag",
        message="Hi, I'm looking for a professional bag for work occasions. Can you help?",
    )


@pytest.fixture
def mock_email_analysis():
    """Create a mock email analysis."""
    return EmailAnalysis(
        email_id="TEST001",
        primary_intent="product inquiry",
        language="English",
        segments=[],
    )


@pytest.fixture
def mock_classifier_output(mock_email_analysis):
    """Create a mock classifier output."""
    return ClassifierOutput(email_analysis=mock_email_analysis)


@pytest.fixture
def mock_composer_input(mock_email, mock_classifier_output):
    """Create a mock composer input."""
    return ComposerInput(email=mock_email, classifier=mock_classifier_output)


@pytest.fixture
def mock_hermes_config():
    """Create a mock Hermes config."""
    return HermesConfig(
        llm_provider="OpenAI",
        llm_api_key="test-key",
        llm_model_weak="gpt-3.5-turbo",
        llm_model_strong="gpt-4",
        vector_store_path="./test_chroma_db",
    )


class TestToolErrorHandling:
    """Integration tests for tool error handling."""

    @pytest.mark.asyncio
    async def test_composer_handles_validation_error_with_retry(
        self, mock_composer_input, mock_hermes_config
    ):
        """Test that composer handles validation errors with retry logic."""

        # Mock the LLM client to simulate validation error then success
        with patch("hermes.agents.composer.agent.get_llm_client") as mock_get_llm:
            # Create mock chain that fails first, succeeds second
            mock_chain = AsyncMock()

            # First call raises ValidationError (simulating tool calling failure)
            validation_error = ValidationError.from_exception_data(
                "ComposerOutput",
                [{"type": "missing", "loc": ("composer",), "msg": "Field required"}],
            )

            # Second call succeeds
            success_response = ComposerOutput(
                email_id="TEST001",
                subject="Re: Looking for a work bag",
                response_body="Thank you for your inquiry about work bags...",
                language="English",
                tone="professional and helpful",
                response_points=[],
            )

            mock_chain.ainvoke.side_effect = [validation_error, success_response]

            # Mock LLM client to return our mock chain
            mock_llm = MagicMock()
            mock_llm.__or__ = MagicMock(return_value=mock_chain)
            mock_get_llm.return_value = mock_llm

            # Mock the prompt
            with patch("hermes.agents.composer.agent.COMPOSER_PROMPT") as mock_prompt:
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)

                # Run the composer
                result = await run_composer(
                    state=mock_composer_input,
                    runnable_config={
                        "configurable": {"hermes_config": mock_hermes_config}
                    },
                )

                # Verify success
                assert "composer" in result
                assert isinstance(result["composer"], ComposerOutput)
                assert result["composer"].email_id == "TEST001"

                # Verify retry was attempted (chain called twice)
                assert mock_chain.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_composer_falls_back_to_no_tools_on_persistent_failure(
        self, mock_composer_input, mock_hermes_config
    ):
        """Test that composer falls back to no-tools execution when retries fail."""

        with patch("hermes.agents.composer.agent.get_llm_client") as mock_get_llm:
            # Create mock chains - one that always fails, one that succeeds
            mock_failing_chain = AsyncMock()
            mock_success_chain = AsyncMock()

            # Failing chain always raises ValidationError
            validation_error = ValidationError.from_exception_data(
                "ComposerOutput",
                [{"type": "missing", "loc": ("composer",), "msg": "Field required"}],
            )
            mock_failing_chain.ainvoke.side_effect = validation_error

            # Success chain returns valid response
            success_response = ComposerOutput(
                email_id="TEST001",
                subject="Re: Looking for a work bag",
                response_body="Thank you for your inquiry...",
                language="English",
                tone="professional and helpful",
                response_points=[],
            )
            mock_success_chain.ainvoke.return_value = success_response

            # Mock LLM clients - first with tools (fails), second without tools (succeeds)
            def mock_llm_side_effect(*args, **kwargs):
                mock_llm = MagicMock()
                if kwargs.get("tools", []):  # Has tools - will fail
                    mock_llm.__or__ = MagicMock(return_value=mock_failing_chain)
                else:  # No tools - will succeed
                    mock_llm.__or__ = MagicMock(return_value=mock_success_chain)
                return mock_llm

            mock_get_llm.side_effect = mock_llm_side_effect

            # Mock the prompt
            with patch("hermes.agents.composer.agent.COMPOSER_PROMPT") as mock_prompt:
                mock_prompt.__or__ = MagicMock(
                    side_effect=[mock_failing_chain, mock_success_chain]
                )

                # Run the composer
                result = await run_composer(
                    state=mock_composer_input,
                    runnable_config={
                        "configurable": {"hermes_config": mock_hermes_config}
                    },
                )

                # Verify success with fallback
                assert "composer" in result
                assert isinstance(result["composer"], ComposerOutput)
                assert result["composer"].email_id == "TEST001"

                # Verify both LLM clients were created (with and without tools)
                assert mock_get_llm.call_count >= 2

    @pytest.mark.asyncio
    async def test_composer_handles_tool_call_error_gracefully(
        self, mock_composer_input, mock_hermes_config
    ):
        """Test that composer handles ToolCallError gracefully."""

        with patch("hermes.agents.composer.agent.get_llm_client") as mock_get_llm:
            # Create mock retry handler that raises ToolCallError
            with patch(
                "hermes.agents.composer.agent.ToolCallRetryHandler"
            ) as mock_retry_handler_class:
                mock_retry_handler = AsyncMock()
                mock_retry_handler.retry_with_tool_calling.side_effect = ToolCallError(
                    "Tool calling failed after retries",
                    missing_tools=["find_products_for_occasion"],
                )
                mock_retry_handler_class.return_value = mock_retry_handler

                # Mock fallback chain that succeeds
                mock_fallback_chain = AsyncMock()
                success_response = ComposerOutput(
                    email_id="TEST001",
                    subject="Re: Looking for a work bag",
                    response_body="Thank you for your inquiry...",
                    language="English",
                    tone="professional and helpful",
                    response_points=[],
                )
                mock_fallback_chain.ainvoke.return_value = success_response

                # Mock LLM clients
                def mock_llm_side_effect(*args, **kwargs):
                    mock_llm = MagicMock()
                    if kwargs.get("tools", []):  # Has tools
                        mock_llm.__or__ = MagicMock(return_value=AsyncMock())
                    else:  # No tools - fallback
                        mock_llm.__or__ = MagicMock(return_value=mock_fallback_chain)
                    return mock_llm

                mock_get_llm.side_effect = mock_llm_side_effect

                # Mock the prompt
                with patch(
                    "hermes.agents.composer.agent.COMPOSER_PROMPT"
                ) as mock_prompt:
                    mock_prompt.__or__ = MagicMock(return_value=mock_fallback_chain)

                    # Run the composer
                    result = await run_composer(
                        state=mock_composer_input,
                        runnable_config={
                            "configurable": {"hermes_config": mock_hermes_config}
                        },
                    )

                    # Verify success with fallback
                    assert "composer" in result
                    assert isinstance(result["composer"], ComposerOutput)
                    assert result["composer"].email_id == "TEST001"
                    # Verify retry was attempted
                    mock_retry_handler.retry_with_tool_calling.assert_called_once()
