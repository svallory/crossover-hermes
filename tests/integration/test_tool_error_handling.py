"""Integration tests for tool error handling in the workflow."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pydantic import ValidationError
from langchain_core.exceptions import OutputParserException

from hermes.agents.composer.agent import run_composer
from hermes.agents.composer.models import ComposerInput, ComposerOutput
from hermes.agents.classifier.models import ClassifierOutput, EmailAnalysis
from hermes.model.email import CustomerEmail
from hermes.config import HermesConfig
from hermes.utils.tool_error_handler import ToolCallError
from hermes.agents.composer.agent import Agents
from hermes.model.errors import Error


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
        vector_store_path="./test_chroma_db",
    )


class TestToolErrorHandling:
    """Integration tests for tool error handling."""

    @pytest.mark.asyncio
    async def test_composer_handles_validation_error_with_parser_retry(
        self, mock_composer_input, mock_hermes_config
    ):
        """Test composer when PydanticToolsParser retries on ValidationError and succeeds."""
        with patch("hermes.agents.composer.agent.get_llm_client") as mock_get_llm:
            mock_chain = AsyncMock()

            # Simulate parser raising OutputParserException (wrapping ValidationError) first, then success
            validation_error = ValidationError.from_exception_data(
                "ComposerOutput",
                [{"type": "missing", "loc": ("subject",), "msg": "Field required"}],
            )
            parser_exception = OutputParserException(
                error="Failed to parse",
                llm_output="invalid output",
                observation="",
            )
            parser_exception.__cause__ = validation_error  # Simulate original cause

            success_response = ComposerOutput(
                email_id="TEST001",
                subject="Re: Looking for a work bag",
                response_body="Thank you for your inquiry...",
                language="English",
                tone="professional",
                response_points=[],
            )
            # The chain.ainvoke is called multiple times by the parser's retry mechanism
            mock_chain.ainvoke.side_effect = [parser_exception, success_response]

            mock_llm = MagicMock()
            # The PydanticToolsParser is part of the chain returned by get_llm_client
            # So, its retry mechanism will call mock_chain.ainvoke multiple times.
            mock_llm.__or__ = MagicMock(return_value=mock_chain)
            mock_get_llm.return_value = mock_llm

            with patch("hermes.agents.composer.agent.COMPOSER_PROMPT") as mock_prompt:
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)

                result = await run_composer(
                    state=mock_composer_input,
                    runnable_config={
                        "configurable": {"hermes_config": mock_hermes_config}
                    },
                )

                assert Agents.COMPOSER in result
                assert isinstance(result[Agents.COMPOSER], ComposerOutput)
                assert mock_chain.ainvoke.call_count == 2  # Due to parser retry

    @pytest.mark.asyncio
    async def test_composer_fails_on_persistent_validation_error(
        self, mock_composer_input, mock_hermes_config
    ):
        """Test composer fails gracefully when PydanticToolsParser retries are exhausted."""
        with patch("hermes.agents.composer.agent.get_llm_client") as mock_get_llm:
            mock_chain = AsyncMock()

            validation_error = ValidationError.from_exception_data(
                "ComposerOutput",
                [{"type": "missing", "loc": ("subject",), "msg": "Field required"}],
            )
            parser_exception = OutputParserException(
                error="Failed to parse after retries",
                llm_output="invalid output",
                observation="",
            )
            parser_exception.__cause__ = validation_error

            # Simulate parser failing after all its retries
            # PydanticToolsParser retries 3 times by default.
            mock_chain.ainvoke.side_effect = [parser_exception] * 3  # Should be 3

            mock_llm = MagicMock()
            mock_llm.__or__ = MagicMock(return_value=mock_chain)
            mock_get_llm.return_value = mock_llm

            with patch("hermes.agents.composer.agent.COMPOSER_PROMPT") as mock_prompt:
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)

                result = await run_composer(
                    state=mock_composer_input,
                    runnable_config={
                        "configurable": {"hermes_config": mock_hermes_config}
                    },
                )

                assert "errors" in result
                assert Agents.COMPOSER in result["errors"]
                error_output = result["errors"][Agents.COMPOSER]
                # With the new ToolCallRetryHandler, we expect an Error wrapper containing a ToolCallError
                assert isinstance(error_output, Error)
                assert error_output.exception_type == "ToolCallError"
                assert error_output.exception_type == "ToolCallError"
                # The retry handler would be called 3 times (max_retries=2 + 1 initial)
                assert mock_chain.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_composer_handles_tool_call_error_gracefully(
        self, mock_composer_input, mock_hermes_config
    ):
        """Test composer handles ToolCallError by returning an error node."""
        with patch("hermes.agents.composer.agent.get_llm_client") as mock_get_llm:
            mock_chain = AsyncMock()
            tool_call_err = ToolCallError(
                "Tool calling failed", missing_tools=["some_tool"]
            )
            mock_chain.ainvoke.side_effect = tool_call_err  # Direct error from chain

            mock_llm = MagicMock()
            mock_llm.__or__ = MagicMock(return_value=mock_chain)
            mock_get_llm.return_value = mock_llm

            with patch("hermes.agents.composer.agent.COMPOSER_PROMPT") as mock_prompt:
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)

                result = await run_composer(
                    state=mock_composer_input,
                    runnable_config={
                        "configurable": {"hermes_config": mock_hermes_config}
                    },
                )

                assert "errors" in result
                assert Agents.COMPOSER in result["errors"]
                error_output = result["errors"][Agents.COMPOSER]
                assert isinstance(error_output, Error)
                assert error_output.exception_type == "ToolCallError"

    @pytest.mark.asyncio
    async def test_composer_handles_unexpected_error_gracefully(
        self, mock_composer_input, mock_hermes_config
    ):
        """Test composer handles unexpected errors by returning an error node."""
        with patch("hermes.agents.composer.agent.get_llm_client") as mock_get_llm:
            mock_chain = AsyncMock()
            unexpected_error = ValueError("Something broke unexpectedly")
            mock_chain.ainvoke.side_effect = unexpected_error  # Direct error from chain

            mock_llm = MagicMock()
            mock_llm.__or__ = MagicMock(return_value=mock_chain)
            mock_get_llm.return_value = mock_llm

            with patch("hermes.agents.composer.agent.COMPOSER_PROMPT") as mock_prompt:
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)

                result = await run_composer(
                    state=mock_composer_input,
                    runnable_config={
                        "configurable": {"hermes_config": mock_hermes_config}
                    },
                )

                assert "errors" in result
                assert Agents.COMPOSER in result["errors"]
                error_output = result["errors"][Agents.COMPOSER]
                assert isinstance(error_output, Error)

    # Test for the skip functionality has been removed as the associated fallback logic in the agent was removed.
