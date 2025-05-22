This file, `errors.py`, defines common Pydantic models used across the Hermes system to represent specific error conditions. Currently, it defines the `ProductNotFound` model.

Key model defined:
-   `ProductNotFound`: This model is designed to specifically signal that a product could not be located in the catalog during processing. It includes a descriptive `message` and optional fields (`query_product_id`, `query_product_name`) to provide context about the product that was being searched for.

Architecturally, this file promotes standardized error reporting within the system. By defining explicit error models like `ProductNotFound`, agents can communicate specific failure modes in a structured and type-safe manner. This is particularly useful in a workflow like Hermes, where different agents might encounter domain-specific errors (like a product not being found during the Stockkeeper's resolution process or the Fulfiller attempting to process an invalid product). Using these models allows downstream nodes or error handling mechanisms in the workflow graph to programmatically identify and react to specific error types, rather than relying solely on generic exceptions or unstructured error messages. This contributes to the robustness and maintainability of the system.

[Link to source file](../../../../src/hermes/model/errors.py) 