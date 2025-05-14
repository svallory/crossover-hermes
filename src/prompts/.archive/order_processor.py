""" {cell}
## Order Processor Prompt

This module defines the prompt template used by the Order Processor Agent to:
1. Process order requests based on email analysis
2. Generate a structured output conforming to the OrderProcessingResult schema
3. Handle product references, check availability, and suggest alternatives

This prompt works with the with_structured_output() method to enforce output schema compliance.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from src.prompts.order_processor import (
    order_processor_md,
    order_processing_verification_md
)

# Create the prompt template using the markdown content
order_processor_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=order_processor_md.split("### USER REQUEST")[0].strip()),
    HumanMessage(content=order_processor_md.split("### USER REQUEST")[1].strip())
])

# Create verification prompt template
order_processing_verification_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessage(content=order_processing_verification_md.split("### USER REQUEST")[0].strip()),
    HumanMessage(content=order_processing_verification_md.split("### USER REQUEST")[1].strip())
])

""" {cell}
### Order Processor Prompt Implementation Notes

This prompt is designed to work with LangChain's structured output capabilities, generating an OrderProcessingResult directly from the LLM.

Key aspects:

1. **Structured Output Focus**: The prompt is designed to work with `with_structured_output(OrderProcessingResult)` to enforce schema compliance.

2. **Complete Process in One Step**: Rather than using multiple tool calls, the LLM processes the entire order in one step, with access to product catalog data.

3. **Clear Guidelines**: Provides explicit instructions for determining item status, calculating totals, and suggesting alternatives.

4. **Context-Aware Processing**: Uses the email analysis from the previous agent and product catalog data to make informed decisions.

This approach streamlines the order processing workflow by leveraging the LLM's ability to understand product references, match them to catalog items, and generate structured output in a single step.
""" 