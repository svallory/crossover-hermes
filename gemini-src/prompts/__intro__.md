# Prompts for Hermes Agents

This section details the prompt engineering strategy and the specific prompts used by the various agents in the Hermes email processing system. Effective prompt design is critical for eliciting the desired behavior, accuracy, and tone from Large Language Models (LLMs).

## Prompt Design Philosophy

The prompts for Hermes agents are designed with the following principles in mind, aligning with the guidance in `reference-solution-spec.md` and best practices for LLM interaction:

1.  **Clarity and Specificity**: Prompts are written to be as clear and unambiguous as possible, precisely defining the task, the expected output format, and any constraints.
2.  **Role Playing**: System messages often assign a role to the LLM (e.g., "You are an expert email analyst for a fashion retail company") to help guide its responses and behavior.
3.  **Structured Output**: For tasks requiring specific data extraction or classification, prompts instruct the LLM to provide output in a structured format (e.g., JSON that can be parsed into Pydantic models). This is crucial for reliable integration with the rest of the system. LangChain's `create_structured_output_chain` or similar mechanisms are leveraged where appropriate.
4.  **Few-Shot Examples**: For complex tasks, particularly classification or nuanced interpretation, prompts may include few-shot examples. These examples demonstrate the desired input-output behavior and help the LLM generalize better. These examples are stored as Python variables for type safety and ease of integration.
5.  **Contextual Information**: Prompts are designed to dynamically incorporate relevant contextual information, such as the customer's email content, product details (retrieved via RAG), or signals detected in previous steps.
6.  **Tone and Persona**: For response generation, prompts guide the LLM on the desired tone (e.g., professional, empathetic, friendly) and persona (e.g., a helpful customer service representative).
7.  **Use of `ChatPromptTemplate`**: All prompts are constructed using LangChain's `ChatPromptTemplate`, typically consisting of a `SystemMessagePromptTemplate` and a `HumanMessagePromptTemplate`. This provides a standardized way to structure conversations with the LLM.
8.  **Python Variables for Prompts**: Prompts are defined as Python variables (e.g., instances of `ChatPromptTemplate`) within their respective modules (e.g., `src/prompts/email_classifier.py`). This approach is preferred over markdown prompt files for better type safety, version control, and integration with the Python codebase.
9.  **Iterative Refinement**: Prompt engineering is an iterative process. The prompts provided are a starting point and would typically be refined through testing and evaluation with various email examples.

## Organization of Prompts

Prompts are organized into separate Python files within the `src/prompts/` directory, with one file per agent that requires specific prompting. This modular structure ensures that prompts are co-located with the agent logic they support or are easily referenced:

-   `email_classifier.py`: Contains prompts for the `Email Analyzer Agent`, focusing on email classification, language/tone detection, product reference extraction, and customer signal identification.
-   `order_processor.py`: May contain prompts if the `Order Processor Agent` needs LLM assistance for complex decision-making beyond tool use (e.g., interpreting ambiguous order details, though this is often handled by structured data extraction from the Email Analyzer).
-   `inquiry_responder.py`: Includes prompts for the `Inquiry Responder Agent`, particularly for synthesizing answers from RAG-retrieved product information and customer questions.
-   `response_composer.py`: Houses prompts for the `Response Composer Agent`, guiding the generation of the final customer-facing email, incorporating all necessary information, and adhering to the desired tone and style.

The subsequent files in this directory will provide the concrete implementations of these prompts.

```python
# This is a placeholder Python cell that might be used for initial imports or setup
# when the notebook is assembled for the prompts section.
print("Hermes Solution Notebook - Prompts Introduction Loaded")
``` 