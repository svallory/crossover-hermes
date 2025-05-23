This file, `models.py`, defines the Pydantic data structures used by the Composer agent and within the overall workflow state to represent the Composer's input and output.

Key models include:
-   `ResponseTone`: An enumeration listing the possible tones the composed email response can take (e.g., `PROFESSIONAL`, `FRIENDLY`).
-   `ResponsePoint`: A structure representing a discrete piece of content intended for the final response body, with fields for type, content, priority, and optional related context (like a product ID). This allows for a more structured approach to building the response.
-   `ComposedResponse`: The central model representing the final output of the Composer agent. It encapsulates all aspects of the email to be sent, including `email_id`, `subject`, the main `response_body`, `language`, the selected `tone`, and a list of `ResponsePoint` objects.
-   `ComposerInput`: Defines the expected input structure for the Composer agent's processing function. It extends `ClassifierInput` and includes optional fields to receive the processed outputs from the Classifier, Advisor, and Fulfiller agents (`ClassifierOutput`, `AdvisorOutput`, `FulfillerOutput`). This model explicitly shows the dependencies of the Composer on upstream agents.
-   `ComposerOutput`: A simple wrapper model containing the `ComposedResponse`, defining the structure of the data returned by the Composer node in the workflow.

Architecturally, these models are critical for ensuring type safety and clarity in the data passed between the Composer agent and the rest of the workflow. They define the contracts for what data the Composer expects to receive and what data it will produce, facilitating the integration of this agent into the LangGraph pipeline. The `ComposedResponse` model specifically dictates the format of the final customer-facing output.

[Link to source file](../../../../src/hermes/agents/composer/models.py) 