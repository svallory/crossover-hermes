# ITD-004: RAG Orchestration Approach for Hermes PoC

**Date:** 2024-07-26
**Author:** Gemini Assistant
**Status:** Proposed

## 1. Context

Task 3 (Handle Product Inquiry) requires implementing a Retrieval-Augmented Generation (RAG) system. This involves:
1.  Taking a customer's email inquiry.
2.  Embedding the inquiry text (using OpenAI `text-embedding-3-small`, per ITD-002).
3.  Searching the product vector database (Pinecone, per ITD-001) for relevant product information.
4.  Constructing a prompt for the LLM (GPT-4o) that includes the original inquiry and the retrieved product context.
5.  Generating a final response based on the inquiry and context.

We need to decide how to orchestrate these steps: use a dedicated framework/library or implement the logic directly.

## 2. Requirements

*   **Functionality:** Must correctly implement the retrieve-generate sequence.
*   **Integration:** Work smoothly with the chosen components: Pinecone client, OpenAI client, pandas DataFrames.
*   **Simplicity (PoC Focus):** Prioritize a straightforward implementation suitable for a proof-of-concept within a Jupyter notebook.
*   **Control & Transparency:** Allow clear visibility and control over each step (embedding, retrieval parameters, prompt construction, LLM call).
*   **Maintainability:** Code should be easy to understand and modify.
*   **Minimal Dependencies:** Avoid adding large or complex libraries unless they offer significant advantages for the PoC's scope.

## 3. Options Considered

1.  **Custom Implementation:**
    *   **Method:** Write Python code to explicitly perform each step: call OpenAI for query embedding, call Pinecone client for search, format the retrieved context and query into a string prompt, call OpenAI client for generation.
    *   **Pros:** Full control over every step, maximum transparency, no additional library dependencies, potentially simpler for a well-defined, single RAG pipeline.
    *   **Cons:** Requires writing boilerplate code for the sequence, less reusable if multiple complex chains were needed (not the case here).

2.  **LangChain Framework:**
    *   **Method:** Use LangChain's abstractions (`VectorStoreRetriever`, `ChatPromptTemplate`, `RunnableSequence` or LCEL) to define and execute the RAG pipeline.
    *   **Pros:** Provides pre-built components for RAG, potentially less boilerplate for complex chains, promotes a standard structure.
    *   **Cons:** Introduces a significant dependency (`langchain`, `langchain-openai`, `langchain-pinecone`), adds a layer of abstraction that might obscure details, can have a steeper learning curve for its specific patterns, potentially overkill for a single, straightforward RAG task.

3.  **LlamaIndex Framework:**
    *   **Method:** Similar to LangChain, use LlamaIndex's tools for data indexing, defining retrievers, and query engines.
    *   **Pros:** Strong focus on data indexing and retrieval aspects of RAG.
    *   **Cons:** Similar to LangChain - adds a major dependency, abstraction layer, and potential complexity for this specific PoC scope.

## 4. Comparison

| Feature             | Custom Implementation | LangChain        | LlamaIndex       |
| :------------------ | :------------------ | :--------------- | :--------------- |
| **Control**         | **High**            | Medium           | Medium           |
| **Transparency**    | **High**            | Medium-Low       | Medium-Low       |
| **Simplicity (PoC)**| **High**            | Medium           | Medium           |
| **Dependencies**    | **Minimal**         | High             | High             |
| **Boilerplate**     | Medium              | Low (Potentially)| Low (Potentially)|
| **Learning Curve**  | Low                 | Medium           | Medium           |
| **Flexibility**     | High                | High             | High             |

## 5. Decision

**Option 1: Custom Implementation** is selected for orchestrating the RAG pipeline in Task 3.

## 6. Rationale

For this specific PoC, where we need to implement one primary RAG pipeline with already chosen components (OpenAI, Pinecone), a custom implementation offers the best balance of simplicity, control, and transparency.

*   **Simplicity & Clarity:** Directly using the `openai` and `pinecone-client` libraries for their respective tasks (embedding, search, generation) makes the flow explicit and easy to follow within the notebook context. It avoids introducing the conceptual overhead and potential complexities of a large framework like LangChain or LlamaIndex for a single-use case.
*   **Minimal Dependencies:** This approach avoids adding heavy dependencies, keeping the PoC environment cleaner.
*   **Sufficient for Scope:** The required RAG logic (embed query -> search -> format prompt -> generate) is straightforward enough that the benefits of a framework's pre-built chains do not outweigh the cost of adding and learning the framework for this PoC.

While LangChain/LlamaIndex are powerful for building complex LLM applications, they are not strictly necessary here and might add unnecessary layers for this specific task.

## 7. Next Steps

*   Implement the RAG logic in Task 3 by directly using:
    *   The `openai` client to embed the inquiry.
    *   The `pinecone` client to perform similarity search against the product index.
    *   Standard Python string formatting to construct the final prompt including retrieved context.
    *   The `openai` client to generate the final response.
*   Update `plan.md` to reflect this decision. 