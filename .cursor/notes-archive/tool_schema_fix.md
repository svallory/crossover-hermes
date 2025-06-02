# Tool Schema Fix for OpenAI API Compatibility

## Problem
OpenAI API was returning 400 Bad Request errors for LangChain tool definitions:

```
ERROR:hermes.utils.tool_error_handler:Unexpected error on attempt 1: Error code: 400 - {'error': {'message': "Invalid schema for function 'find_product_by_name': In context=(), 'required' is required to be supplied and to be an array including every key in properties. Missing 'threshold'.", 'type': 'invalid_request_error', 'param': 'tools[1].function.parameters', 'code': 'invalid_function_parameters'}}
```

## Root Cause
OpenAI's structured outputs feature requires **all fields to be marked as required** in the JSON schema when using `strict: true`. This is documented in their [structured outputs guide](https://platform.openai.com/docs/guides/structured-outputs/supported-schemas?api-mode=responses) under "All fields must be required".

The issue occurs because:
1. LangChain tools with default parameter values generate schemas where optional parameters are not included in the `required` array
2. OpenAI's structured outputs with `strict: true` enforces that ALL properties must be in the `required` array
3. This creates a mismatch between what LangChain generates and what OpenAI expects

## Solution
Following OpenAI's recommendation, we:
1. **Removed all default parameter values** from `@tool` decorated functions
2. **Changed optional parameter types** to union types with `None` (e.g., `int | None`)
3. **Added explicit None handling** inside each function with appropriate defaults
4. **Updated docstrings** to document the None behavior

### Functions Fixed:
1. `find_product_by_name` - `threshold` and `top_n` parameters
2. `find_complementary_products` - `limit` parameter
3. `search_products_with_filters` - `category`, `season`, `min_price`, `max_price`, `min_stock`, `top_k` parameters
4. `find_products_for_occasion` - `limit` parameter

### Example Fix:
```python
# Before (causing schema errors):
@tool(parse_docstring=True)
def find_product_by_name(
    *, product_name: str, threshold: float = 0.6, top_n: int = 5
) -> list[FuzzyMatchResult] | ProductNotFound:
    """Find products by name using fuzzy matching.

    Args:
        product_name: The product name to search for.
        threshold: Minimum similarity score. Defaults to 0.6.
        top_n: Maximum number of results. Defaults to 5.
    """

# After (OpenAI structured outputs compatible):
@tool(parse_docstring=True)
def find_product_by_name(
    *, product_name: str, threshold: float | None, top_n: int | None
) -> list[FuzzyMatchResult] | ProductNotFound:
    """Find products by name using fuzzy matching.

    Args:
        product_name: The product name to search for.
        threshold: Minimum similarity score. If None, defaults to 0.6.
        top_n: Maximum number of results. If None, defaults to 5.
    """
    # Handle None values with defaults
    if threshold is None:
        threshold = 0.6
    if top_n is None:
        top_n = 5
```

## Technical Details
- This ensures all parameters appear in the JSON schema's `required` array
- OpenAI's structured outputs can now properly validate the schema
- The LLM can still omit optional parameters by passing `null` values
- Function behavior remains identical to the original implementation

## References
- [OpenAI Structured Outputs Documentation](https://platform.openai.com/docs/guides/structured-outputs/supported-schemas)
- [OpenAI Community Discussion on Required Fields](https://community.openai.com/t/strict-true-and-required-fields/1131075)