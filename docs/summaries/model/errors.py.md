This file, `errors.py`, defines common Pydantic models used across the Hermes system to represent specific error conditions. It provides standardized error structures that promote consistent error handling throughout the system.

Key models defined:
-   `Error`: A generic error model that provides a standardized structure for error responses across all agents in the system. It includes:
    - `message`: Primary error message describing what went wrong
    - `source`: Optional name of the agent or component that generated the error  
    - `details`: Optional additional context or technical details about the error
    
-   `ProductNotFound`: A specialized error model that signals when a product could not be located in the catalog during processing. It includes:
    - `message`: Explanation of why the product couldn't be found
    - `query_product_id`: The product ID that was searched for, if provided
    - `query_product_name`: The product name that was searched for, if provided

Architecturally, this file promotes standardized error reporting within the system. By defining explicit error models like `Error` and `ProductNotFound`, agents can communicate failure modes in a structured and type-safe manner. The generic `Error` class provides a consistent interface for all error responses, while specialized models like `ProductNotFound` allow for domain-specific error context. This is particularly useful in a workflow like Hermes, where different agents might encounter various error conditions. Using these models allows downstream nodes or error handling mechanisms in the workflow graph to programmatically identify and react to specific error types, rather than relying solely on generic exceptions or unstructured error messages. This contributes to the robustness and maintainability of the system.

[Link to source file](../../../src/hermes/model/errors.py) 