# Prompts

This directory contains the prompt templates used by the various agents in the Hermes system. Careful prompt engineering is essential for ensuring that Language Models produce structured, high-quality outputs.

## Prompt Design Principles

Our prompts follow these key design principles:

1. **Task Clarity**: Each prompt clearly defines the agent's role, task, and expected output format.

2. **Few-Shot Examples**: Complex tasks include carefully selected examples to guide the model.

3. **Guardrails**: Specific instructions prevent common LLM issues (hallucination, verbosity, etc.)

4. **Structured Output**: Prompts direct the model to produce outputs in formats compatible with our Pydantic schemas.

5. **Chain-of-Thought**: For complex reasoning tasks, prompts encourage step-by-step thinking.

## Prompt Organization

Each agent has its own prompt file:

- **email_classifier.py**: Prompts for analyzing and classifying customer emails
- **order_processor.py**: Prompts for processing order requests and inventory
- **inquiry_responder.py**: Prompts for handling product inquiries using RAG
- **response_composer.py**: Prompts for generating natural customer responses

## Prompt Versioning Strategy

As we refine the system's performance, we track prompt improvements using Python's multiline strings and markdown comments. This allows us to maintain multiple prompt versions and document their evolution over time.

```python {cell}
# Here we'll define the prompt templates used by our Hermes agents.
# Each prompt is carefully engineered to ensure the LLM produces 
# structured, predictable outputs for our processing pipeline.
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
``` 