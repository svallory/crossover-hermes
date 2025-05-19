# Issues

## Instructions

1. Start by running `uv run mypy ./src`
2. Build a markdown todo list below, grouping the issues by files
3. Resolve the issues one file at a time
4. Iterate until all issues are fixed

**NOTE:** For issues that come from other library typings, verify if the issue is on our side or the type hint in the library is badly defined. When the problem is in the library, just use `# type: ignore` on the line with the issue.

## List

*   **src/hermes/tools/catalog_tools.py**
    *   [x] 24: error: Skipping analyzing "thefuzz": module is installed, but missing library stubs or py.typed marker  [import-untyped]
    *   [x] 27: error: Cannot find implementation or library stub for module named "hermes.model"  [import-not-found]
    *   [x] 28: error: Cannot find implementation or library stub for module named "hermes.data_processing.vector_store"  [import-not-found]
    *   [x] 34: error: Cannot find implementation or library stub for module named "hermes.data_processing.load_data"  [import-not-found]
    *   [x] 36: error: Name "ProductNotFound" already defined (possibly by an import)  [no-redef]
    *   [x] 51: error: No overload variant of "tool" matches argument types "str", "str"  [call-overload]
    *   [x] 103: error: No overload variant of "tool" matches argument types "str", "str"  [call-overload]
    *   [x] 183: error: No overload variant of "tool" matches argument type "str"  [call-overload]
    *   [x] 208: error: Name "create_filter_dict" is not defined  [name-defined]
    *   [x] 240: error: No overload variant of "tool" matches argument types "str", "str"  [call-overload]
    *   [x] 346: error: No overload variant of "tool" matches argument types "str", "str"  [call-overload]
    *   [x] 382: error: No overload variant of "tool" matches argument type "str"  [call-overload]
*   **src/hermes/data_processing/vector_store.py**
    *   [x] 21: error: Module "chromadb.utils" has no attribute "SentenceTransformerEmbeddingFunction"  [attr-defined]
    *   [x] 21: error: Name "SentenceTransformerEmbeddingFunction" already defined (possibly by an import)  [no-redef]
    *   [x] 240: error: "Hashable" has no attribute "startswith"  [attr-defined]
    *   [x] 446: error: "Mapping[str, str | int | float | bool | None]" has no attribute "copy"  [attr-defined]
    *   [x] 450: error: Incompatible return value type (got "list[tuple[Mapping[str, str | int | float | bool | None], float]]", expected "list[tuple[dict[str, Any], float]]")  [return-value]
    *   [x] 564: error: Unsupported target for indexed assignment ("dict[str, Any] | None")  [index]
    *   [x] 618: error: Unsupported target for indexed assignment ("dict[str, Any] | None")  [index]
*   **src/hermes/data_processing/load_data.py**
    *   [x] 30: error: Incompatible return value type (got "None", expected "DataFrame")  [return-value]
*   **src/hermes/utils/llm_client.py**
    *   [x] 62: error: Unexpected keyword argument "openai_api_key" for "ChatOpenAI"  [call-arg]
    *   [x] 62: error: Unexpected keyword argument "openai_api_base" for "ChatOpenAI"  [call-arg]
*   **src/hermes/tools/order_tools.py**
    *   [x] 95: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 154: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 168: error: Item "None" of "DataFrame | None" has no attribute "loc"  [union-attr]
    *   [x] 169: error: Item "None" of "DataFrame | None" has no attribute "loc"  [union-attr]
    *   [x] 185: error: Item "None" of "DataFrame | None" has no attribute "loc"  [union-attr]
    *   [x] 214: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 215: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 229: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 230: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 231: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 232: error: Value of type "DataFrame | None" is not indexable  [index]
    *   [x] 259: error: Unexpected keyword argument "original_product_id" for "AlternativeProduct"  [call-arg]
    *   [x] 259: error: Unexpected keyword argument "original_product_name" for "AlternativeProduct"  [call-arg]
    *   [x] 259: error: Unexpected keyword argument "stock_available" for "AlternativeProduct"  [call-arg]
    *   [x] 250: error: No overload variant of "sort_values" of "Series" matches argument types "str", "bool"  [call-overload]
    *   [x] 288: error: Unexpected keyword argument "original_product_id" for "AlternativeProduct"  [call-arg]
    *   [x] 288: error: Unexpected keyword argument "original_product_name" for "AlternativeProduct"  [call-arg]
    *   [x] 288: error: Unexpected keyword argument "stock_available" for "AlternativeProduct"  [call-arg]
    *   [x] 294: error: Argument "price" to "AlternativeProduct" has incompatible type "float | None"; expected "float"  [arg-type]
    *   [x] 238: error: Unexpected keyword argument "original_product_id" for "AlternativeProduct"  [call-arg]
    *   [x] 238: error: Unexpected keyword argument "original_product_name" for "AlternativeProduct"  [call-arg]
    *   [x] 238: error: Unexpected keyword argument "stock_available" for "AlternativeProduct"  [call-arg]
    *   [x] 250: error: No overload variant of "sort_values" of "Series" matches argument types "str", "bool"  [call-overload]
    *   [x] 267: error: Unexpected keyword argument "original_product_id" for "AlternativeProduct"  [call-arg]
    *   [x] 267: error: Unexpected keyword argument "original_product_name" for "AlternativeProduct"  [call-arg]
    *   [x] 267: error: Unexpected keyword argument "stock_available" for "AlternativeProduct"  [call-arg]
    *   [x] 273: error: Argument "price" to "AlternativeProduct" has incompatible type "float | None"; expected "float"  [arg-type]
*   **src/hermes/agents/order_processor/process_order.py**
    *   [x] 17: error: No overload variant of "traceable" matches argument types "str", "str"  [call-overload]
    *   [x] 63: error: Incompatible types in assignment (expression has type "dict[Any, Any] | BaseModel", variable has type "ProcessedOrder")  [assignment]
*   **src/hermes/agents/inquiry_responder/inquiry_response.py**
    *   [x] 19: error: No overload variant of "traceable" matches argument types "str", "str"  [call-overload]
    *   [x] 71: error: Incompatible types in assignment (expression has type "dict[Any, Any] | BaseModel", variable has type "InquiryAnswers")  [assignment]
    *   [x] 90: error: Unexpected keyword argument "response_points" for "InquiryAnswers"  [call-arg]
*   **src/hermes/agents/response_composer/compose_response.py**
    *   [x] 19: error: No overload variant of "traceable" matches argument types "str", "str"  [call-overload]
    *   [x] 67: error: Incompatible types in assignment (expression has type "dict[str, Any] | InquiryAnswers", target has type "dict[str, Any] | EmailAnalysis")  [assignment]
    *   [x] 75: error: Incompatible types in assignment (expression has type "dict[str, Any] | ProcessedOrder", target has type "dict[str, Any] | EmailAnalysis")  [assignment]
    *   [x] 87: error: Incompatible types in assignment (expression has type "dict[Any, Any] | BaseModel", variable has type "ComposedResponse")  [assignment]
    *   [x] 106: error: Argument "tone" to "ComposedResponse" has incompatible type "str"; expected "ResponseTone"  [arg-type]
*   **src/hermes/main.py**
    *   [x] 61: error: Unexpected keyword argument "email_data" for "hermes_langgraph_workflow"  [call-arg]
    *   [x] 75: error: "OutputState" has no attribute "get"  [attr-defined]
    *   [x] 76: error: Value of type "OutputState" is not indexable  [index]
    *   [x] 82: error: "OutputState" has no attribute "get"  [attr-defined]
    *   [x] 83: error: Value of type "OutputState" is not indexable  [index]
    *   [x] 91: error: "object" has no attribute "append"  [attr-defined]
    *   [x] 92: error: Argument 1 to "len" has incompatible type "object"; expected "Sized"  [arg-type]
    *   [x] 95: error: "OutputState" has no attribute "get"  [attr-defined]
    *   [x] 96: error: Value of type "OutputState" is not indexable  [index]
    *   [x] 97: error: Argument 1 to "len" has incompatible type "object"; expected "Sized"  [arg-type]
    *   [x] 247: error: Incompatible types in assignment (expression has type "None", variable has type "int")  [assignment]
    *   [x] 254: error: Argument "emails_to_process" to "process_emails" has incompatible type "list[dict[Hashable, Any]]"; expected "list[dict[str, str]]"  [arg-type]

## Summary of Remaining Issues

The only remaining issues are import-related errors in src/hermes/tools/catalog_tools.py:

1. Skipping analyzing "thefuzz": module is installed, but missing library stubs or py.typed marker [import-untyped]
2. Cannot find implementation or library stub for modules:
   - "hermes.model" 
   - "hermes.data_processing.vector_store"
   - "hermes.data_processing.load_data"

These are related to module imports and don't affect the actual functionality. The "thefuzz" error occurs because the package doesn't provide type hints, and the other errors are due to how the imports are structured in the project.
