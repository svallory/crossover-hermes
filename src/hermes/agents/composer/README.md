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
- `compose_response.py`: Main function that orchestrates the response composition process

## Usage

The Response Composer should be the final agent in the pipeline, after the Email Analyzer and any applicable domain-specific agents (Inquiry Responder, Order Processor).

```python
from hermes.agents.response_composer import compose_response, ResponseComposerInput

# Create input from previous agent outputs
composer_input = ResponseComposerInput(
    email_analysis=email_analysis_result,
    inquiry_response=inquiry_response,  # Optional
    order_result=order_result  # Optional
)

# Generate the final response
response_output = await compose_response(composer_input)

# Access the composed response
final_response = response_output.composed_response
print(final_response.response_body)
```

## Response Structure

The composed response includes:

- **Subject Line**: An appropriate subject for the response email
- **Response Body**: The complete natural language response
- **Language**: Matches the customer's original language
- **Tone**: Adapts to the customer's communication style
- **Response Points**: Structured breakdown of the response elements

## Customization

The Response Composer can be customized by:

1. Modifying the prompt in `prompts.py` to change the response style or structure
2. Adjusting the temperature parameter in `compose_response.py` to control creativity
3. Extending the `ComposedResponse` model to include additional metadata 