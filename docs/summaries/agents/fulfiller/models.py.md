# Summary of src/hermes/agents/fulfiller/models.py

This file, `models.py`, defines the Pydantic data models used for the input and output of the Fulfiller agent (Order Processor) within the Hermes workflow.

Key components and responsibilities:
-   **`FulfillerInput(ClassifierInput)`:** This model defines the input structure for the Fulfiller agent. 
    -   It inherits from `ClassifierInput` (from `hermes.agents.classifier.models`), thereby including fields like `email_id`, `subject`, and `message` from the original email.
    -   It adds a crucial field: `classifier: ClassifierOutput`, which holds the structured output from the Email Analyzer (Classifier agent). This provides the Fulfiller with the segmented email and identified product mentions.
    -   It also requires `stockkeeper: StockkeeperOutput` (based on the Fulfiller agent logic and workflow graph), which provides the resolved product information from the Stockkeeper agent. This is essential for knowing which catalog products correspond to the customer's mentions.
-   **`FulfillerOutput(BaseModel)`:** This model defines the output structure of the Fulfiller agent.
    -   It contains a single field: `order_result: Order`, which holds an `Order` object (from `hermes.model.order`). This `Order` object represents the complete result of processing the customer's order request, including details of items, quantities, prices, statuses, and any applied promotions.

Architecturally, `models.py` for the Fulfiller agent establishes clear data contracts. `FulfillerInput` specifies its dependency on the outputs of both the Classifier and Stockkeeper agents. `FulfillerOutput` defines the structured format (`Order` model) in which the Fulfiller provides its results to the Composer agent for generating the final customer response. These models are crucial for maintaining data consistency and enabling the modular design of the Hermes workflow.

[Link to source file](../../../../src/hermes/agents/fulfiller/models.py) 