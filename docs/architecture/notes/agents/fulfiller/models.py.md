## File: src/hermes/agents/fulfiller/models.py

This file defines the Pydantic models used for input and output of the Fulfiller agent (Order Processor).

**Models Defined:**

*   **`FulfillerInput(ClassifierInput)`:**
    *   Inherits from `ClassifierInput` (from `src.hermes.agents.classifier.models`), meaning it includes fields like `email_id`, `subject`, `message`.
    *   Adds a field:
        *   `classifier: ClassifierOutput`: This field holds the output from the Email Analyzer (Classifier agent). It's described as "The output of the email analyzer".
    *   **Purpose:** Represents the combined input needed for the Fulfiller agent, including the initial email data and the analysis performed by the classifier.

*   **`FulfillerOutput(BaseModel)`:**
    *   Defines a single field:
        *   `order_result: Order`: This field holds the `Order` object (from `src.hermes.model.order`) that results from processing the order request. It's described as "The complete result of processing the order request".
    *   **Purpose:** Represents the structured output of the Fulfiller agent, which is the processed order itself.

**Dependencies:**

*   `src.hermes.agents.classifier.models`: For `ClassifierInput` and `ClassifierOutput`.
*   `src.hermes.model.order`: For the `Order` model. 