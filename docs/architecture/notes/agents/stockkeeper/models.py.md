This file, `models.py`, defines the Pydantic data structures used by the Stockkeeper agent (Product Resolver) within the Hermes workflow. These models represent the expected input and the structured output of the Stockkeeper's processing logic.

Key models include:
-   `StockkeeperInput`: Defines the input structure for the Stockkeeper agent. It requires the `ClassifierOutput`, indicating that the Stockkeeper operates on the results of the initial email analysis, specifically relying on the identified `ProductMention` objects contained within.
-   `StockkeeperOutput`: Defines the output structure produced by the Stockkeeper agent. It contains three main fields:
    -   `resolved_products`: A list of `Product` objects that were successfully matched to product mentions in the email.
    -   `unresolved_mentions`: A list of `ProductMention` objects that the Stockkeeper could not confidently resolve to a product in the catalog.
    -   `metadata`: A dictionary for storing additional information about the resolution process.
    -   It also includes a `@property` `resolution_rate` to calculate the percentage of product mentions that were successfully resolved.

Architecturally, these models establish clear data contracts for the Stockkeeper agent. `StockkeeperInput` specifies its dependency on the Classifier's output, while `StockkeeperOutput` defines the structured format in which the Stockkeeper provides its results (resolved products and unresolved mentions) to subsequent agents in the workflow (like the Advisor or Fulfiller). This promotes modularity and ensures data consistency across the pipeline.

[Link to source file](../../../../src/hermes/agents/stockkeeper/models.py) 