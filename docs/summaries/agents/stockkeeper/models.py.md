# Summary of src/hermes/agents/stockkeeper/models.py

This file, `models.py`, defines the Pydantic data structures that specify the input and output for the Stockkeeper agent (also known as the Product Resolver) within the Hermes workflow.

Key components and responsibilities:
-   **`StockkeeperInput`**: This model defines the input structure required by the Stockkeeper agent.
    -   It mandates a `classifier: ClassifierOutput` field, indicating a direct dependency on the output of the Classifier agent. This `ClassifierOutput` contains the `EmailAnalysis`, which includes the list of `ProductMention` objects that the Stockkeeper needs to process.
-   **`StockkeeperOutput`**: This model defines the structured output produced by the Stockkeeper agent after it has attempted to resolve product mentions.
    -   `resolved_products: list[Product]`: A list of `Product` objects (presumably from `hermes.model.product`) that were successfully matched to product mentions from the input.
    -   `unresolved_mentions: list[ProductMention]`: A list of `ProductMention` objects that the Stockkeeper could not confidently resolve to a specific product in the catalog.
    -   `metadata: dict | None`: An optional dictionary for storing any additional metadata related to the resolution process (e.g., confidence scores, resolution methods used).
    -   It also features a useful `@property` named `resolution_rate`, which calculates the percentage of input product mentions that were successfully resolved into products.

Architecturally, `models.py` for the Stockkeeper agent establishes clear data contracts essential for modularity and data integrity within the Hermes pipeline. `StockkeeperInput` explicitly declares its reliance on the Classifier's output. `StockkeeperOutput` provides a well-defined structure for passing the results of product resolution—both successful matches and unresolved mentions—to downstream agents such as the Advisor (for inquiries) and the Fulfiller (for orders). This ensures that subsequent processing steps have access to accurate and consistently formatted product information.

[Link to source file](../../../../src/hermes/agents/stockkeeper/models.py) 