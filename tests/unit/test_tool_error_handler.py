"""Tests for tool error handling utilities."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel, ValidationError

from hermes.utils.tool_error_handler import (
    ToolCallError,
    ToolCallValidator,
    ToolCallRetryHandler,
    detect_tool_calling_failure,
    is_tool_calling_validation_error,
    DEFAULT_RETRY_TEMPLATE,
)


class MockResponse(BaseModel):
    """Mock response model for testing."""

    message: str
    tool_calls: list = []


class TestToolCallValidator:
    """Tests for ToolCallValidator."""

    def test_validate_tool_calls_success(self):
        """Test successful validation when required tools are called."""
        validator = ToolCallValidator(required_tools=["find_products_for_occasion"])

        response = MagicMock()
        response.tool_calls = [{"name": "find_products_for_occasion"}]

        result = validator.validate_tool_calls(response)

        assert result["validation_passed"] is True
        assert "find_products_for_occasion" in result["called_tools"]
        assert len(result["missing_tools"]) == 0

    def test_validate_tool_calls_missing_required(self):
        """Test validation failure when required tools are missing."""
        validator = ToolCallValidator(required_tools=["find_products_for_occasion"])

        response = MagicMock()
        response.tool_calls = [{"name": "other_tool"}]

        with pytest.raises(ToolCallError) as exc_info:
            validator.validate_tool_calls(response)

        assert "find_products_for_occasion" in str(exc_info.value)
        assert "find_products_for_occasion" in exc_info.value.missing_tools

    def test_validate_tool_calls_no_tools(self):
        """Test validation when no tools are called."""
        validator = ToolCallValidator(required_tools=["find_products_for_occasion"])

        response = MagicMock()
        response.tool_calls = []

        with pytest.raises(ToolCallError):
            validator.validate_tool_calls(response)


class TestToolCallRetryHandler:
    """Tests for ToolCallRetryHandler."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        handler = ToolCallRetryHandler(max_retries=2)

        mock_chain = AsyncMock()
        mock_response = MockResponse(message="success")
        mock_chain.ainvoke.return_value = mock_response

        result = await handler.retry_with_tool_calling(
            chain=mock_chain, input_data={"test": "data"}
        )

        assert result == mock_response
        assert mock_chain.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_validation_error_recovery(self):
        """Test recovery from validation error on retry."""
        handler = ToolCallRetryHandler(
            max_retries=2, backoff_factor=0
        )  # No delay for testing

        mock_chain = AsyncMock()

        # First call raises ValidationError, second succeeds
        validation_error = ValidationError.from_exception_data(
            "MockResponse",
            [{"type": "missing", "loc": ("composer",), "msg": "Field required"}],
        )
        mock_success_response = MockResponse(message="success")

        mock_chain.ainvoke.side_effect = [validation_error, mock_success_response]

        result = await handler.retry_with_tool_calling(
            chain=mock_chain,
            input_data={"test": "data"},
            retry_prompt_template=DEFAULT_RETRY_TEMPLATE,
        )

        assert result == mock_success_response
        assert mock_chain.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test when all retries are exhausted."""
        handler = ToolCallRetryHandler(max_retries=1, backoff_factor=0)

        mock_chain = AsyncMock()
        validation_error = ValidationError.from_exception_data(
            "MockResponse",
            [{"type": "missing", "loc": ("composer",), "msg": "Field required"}],
        )
        mock_chain.ainvoke.side_effect = validation_error

        with pytest.raises(ToolCallError) as exc_info:
            await handler.retry_with_tool_calling(
                chain=mock_chain, input_data={"test": "data"}
            )

        assert "Validation error" in str(exc_info.value)
        assert mock_chain.ainvoke.call_count == 2  # Initial + 1 retry

    def test_extract_missing_tools_from_validation_error(self):
        """Test extraction of missing tools from validation error."""
        handler = ToolCallRetryHandler()

        error_str = "1 validation error for WorkflowOutput\ncomposer\n  Field required [type=missing, input_value={'email': CustomerEmail(e...de=None, details=None)}}, input_type=AddableValuesDict]"

        missing_tools = handler._extract_missing_tools_from_validation_error(error_str)

        assert "find_products_for_occasion" in missing_tools
        assert "find_complementary_products" in missing_tools

    def test_extract_missing_tools_specific_tool_mention(self):
        """Test extraction when specific tool is mentioned in error."""
        handler = ToolCallRetryHandler()

        error_str = "Error in compose_response: Failed to compose response for email E012: 'find_products_for_occasion'"

        missing_tools = handler._extract_missing_tools_from_validation_error(error_str)

        assert "find_products_for_occasion" in missing_tools

    def test_add_retry_guidance(self):
        """Test adding retry guidance to input data."""
        handler = ToolCallRetryHandler()

        input_data = {"email_analysis": {"test": "data"}}
        missing_tools = ["find_products_for_occasion"]

        result = handler._add_retry_guidance(
            input_data, missing_tools, DEFAULT_RETRY_TEMPLATE
        )

        assert "retry_guidance" in result
        assert "find_products_for_occasion" in result["retry_guidance"]


class TestDetectToolCallingFailure:
    """Tests for detect_tool_calling_failure function."""

    def test_detect_string_response_with_tool_reference(self):
        """Test detection of tool calling failure in string response."""
        response = "Error: 'find_products_for_occasion' tool not found"

        result = detect_tool_calling_failure(response)

        assert result is not None
        assert "find_products_for_occasion" in result

    def test_detect_validation_error_with_schema(self):
        """Test detection of validation error with expected schema."""
        response = {"invalid": "data"}

        result = detect_tool_calling_failure(response, MockResponse)

        assert result is not None
        assert "validation failed" in result.lower()

    def test_no_failure_detected(self):
        """Test when no failure is detected."""
        response = MockResponse(message="success")

        result = detect_tool_calling_failure(response, MockResponse)

        assert result is None


class TestIsToolCallingValidationError:
    """Tests for is_tool_calling_validation_error function."""

    def test_is_tool_calling_validation_error_true(self):
        """Test detection of tool calling validation error."""
        error = ValidationError.from_exception_data(
            "ComposerOutput",
            [{"type": "missing", "loc": ("composer",), "msg": "Field required"}],
        )

        result = is_tool_calling_validation_error(error)

        assert result is True

    def test_is_tool_calling_validation_error_false(self):
        """Test when error is not tool calling related."""
        error = ValidationError.from_exception_data(
            "MockResponse",
            [{"type": "missing", "loc": ("message",), "msg": "Field required"}],
        )

        result = is_tool_calling_validation_error(error)

        assert result is False

    def test_is_tool_calling_validation_error_not_validation_error(self):
        """Test when error is not a ValidationError."""
        error = ValueError("Some other error")

        result = is_tool_calling_validation_error(error)

        assert result is False
