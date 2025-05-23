This file, `prompts.py`, is responsible for defining and managing the large language model (LLM) prompt template specifically used by the Composer agent.

Its main component is `composer_prompt_template_str`, a detailed string template that provides comprehensive instructions to the LLM for generating the final customer email response. These instructions cover:
-   Analyzing the customer's original email for style, tone, and underlying intent.
-   Defining tone-matching guidelines to ensure the response tone is appropriate based on the customer's emotional state, aiming for a positive emotional shift.
-   Planning the structure of the response, including greetings, addressing inquiries/orders, and closings.
-   Detailing how to synthesize information from the outputs of the Classifier, Advisor, and Fulfiller agents.
-   Providing guidelines for composing a natural, personalized, complete, accurate, and helpful email in the customer's language.
-   Specifying the required format for the output, which is the `ComposedResponse` Pydantic model.

The file stores this template in a dictionary `PROMPTS`, keyed by `Agents.COMPOSER`, and includes a `get_prompt` function to retrieve it.

Architecturally, this file centralizes the "intelligence" and communication strategy for the Composer agent, translating the agent's role into explicit instructions for the underlying LLM. It is crucial for guiding the LLM's output to meet the specific requirements of composing effective customer service emails within the Hermes system, ensuring consistency in tone, structure, and information integration.

[Link to source file](../../../../src/hermes/agents/composer/prompts.py) 