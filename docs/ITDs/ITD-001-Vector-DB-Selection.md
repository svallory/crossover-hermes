# ITD-001: Vector Database Selection for Hermes PoC

**Date:** 2024-07-26
**Updated:** 2024-12-XX (Implementation Review)
**Author:** Gemini Assistant
**Status:** Implemented

## 1. Context

The Hermes project requires a vector database to implement the Retrieval-Augmented Generation (RAG) pattern for Task 3 (Handle Product Inquiry). The solution is a Proof-of-Concept (PoC) intended to run as a LangGraph-based workflow system, interacting with product/email data from CSV files and Google Sheets.

A key requirement from the notebook description is that the solution must scale to handle a potential catalog of **over 100,000 products** for the RAG task, without including the entire catalog in the LLM prompt.

The primary constraints and requirements are:

*   **Scalability:** Must handle 100,000+ product vector embeddings and metadata efficiently for similarity search.
*   **Local Development:** The database must be easily accessible from Python code running locally and in development environments.
*   **Ease of Setup & Use (PoC Focus):** Minimal configuration and simple API preferred for rapid PoC development.
*   **Cost:** Must be cost-effective for development and testing phases with ~100k-200k vectors.
*   **Core Functionality:** Ability to store vector embeddings and associated metadata, and perform efficient similarity searches.
*   **Integration:** Seamless integration with LangChain ecosystem and OpenAI embeddings.
*   **Persistence:** Support for persistent storage to avoid reindexing on every startup.

## 2. Options Considered

Based on common vector database solutions, the scalability requirement, and the need for easy local development:

1.  **ChromaDB:** Open-source, AI-native vector database with persistent storage capabilities.
2.  **FAISS:** Highly optimized similarity search library by Facebook.
3.  **Pinecone:** Fully managed vector database service.
4.  **Weaviate:** Open-source vector database with a managed cloud offering (WCS).
5.  **Qdrant:** Open-source vector database with a managed cloud offering.
6.  **Milvus:** Open-source vector database with a managed cloud offering (Zilliz Cloud).

## 3. Comparison

| Feature                           | ChromaDB (Local)                   | FAISS (Local)         | Pinecone (Managed)        | Weaviate (Managed - WCS) | Qdrant (Managed)  | Milvus (Managed - Zilliz) |
| :-------------------------------- | :--------------------------------- | :-------------------- | :------------------------ | :----------------------- | :---------------- | :------------------------ |
| **Type**                          | DB (OSS)                           | Library (OSS)         | Managed Service           | Managed Service          | Managed Service   | Managed Service           |
| **Local Development Suitability** | **High**                           | High                  | Medium (API Keys)         | Medium (API Keys)        | Medium (API Keys) | Medium (API Keys)         |
| **Persistent Storage**            | **Built-in**                       | Manual Implementation | **N/A (Hosted)**          | **N/A (Hosted)**         | **N/A (Hosted)**  | **N/A (Hosted)**          |
| **Ease of Use (PoC)**             | **Very High (Local)**              | Medium                | High                      | High                     | High              | Medium-High               |
| **Scalability (100k+ Vectors)**   | **High (Local)**                   | High (Local)          | **High**                  | High                     | High              | Very High                 |
| **Cost (Development)**            | **Free**                           | **Free**              | **Paid (Even Free Tier)** | Paid (Free Tier Limited) | Paid (Free Tier)  | Paid (Free Tier)          |
| **Metadata Handling**             | **Built-in**                       | Manual                | Built-in                  | Built-in                 | Built-in          | Built-in                  |
| **LangChain Integration**         | **Excellent (`langchain-chroma`)** | Good                  | Very Good                 | Good                     | Good              | Good                      |
| **Zero Configuration**            | **Yes**                            | No                    | No (API Keys)             | No (API Keys)            | No (API Keys)     | No (API Keys)             |

**Notes:**
*   For a PoC focused on rapid development and testing, local solutions provide faster iteration cycles without API key management or network dependencies.
*   ChromaDB offers excellent LangChain integration via the `langchain-chroma` package, making it trivial to integrate with OpenAI embeddings.
*   Persistent storage in ChromaDB eliminates the need to rebuild the vector index on every application startup.
*   The 100k+ vector requirement is easily handled by ChromaDB's local storage with modern hardware.
*   Zero configuration setup accelerates development without the overhead of account management, API quotas, or network latency.

## 4. Decision

**ChromaDB with persistent local storage** is selected as the vector database for the Hermes PoC.

## 5. Rationale

Given the requirement to handle 100,000+ product vectors and the need for rapid PoC development, ChromaDB provides the optimal balance for this implementation:

*   **Handles Scale:** Efficiently manages 100k+ vectors with persistent storage in the `./chroma_db` directory.
*   **Zero Configuration:** Works out-of-the-box without API keys, account setup, or network dependencies.
*   **Excellent LangChain Integration:** Native support via `langchain-chroma` package with seamless OpenAI embeddings integration.
*   **Persistent Storage:** Automatically persists vector embeddings and metadata, eliminating reindexing overhead.
*   **Development Velocity:** Enables fast iteration cycles for PoC development without external service dependencies.
*   **Cost Effective:** Completely free for development and testing phases.
*   **Simple Deployment:** Single directory (`./chroma_db`) contains entire vector database, simplifying backup and deployment.

The implementation uses:
```python
# Vector store configuration
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "products_catalog"
EMBEDDING_MODEL = "text-embedding-3-small"
```

While managed services like Pinecone excel for production deployments, ChromaDB's simplicity and zero-configuration setup make it ideal for PoC development where rapid iteration and minimal overhead are priorities.

## 6. Implementation Details

*   **Storage Location:** `./chroma_db` directory for persistent vector storage
*   **Collection Name:** `products_catalog` for product embeddings
*   **Embedding Model:** OpenAI `text-embedding-3-small` (1536 dimensions)
*   **LangChain Integration:** Uses `langchain-chroma` with `OpenAIEmbeddings`
*   **Global Caching:** Single vector store instance via `get_vector_store()` function
*   **Document Format:** Products stored as LangChain Documents with comprehensive metadata including product_id, name, category, stock, price, season, type, and description

## 7. Next Steps

*   ~~Add `chromadb` and `langchain-chroma` to the project's dependencies.~~ ✅ Complete
*   ~~Configure ChromaDB with persistent storage in `./chroma_db` directory.~~ ✅ Complete
*   ~~Implement the vector store initialization in `hermes/data/vector_store.py`.~~ ✅ Complete
*   ~~Integrate with product catalog loading and LangChain Documents.~~ ✅ Complete
*   ~~Implement RAG pipeline using ChromaDB for vector storage and retrieval.~~ ✅ Complete