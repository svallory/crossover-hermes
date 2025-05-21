# Inquiry Responder Agent

## Overview

The Inquiry Responder Agent handles customer product inquiries by extracting questions from emails and providing factual, objective answers. This agent focuses solely on gathering and providing accurate product information, while leaving tone adaptation and final response composition to the Response Composer agent. This separation of concerns ensures clear responsibilities in the Hermes system.

## Core Capabilities

- **LLM-powered Question Extraction**: Uses advanced AI to identify questions in inquiry segments, beyond just sentences with question marks.
- **AI-based Question Classification**: Leverages the LLM to classify questions by type with contextual understanding.
- **Factual Product Information**: Provides objective information about products mentioned by customers.
- **Objective Question Answering**: Delivers factual answers without subjective language or personalized phrasing.
- **Related Product Identification**: Identifies functionally related products based on clear, objective criteria.
- **Missing Information Tracking**: Notes questions that cannot be answered with available data.

## Implementation Details

The agent consists of the following components:

- **inquiry_response.py**: The main entry point that processes inquiry requests and generates factual answers.
- **models.py**: Pydantic models defining the data structures used by the agent.
- **prompts.py**: LLM prompt templates used to generate factual responses.

## Input and Output

### Input
The agent requires only one input:

**Required input:**
- `email_analysis`: Complete `EmailAnalysisResult` from the Email Analyzer

The LLM uses this single input to:
- Extract the email ID
- Identify primary products directly from product mentions
- Extract and classify customer questions from inquiry segments
- Identify product references that couldn't be resolved
- Determine objectively related products

### Output
- The agent produces an `InquiryResponse` object containing:
  - Factual answers to customer questions
  - A list of unanswerable questions
  - Product information in an objective format
  - Related products identified by objective criteria

## Separation of Concerns

This agent intentionally focuses only on factual information extraction and answering, leaving several responsibilities to the Response Composer:

- **Inquiry Responder (This Agent)**
  - Extracts questions and product mentions
  - Provides factual, objective answers
  - Identifies related products by objective criteria
  - Tracks unanswerable questions

- **Response Composer (Separate Agent)**
  - Adapts tone to match customer communication style
  - Converts factual answers into customer-friendly language
  - Incorporates customer context and signals
  - Generates natural-sounding final responses
  - Handles customer objections and irrelevant information

## LLM-based Processing

This agent uses AI techniques for end-to-end factual processing:

1. The LLM extracts all necessary information from the EmailAnalysisResult
2. It identifies and classifies questions from inquiry segments
3. It provides factual answers based on available product information
4. It identifies objectively related products

## Usage Example

```python
from src.hermes.agents.advisor import respond_to_inquiry

# Create the input with EmailAnalysisResult
input_state = AdvisorInput(
    email_analysis=email_analysis_result  # From Email Analyzer
)

# Generate the factual response
response = await respond_to_inquiry(input_state, config)

# Access the factual answers
for qa in response.inquiry_response.answered_questions:
    print(f"Q: {qa.question}")
    print(f"A: {qa.answer}")
```

## Extensibility

The agent is designed to be extensible in several ways:
- The prompt can be adjusted to handle new types of questions
- Additional product attributes can be incorporated
- Answer types can be extended for different information categories 