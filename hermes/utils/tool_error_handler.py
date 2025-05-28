"""Tool calling error detection and retry utilities for LLM agents.

This module provides utilities to detect when an LLM fails to call required tools
and implements retry mechanisms to handle such failures gracefully.
"""

import logging
from typing import Any, Dict, List, Optional, Type
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel, ValidationError
import re

logger = logging.getLogger(__name__)


class ToolCallError(Exception):
    """Exception raised when tool calling fails or is incomplete."""

    def __init__(
        self,
        message: str,
        missing_tools: List[str] = None,
        original_error: Exception = None,
    ):
        super().__init__(message)
        self.missing_tools = missing_tools or []
        self.original_error = original_error


class ToolCallValidator:
    """Validates that required tools were called by the LLM."""

    def __init__(
        self, required_tools: List[str] = None, optional_tools: List[str] = None
    ):
        """Initialize the validator.

        Args:
            required_tools: List of tool names that must be called
            optional_tools: List of tool names that may be called
        """
        self.required_tools = required_tools or []
        self.optional_tools = optional_tools or []

    def validate_tool_calls(self, response: Any) -> Dict[str, Any]:
        """Validate that required tools were called in the LLM response.

        Args:
            response: The LLM response to validate

        Returns:
            Dict with validation results

        Raises:
            ToolCallError: If required tools were not called
        """
        called_tools = []

        # Extract tool calls from different response formats
        if hasattr(response, "tool_calls") and response.tool_calls:
            called_tools = [
                tool_call.get("name", "") for tool_call in response.tool_calls
            ]
        elif isinstance(response, AIMessage) and hasattr(response, "tool_calls"):
            called_tools = [
                tool_call.get("name", "") for tool_call in response.tool_calls
            ]
        elif isinstance(response, dict) and "tool_calls" in response:
            called_tools = [
                tool_call.get("name", "") for tool_call in response["tool_calls"]
            ]

        # Check for missing required tools
        missing_tools = [
            tool for tool in self.required_tools if tool not in called_tools
        ]

        if missing_tools:
            raise ToolCallError(
                f"Required tools not called: {missing_tools}. Called tools: {called_tools}",
                missing_tools=missing_tools,
            )

        return {
            "called_tools": called_tools,
            "missing_tools": missing_tools,
            "validation_passed": len(missing_tools) == 0,
        }


class ToolCallRetryHandler:
    """Handles retrying LLM calls when tool calling fails."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        """Initialize the retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Factor to multiply delay between retries
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def retry_with_tool_calling(
        self,
        chain: Runnable,
        input_data: Dict[str, Any],
        validator: ToolCallValidator = None,
        retry_prompt_template: str = None,
    ) -> Any:
        """Retry an LLM chain call with tool calling validation.

        Args:
            chain: The LangChain runnable to execute
            input_data: Input data for the chain
            validator: Tool call validator (optional)
            retry_prompt_template: Template for retry prompts

        Returns:
            The successful response from the chain

        Raises:
            ToolCallError: If all retries fail
        """
        last_error = None
        original_input = input_data.copy()

        for attempt in range(self.max_retries + 1):
            try:
                # Execute the chain
                response = await chain.ainvoke(input_data)

                # Validate tool calls if validator provided
                if validator:
                    validator.validate_tool_calls(response)

                logger.info(f"Tool calling succeeded on attempt {attempt + 1}")
                return response

            except ToolCallError as e:
                last_error = e
                logger.warning(f"Tool calling failed on attempt {attempt + 1}: {e}")

                # If this is the last attempt, raise the error
                if attempt >= self.max_retries:
                    break

                # Modify input for retry with additional guidance
                if retry_prompt_template and e.missing_tools:
                    input_data = self._add_retry_guidance(
                        original_input, e.missing_tools, retry_prompt_template
                    )

                # Add delay between retries
                if self.backoff_factor > 0:
                    import asyncio

                    await asyncio.sleep(self.backoff_factor * (attempt + 1))

            except ValidationError as e:
                # Handle Pydantic validation errors (like the one in the original error)
                error_str = str(e)

                # Check if this is a tool calling related validation error
                missing_tools = self._extract_missing_tools_from_validation_error(
                    error_str
                )

                last_error = ToolCallError(
                    f"Validation error in LLM response: {error_str}",
                    missing_tools=missing_tools,
                    original_error=e,
                )
                logger.warning(f"Validation error on attempt {attempt + 1}: {e}")

                if attempt >= self.max_retries:
                    break

                # Add retry guidance for validation errors
                if retry_prompt_template and missing_tools:
                    input_data = self._add_retry_guidance(
                        original_input, missing_tools, retry_prompt_template
                    )

            except Exception as e:
                # Handle other unexpected errors
                last_error = ToolCallError(
                    f"Unexpected error during tool calling: {str(e)}", original_error=e
                )
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")

                if attempt >= self.max_retries:
                    break

        # All retries failed
        raise last_error or ToolCallError("All retry attempts failed")

    def _extract_missing_tools_from_validation_error(self, error_str: str) -> List[str]:
        """Extract potentially missing tools from validation error messages.

        Args:
            error_str: The validation error string

        Returns:
            List of potentially missing tool names
        """
        missing_tools = []

        # Look for specific tool names mentioned in error
        tool_patterns = [
            r"find_products_for_occasion",
            r"find_product_by_id",
            r"find_product_by_name",
            r"find_complementary_products",
            r"search_products_with_filters",
        ]

        for pattern in tool_patterns:
            if re.search(pattern, error_str, re.IGNORECASE):
                missing_tools.append(pattern)

        # Look for field required errors that might indicate missing tool output
        if "Field required" in error_str and "composer" in error_str.lower():
            # This suggests the composer agent didn't produce proper output, possibly due to tool calling failure
            missing_tools.extend(
                ["find_products_for_occasion", "find_complementary_products"]
            )

        return missing_tools

    def _add_retry_guidance(
        self, input_data: Dict[str, Any], missing_tools: List[str], retry_template: str
    ) -> Dict[str, Any]:
        """Add guidance to the input for retry attempts.

        Args:
            input_data: Original input data
            missing_tools: List of tools that were not called
            retry_template: Template for retry guidance

        Returns:
            Modified input data with retry guidance
        """
        # Create a copy to avoid modifying the original
        retry_input = input_data.copy()

        # Add retry guidance to the prompt or input
        retry_guidance = retry_template.format(missing_tools=", ".join(missing_tools))

        # Try to add guidance to common input fields
        if "email_analysis" in retry_input:
            # For composer agent, add guidance to the email analysis
            if isinstance(retry_input["email_analysis"], dict):
                retry_input["retry_guidance"] = retry_guidance
            else:
                retry_input["retry_guidance"] = retry_guidance
        elif "input" in retry_input:
            retry_input["input"] += f"\n\n{retry_guidance}"
        elif "prompt" in retry_input:
            retry_input["prompt"] += f"\n\n{retry_guidance}"
        elif "query" in retry_input:
            retry_input["query"] += f"\n\n{retry_guidance}"
        else:
            # Add as a new field
            retry_input["retry_guidance"] = retry_guidance

        return retry_input


def detect_tool_calling_failure(
    response: Any, expected_schema: Type[BaseModel] = None
) -> Optional[str]:
    """Detect if an LLM response indicates a tool calling failure.

    Args:
        response: The LLM response to analyze
        expected_schema: Expected Pydantic schema for the response

    Returns:
        Error message if failure detected, None otherwise
    """
    # Check for common tool calling failure patterns
    if isinstance(response, str):
        # Look for error patterns in string responses
        error_patterns = [
            r"'(\w+)' tool",  # References to specific tools
            r"function (\w+)",  # Function references
            r"call (\w+)",  # Call references
            r"tool_choice",  # Tool choice errors
            r"ValidationError",  # Validation errors
            r"find_products_for_occasion",  # Specific tool that's failing
        ]

        for pattern in error_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return f"Potential tool calling failure detected in response: {response[:200]}..."

    # Check for validation errors with expected schema
    if expected_schema:
        try:
            if isinstance(response, dict):
                expected_schema.model_validate(response)
            elif hasattr(response, "model_dump"):
                expected_schema.model_validate(response.model_dump())
        except ValidationError as e:
            error_str = str(e)
            # Check if this looks like a tool calling issue
            if any(
                tool in error_str
                for tool in [
                    "find_products_for_occasion",
                    "find_product_by",
                    "search_products",
                ]
            ):
                return f"Tool calling validation failure: {error_str}"
            return f"Response validation failed: {error_str}"

    return None


def is_tool_calling_validation_error(error: Exception) -> bool:
    """Check if an exception is likely caused by tool calling failures.

    Args:
        error: The exception to check

    Returns:
        True if this looks like a tool calling validation error
    """
    if not isinstance(error, ValidationError):
        return False

    error_str = str(error)

    # Look for patterns that suggest tool calling issues
    tool_calling_indicators = [
        "find_products_for_occasion",
        "find_product_by_id",
        "find_complementary_products",
        "Field required" and "composer",
        "tool_calls",
        "function_calling",
    ]

    return any(indicator in error_str for indicator in tool_calling_indicators)


# Default retry prompt template
DEFAULT_RETRY_TEMPLATE = """
IMPORTANT: You must call the following tools that were missing from your previous response: {missing_tools}

Please ensure you call all required tools to complete the task properly. If you need to find products for a specific occasion or context, use the find_products_for_occasion tool.
"""
