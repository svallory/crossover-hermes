# Summary of src/hermes/state.py

This file, `state.py`, defines the `HermesState` dataclass, which serves as the central, shared state object for the LangGraph-based email processing pipeline in the Hermes system. This state object is passed between different nodes (agents) in the workflow, accumulating data, agent outputs, and tracking errors as an email is processed.

Key components and responsibilities of `HermesState`:
-   **Dataclass Structure**: Defined as a Python `dataclass` for clear structure and type hinting.

-   **Input Email Data**: Stores the initial information from the incoming email:
    -   `email_id` (str): A unique identifier for the email being processed.
    -   `email_subject` (Optional[str]): The subject line of the email.
    -   `email_message` (str): The body/content of the email.

-   **Agent Outputs**: Contains fields to store the outputs from various agents as they process the email. These are typically stored as dictionaries within the LangGraph state, which agents then parse into their specific Pydantic output models.
    -   `email_analysis` (Optional[dict[str, Any]]): Stores the structured output from the Classifier agent (e.g., intent, product mentions, sentiment).
    -   `first_pass` (Optional[dict[str, Any]]): Noted as being added from an email analyzer agent in a notebook, likely holds initial processing results or a specific agent's output.
    -   `final_response` (Optional[str]): A placeholder for the final composed email response that will be sent back to the customer.

-   **LangGraph Message History**: 
    -   `messages` (Annotated[list[BaseMessage], add_messages]): This field is specifically designed for LangGraph. It accumulates a list of `BaseMessage` objects (e.g., `HumanMessage`, `AIMessage`) representing the conversational history or interactions between agents or between agents and LLMs. The `add_messages` annotation likely tells LangGraph how to update this field (by appending new messages).

-   **Error Tracking**:
    -   `errors` (list[str]): A list to accumulate error messages or structured error objects that occur during processing by any agent in the pipeline.

-   **Metadata**:
    -   `metadata` (dict[str, Any]): A flexible dictionary to store any other relevant metadata that might be useful for tracking, debugging, or extending the state with custom information without altering the core fields.

-   **Shared Resources**: Provides access to shared resources that agents might need. These are marked with `repr=False` to prevent large data structures from being printed when the state object is represented as a string (e.g., in logs).
    -   `product_catalog_df` (Optional[pd.DataFrame]): A pandas DataFrame containing the product catalog. This allows agents to access product information directly.
    -   `vector_store` (Optional[Any]): A reference to the vector store client (e.g., ChromaDB instance). This allows agents like the Stockkeeper or Advisor to perform semantic searches for products.

Architecturally, `HermesState` is the backbone of the LangGraph workflow in Hermes. It embodies the shared memory or context that evolves as an email passes through different processing stages (agents). By centralizing all relevant data—from initial input to intermediate agent outputs, shared resources, and error logs—it enables complex, multi-step processing pipelines. The design allows agents to operate somewhat independently, reading necessary information from the state and writing their results back to it. The inclusion of `messages` and `errors` fields provides built-in support for conversational history and robust error handling within the LangGraph framework. The use of optional fields and dictionaries for agent outputs offers flexibility in how agents contribute to the state.

[Link to source file](../../../src/hermes/state.py) 