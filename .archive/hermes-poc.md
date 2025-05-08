# Hermes Email Processing POC: Solution Overview

This document outlines the functionality and workflow of the `hermes-poc.py` script, a proof-of-concept for an automated email processing system. The system uses Large Language Models (LLMs) and a vector database (Pinecone) to categorize incoming emails, extract relevant information, match products, process orders or inquiries, and compose appropriate responses.

## 1. Setup and Configuration

The script begins by setting up necessary configurations:

*   **Environment Variables:** Loads API keys and settings for OpenAI and Pinecone, along with model names and other constants.
    *   `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`
    *   `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, `PINECONE_INDEX_NAME`
*   **Data Configuration:** Defines input Google Sheet ID, output Excel file name, and directories for prompts and supplementary documents.
*   **Client Initialization:**
    *   Initializes LangChain's `ChatOpenAI` model for LLM interactions and `OpenAIEmbeddings` for generating text embeddings.
    *   Error handling is in place for missing API keys.

## 2. Data Loading

The system loads various data sources:

*   **Google Sheets:**
    *   `products_df`: Reads product catalog data (ID, name, category, description, stock, price, season) from a Google Sheet. Performs type conversions and handles missing values.
    *   `emails_df`: Reads email data (ID, subject, message) from another Google Sheet.
*   **Inventory DataFrame:** Creates `inventory_df` from `products_df` for quick stock lookups and updates.
*   **Sales Guide:** Loads content from `sales-email-intelligence-guide.md` located in the `docs/` directory.
*   **Prompt Templates:**
    *   A helper function `load_prompt_template` reads prompt files from the `prompts/` directory.
    *   It dynamically injects the sales guide content and other runtime values (like email content or product catalogs) into the prompts.

## 3. Pydantic Models for Structured LLM Outputs

To ensure reliable and structured data from LLM calls, the script defines several Pydantic models. These models specify the expected schema for outputs from different processing agents. Examples include:

*   `ClassificationAgentOutput`: For email categorization and signal extraction.
*   `ProductMatcherAgentOutput`: For identifying products mentioned in emails.
*   `OrderProcessingAgentOutput`: For processing order requests and checking inventory.
*   `InquiryProcessingAgentOutput`: For handling product inquiries and suggesting alternatives/upsells.
*   `ComposedEmailOutput`: For the final structured email response.
*   `LLMError`: A model to capture errors from LLM calls.

## 4. Core Logic: LangGraph Workflow

The heart of the email processing is a stateful graph built using LangGraph. This graph defines a sequence of steps (nodes) and conditional transitions (edges) based on the processing state.

*   **State Definition (`AgentGraphState`):** A TypedDict that holds all relevant data as it flows through the graph, including the original email, outputs from each agent node, and any accumulated error messages.

*   **Agent Nodes:** Each node typically involves:
    1.  Loading a specific prompt template.
    2.  Injecting relevant data from the current state (e.g., email content, previous agent's output, product catalog snippets).
    3.  Calling an LLM using `call_llm_with_structured_output`, expecting a response conforming to a predefined Pydantic model.
    4.  Updating the graph state with the agent's output or any errors.

    The defined nodes are:
    *   `classification_signal_extraction_node`: Categorizes the email (e.g., "order request," "product inquiry") and extracts key signals.
    *   `product_matcher_node`: Identifies specific products mentioned, attempts to match them against the catalog, and distinguishes between items for order and items for inquiry.
    *   `order_processor_node`: For "order request" emails, processes order items, checks inventory, and determines fulfillment status.
    *   `inquiry_processor_node`: For "product inquiry" emails or orders with issues (e.g., out-of-stock), generates responses, suggests alternatives, and identifies upsell opportunities. Uses RAG (Retrieval Augmented Generation) via `query_pinecone_for_products` for enhanced information retrieval.
    *   `response_composer_node`: Takes all gathered information and outputs from previous nodes to compose a final email response (subject, greeting, body, signature).

*   **Conditional Edges:** Logic functions decide the next step in the workflow based on the output of the current node. For example:
    *   After classification, the flow might go to product matching or directly to response composition if the category doesn't require further product analysis.
    *   After product matching, it branches to order processing (for orders) or inquiry processing (for inquiries).
    *   If an order has items that couldn't be fulfilled, it might also go through inquiry processing to suggest alternatives.

## 5. Key Helper Functions

*   **`call_llm_with_structured_output`**: A wrapper for interacting with the LangChain `ChatOpenAI` model. It can enforce a Pydantic schema on the LLM's output, ensuring structured data, and handles retries and temperature adjustments.
*   **`get_langchain_embeddings`**: Generates embeddings for text lists using the configured `OpenAIEmbeddings` model.
*   **`prepare_embedding_text_for_product`**: Creates a standardized text representation of a product (name, description, category, season) for embedding.
*   **Pinecone Integration:**
    *   `initialize_pinecone`: Connects to Pinecone, creates the index (`PINECONE_INDEX_NAME`) if it doesn't exist.
    *   `populate_pinecone`: If the index is empty, it embeds product data (using `get_langchain_embeddings` and `prepare_embedding_text_for_product`) and upserts it into the Pinecone index. This allows for semantic search over products.
    *   `query_pinecone_for_products`: Takes a query text, embeds it, and queries the Pinecone index to find semantically similar products (used in RAG).
*   **`apply_inventory_updates_from_llm_decision`**: After the graph processes an order, this function updates the `inventory_df` based on the fulfilled quantities decided by the `order_processor_node`.

## 6. Main Processing Loop

The script iterates through emails loaded from `emails_df` (or a subset if `MAX_EMAILS_TO_PROCESS` is set). For each email:

1.  An initial `AgentGraphState` is prepared with the current email's data.
2.  The LangGraph `pipeline.invoke(initial_state_dict)` is called to process the email.
3.  Error handling is in place for critical failures during graph invocation.
4.  The final state from the graph is retrieved.
5.  Results are extracted:
    *   Email classification category.
    *   Order status details (if applicable).
    *   The composed email response.
6.  Inventory is updated by calling `apply_inventory_updates_from_llm_decision` with the `order_processing_output`.
7.  All relevant outputs and any errors encountered during graph execution are collected in lists.
8.  A small delay (`INDIVIDUAL_EMAIL_DELAY_SECONDS`) is introduced between processing emails.

## 7. Output Generation

After processing all emails:

1.  **Error Summary:** If any errors were logged, a summary is printed to the console.
2.  **Excel Output:**
    *   The collected results (email classifications, order statuses, order responses, inquiry responses) are converted into pandas DataFrames.
    *   These DataFrames are written to separate sheets in an Excel file (`OUTPUT_SPREADSHEET_NAME`).
    *   The script ensures that DataFrames have expected columns even if they are empty.
3.  **Final Inventory State:** The first 5 rows of the updated `inventory_df` are printed to show the impact of processed orders.

This structured approach allows for a modular and extensible system for handling complex email-based workflows. 