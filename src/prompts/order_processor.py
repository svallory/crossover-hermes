""" {cell}
## Order Processor Prompt

This module defines the prompt template used by the Order Processor Agent to:
1. Understand the context of an order request
2. Guide the use of inventory and product catalog tools
3. Generate a structured summary of the order processing results

While the core logic relies heavily on tool usage (check_stock, update_stock, find_alternatives), 
a prompt might be needed in complex scenarios, e.g., if the LLM needs to decide which 
tool to use or interpret ambiguous references *after* the initial analysis.

For this reference implementation, we focus on tool-driven logic for the Order Processor,
so a dedicated prompt for LLM processing within the agent is less critical.
However, we define a placeholder structure.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# Define the system message
order_processor_system_message = """
You are an efficient Order Processing Agent for a fashion retail store.
Your primary role is to process customer order requests based on the information provided 
by the Email Analyzer Agent and by using available tools to check stock, update inventory, 
and find alternatives.

You will receive the extracted product references and email analysis.
Your goal is to:
1. Resolve each product reference to a specific item in the catalog.
2. Check stock availability for the requested quantity.
3. If available, update the stock and confirm the item for the order.
4. If out of stock, find suitable alternatives.
5. Compile a final OrderProcessingResult summarizing the outcome.

Focus on using the provided tools accurately. You generally don't need to generate 
natural language, but you might need to interpret tool outputs or handle complex scenarios.
"""

# Define the human message template
order_processor_human_message = """
Email Analysis:
{email_analysis}

Product References:
{product_references}

Please process this order request using the available tools and compile the OrderProcessingResult.
Focus on accuracy of stock checks and updates.
"""

# Create the prompt template
order_processor_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=order_processor_system_message),
    HumanMessage(content=order_processor_human_message)
])
""" {cell}
### Order Processor Prompt Implementation Notes

While the Order Processor Agent in this reference solution relies heavily on direct tool calls and programmatic logic (`process_order_node` function), this prompt structure serves as a placeholder for potential future enhancements where an LLM might be more directly involved in the processing loop.

Key aspects:

1. **Tool-Centric Role**: The system message emphasizes the agent's role in using tools for stock checks, updates, and finding alternatives.

2. **Structured Input**: The human message template expects structured input from the Email Analyzer (`email_analysis`, `product_references`).

3. **Focus on Accuracy**: The prompt guides the agent (or potentially an LLM) to prioritize accurate inventory management.

4. **Limited LLM Requirement**: Acknowledges that in the current implementation, the LLM's role within this specific agent is limited, with most logic handled by Python code and tool interactions.

This placeholder prompt could be expanded with few-shot examples or more detailed instructions if the Order Processor's logic were to become more LLM-driven (e.g., for complex ambiguity resolution or multi-step decision making based on inventory status).
""" 