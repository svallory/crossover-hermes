# Response Composer Agent

## Overview

The Response Composer Agent is the final component in the Hermes email processing pipeline. It takes the outputs from the previous agents (Email Analyzer, Inquiry Responder, and Order Processor) and composes a natural, personalized response that will be sent to the customer.

## Purpose

The primary purpose of this agent is to:

1. Generate natural-sounding, personalized responses that address all customer inquiries and order requests
2. Adapt tone and style to match the customer's communication patterns
3. Ensure all questions and order aspects are properly addressed
4. Provide a consistent, high-quality customer experience

## Components

- `models.py`: Defines the data models used by the Response Composer
- `prompts.py`: Contains the prompt template for the LLM
- `agent.py`: Main function that orchestrates the response composition process

## Usage

The Response Composer should be the final agent in the pipeline, after the Email Analyzer and any applicable domain-specific agents (Inquiry Responder, Order Processor).

```python
from hermes.agents.composer import run_composer, ComposerInput

# Create input from previous agent outputs
composer_input = ComposerInput(
    email_id="E001",
    subject="Customer Inquiry",
    message="Original email content",
    classifier=classifier_output,
    advisor=advisor_output,  # Optional
    fulfiller=fulfiller_output  # Optional
)

# Generate the final response
response_output = await run_composer(composer_input)

# Access the composed response directly
final_response = response_output.data
print(final_response.response_body)
print(final_response.subject)
```

## Response Structure

The composed response (ComposerOutput) includes:

- **email_id**: The ID of the email being responded to
- **subject**: An appropriate subject line for the response email
- **response_body**: The complete natural language response (written in the language detected by the classifier)
- **tone**: Descriptive tone that captures the response style (e.g., "professional and warm", "friendly and enthusiastic")
- **response_points**: Structured breakdown of response elements (used internally for LLM reasoning)

The composer automatically writes the response in the language detected by the classifier agent, eliminating the need for a separate language field in the output.

## Model Simplification

The composer models have been simplified for better maintainability:

- **Flattened Structure**: `ComposerOutput` now contains response fields directly instead of wrapping a separate `ComposedResponse` model
- **Flexible Tone**: The tone field is now a free-form string allowing rich descriptions like "professional and empathetic" rather than being constrained to an enum
- **Internal Reasoning**: `ResponsePoint` is documented as an internal LLM reasoning tool, not used elsewhere in the system

## Customization

The Response Composer can be customized by:

1. Modifying the prompt in `prompts.py` to change the response style or structure
2. Adjusting the temperature parameter in `agent.py` to control creativity
3. Extending the `ComposerOutput` model to include additional metadata