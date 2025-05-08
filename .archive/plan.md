# Hermes Notebook Solver Plan

## Overview

This plan outlines the development of an AI-powered email processing system for a fashion store, implemented within the `hermes.ipynb` notebook. The core objective is to automatically handle incoming customer emails by classifying them, processing order requests, and responding intelligently to product inquiries. We will leverage the capabilities of the GPT-4o large language model via the OpenAI API, combined with established libraries and AI best practices to ensure an effective and scalable proof-of-concept. The process involves reading product catalog and email data from a Google Sheet, performing sequential tasks based on email content, and finally generating structured output in a separate Google Sheet.

The solution adheres to the requirements by employing specific AI techniques. Email classification (Task 1) and initial order item extraction (Task 2) will use direct prompting of GPT-4o for structured output. Order processing logic will handle stock checks and updates within a pandas DataFrame, simulating real-world inventory management. Crucially, for handling open-ended product inquiries (Task 3), we will implement a Retrieval-Augmented Generation (RAG) system. This involves embedding key product information (name, description, category, season) into a vector space using an appropriate model (like `sentence-transformers` or OpenAI embeddings) and storing it in a vector database (e.g., FAISS or ChromaDB). When an inquiry arrives, its embedding will be used to search the vector store for relevant product context, which is then fed into the GPT-4o prompt along with the original question, ensuring grounded and informative responses without exceeding token limits.

Throughout the implementation, we will utilize libraries such as `pandas` for data manipulation, `openai` for LLM interaction, potentially `langchain` or similar libraries to streamline the RAG pipeline, and `gspread`/`gspread-dataframe` for interacting with Google Sheets (assuming execution in Colab for authentication). Best practices will be followed, including clear code structure within the notebook cells, well-defined prompts for the LLM, careful management of the product stock state, and basic error handling for API calls. The final output will be organized into the specified sheets, demonstrating the system's ability to classify, process, and respond accurately.

## Technical Decisions (ITDs)

This section tracks key technical decisions made during the project.

*   **Completed:**
    *   [ITD-001: Vector Database Selection](./ITD-001-Vector-DB-Selection.md) - Decided on Pinecone for its scalability, suitable free tier, and ease of use in a Colab PoC context.
    *   [ITD-002: Embedding Model Selection](./ITD-002-Embedding-Model-Selection.md) - Decided on OpenAI `text-embedding-3-small` for its balance of performance, cost, and ease of integration.
    *   [ITD-003: Product Name/ID Mapping Strategy](./ITD-003-Product-Mapping-Strategy.md) - Decided on Direct LLM Extraction & Mapping (with Fuzzy Matching fallback).
    *   [ITD-004: RAG Orchestration Approach](./ITD-004-RAG-Orchestration-Approach.md) - Decided on Custom Implementation (No LangChain/LlamaIndex).
    *   [ITD-005: LLM Prompting Strategy](./ITD-005-LLM-Prompting-Strategy.md) - Established general principles and task-specific approaches for prompting.
    *   [ITD-005: Agent Architecture](./ITD-005-Agent-Architecture.md) - Proposed a 5-agent architecture for handling email processing.
    *   [ITD-006: Product Matching Implementation](./ITD-006-Product-Matching-Implementation.md) - Detailed implementation approach for product matching using fuzzy matching.
    *   [ITD-007: Pinecone Configuration](./ITD-007-Pinecone-Configuration.md) - Specified Pinecone index configuration and integration approach.
*   **Planned:**
    *(No remaining planned ITDs)*

## 1. Objective & Setup

*   **Goal:** Build an AI system using LLMs (GPT-4o) to classify emails (order vs. inquiry), process orders (check stock, update status), and answer product inquiries using RAG for a fashion store.
*   **Inputs:** Google Sheet with 'products' and 'emails' tabs.
*   **Outputs:** Code in `hermes.ipynb`, a Google Sheet with 'email-classification', 'order-status', 'order-response', 'inquiry-response' tabs.
*   **Setup:**
    *   Install required libraries: `openai`, `pandas`, `langchain`, `google-auth`, `gspread`, `gspread-dataframe`, a vector store library (e.g., `faiss-cpu` or `chromadb`), `sentence-transformers` (if using local embeddings), `pinecone-client` (per ITD-001), `thefuzz`, `python-Levenshtein` (per revised ITD-003).
    *   Configure `OpenAI` client (API key, base URL if needed).
    *   Configure `Pinecone` client (API key, environment).
    *   Implement `read_data_frame` function to load 'products' and 'emails' into DataFrames.
    *   Keep track of the `products_df` state, especially stock levels, as it changes during order processing.

## 2. Task 1: Email Classification

*   **Goal:** Classify emails as "product inquiry" or "order request".
*   **Method:**
    *   Iterate through `emails_df`.
    *   For each email, create a prompt for GPT-4o asking for classification based on subject/body. Use clear labels "product inquiry" or "order request".
    *   Example Prompt Idea:
        ~~~prompt
        Classify the following email based on its content. Respond with only "product inquiry" or "order request".

        Subject: {email_subject}
        Body: {email_body}

        Classification:
        ~~~
    *   Store results (email ID, category) in `email_classification_df`.

## 3. Task 2: Process Order Requests

*   **Filter:** Select emails classified as "order request".
*   **Sub-task 2.1: Process Orders (Update Stock & Status)**
    *   **Method:**
        *   For each order email:
            *   Use GPT-4o to extract product identifiers (mentions) and quantities from the email body. Request JSON output.
            *   Example Extraction Prompt Idea (Revised for ITD-003):
                ~~~prompt
                Extract the product mentions and quantities requested from the following email. Focus on capturing the name or description used by the customer. Respond in JSON format like [{"product_mention": "...", "quantity": ...}, ...]. If no items are found, respond with an empty list [].

                Email Body: {email_body}

                Requested Items:
                ~~~
            *   For each extracted item (`product_mention`, `quantity`):
                *   Use fuzzy matching (`thefuzz`) to map the `product_mention` to the best matching `products_df['name']` above a confidence threshold (e.g., 85).
                *   If match found, get the corresponding `product_id`. Status depends on stock check.
                *   If no confident match, status = `mapping_failed`.
                *   Check current stock in `products_df` for successfully mapped items.
                *   If `stock >= quantity`: status = "created", decrease stock in `products_df`.
                *   If `stock < quantity`: status = "out of stock", requested quantity is recorded.
                *   Append result (email ID, product ID, quantity, status) to `order_status_df`.
*   **Sub-task 2.2: Generate Order Responses**
    *   **Method:**
        *   For each processed order email:
            *   Gather the status of all items in the order (from `order_status_df` for that email ID).
            *   Create a prompt for GPT-4o to generate a professional response.
            *   Prompt should include:
                *   Customer email context (optional, maybe just the order details).
                *   Summary of order processing: items confirmed, items out of stock.
                *   Instructions: Write a professional confirmation/status update email. If OOS, mention it, apologize, and suggest alternatives (retrieve some options from `products_df` - perhaps similar category/season).
            *   Example Prompt Idea:
                ~~~prompt
                Generate a professional response email to the customer regarding their recent order request.

                Order Summary:
                - Item {product_name_1} (ID: {product_id_1}): {status_1} (Quantity: {quantity_1})
                - Item {product_name_2} (ID: {product_id_2}): {status_2} (Quantity: {quantity_2})
                ...

                Instructions:
                - If all items are 'created', confirm the order is processed.
                - If some items are 'out of stock', inform the customer which items are unavailable, apologize, and suggest waiting for restock or potentially offer alternatives like [Alternative Product 1 Name, Alternative Product 2 Name].
                - Maintain a professional and helpful tone.

                Email Response:
                ~~~
            *   Store result (email ID, response) in `order_response_df`.

## 4. Task 3: Handle Product Inquiry

*   **Filter:** Select emails classified as "product inquiry".
*   **Method (RAG):**
    *   **Embedding & Vector Store:**
        *   Choose text fields from `products_df` to embed (e.g., `name`, `description`, `category`, `season`). Concatenate them into a single text per product.
        *   Use the selected embedding model (OpenAI `text-embedding-3-small` per ITD-002) to create vectors for each product's text.
        *   Index these vectors and product metadata (product ID, name, etc.) in the selected vector store (Pinecone per ITD-001).
    *   **Retrieval & Generation:**
        *   For each inquiry email:
            *   Embed the inquiry (email body).
            *   Search the vector store for the top K most relevant product documents/chunks based on vector similarity.
            *   Create a prompt for GPT-4o including the original question and the *retrieved context* (snippets from relevant products).
            *   Instruct the LLM to answer the question *based only on the provided context* and maintain a helpful, professional tone suitable for customer interaction.
            *   Example Prompt Idea:
                ~~~prompt
                Answer the following customer question based *only* on the provided product information context. If the context does not contain the answer, politely state that the information is not available. Maintain a professional and helpful tone.

                Customer Question: {email_body}

                Relevant Product Information Context:
                ---
                Product: {product_name_1}
                Description: {product_description_1}
                Category: {product_category_1}
                ...
                ---
                Product: {product_name_2}
                Description: {product_description_2}
                Category: {product_category_2}
                ...
                ---

                Answer:
                ~~~
            *   Store result (email ID, response) in `inquiry_response_df`.

## 5. Output Generation

*   **Method:**
    *   Collect all generated DataFrames: `email_classification_df`, `order_status_df`, `order_response_df`, `inquiry_response_df`.
    *   Use the `gspread` library and authentication (likely requires running in Google Colab).
    *   Adapt the provided example code:
        *   Authenticate.
        *   Create a new Google Sheet.
        *   Create the four required worksheets with correct titles and headers.
        *   Use `gspread_dataframe.set_with_dataframe` to populate each sheet.
        *   Share the sheet publicly ('anyone' with 'reader' role).
        *   Print the shareable link.

## 6. Code Quality & Comments

*   Add comments explaining logic, especially for LLM interactions and RAG setup.
*   Structure the notebook clearly with headings for each task.
*   Ensure code is runnable and follows Python best practices.
*   Handle potential errors (e.g., API errors, data parsing issues).
*   Monitor token usage if using the limited key.

## 7. Additional Tasks Before Implementation

### 7.1 Architecture Finalization

*   **Goal:** Resolve discrepancy between 3-agent architecture in `plan.md` and 5-agent architecture in `ITD-005-Agent-Architecture.md`.
*   **Method:**
    *   Choose the simpler 3-prompt approach for the PoC:
        1. Classification & Signal Extraction prompt
        2. Order Processing prompt
        3. Inquiry Handling prompt (with RAG)
    *   Update documentation to reflect this decision.

### 7.2 Signal Extraction Enhancement

*   **Goal:** Enhance customer experience by extracting contextual signals.
*   **Method:**
    *   Add signal detection to the classification prompt
    *   Extract elements like:
        * Customer context/needs (e.g., "for my new job")
        * Emotional signals (e.g., "excited about", "disappointed with")
        * Time constraints (e.g., "need this by Friday")
    *   Pass these signals to response generation for personalization

### 7.3 Product Matching Implementation

*   **Goal:** Implement the tiered product matching approach.
*   **Method:**
    *   Build simple function implementing the 4-stage matching algorithm from ITD-006
    *   Test with sample product mentions from the dataset
    *   Integrate with order processing and inquiry handling

### 7.4 RAG Implementation

*   **Goal:** Implement RAG for product inquiries.
*   **Method:**
    *   Set up Pinecone index with configuration from ITD-007
    *   Create embedding pipeline for products
    *   Implement query function for inquiry prompts
    *   Format retrieved context for the LLM prompt 