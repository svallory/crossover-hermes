# ITD-001: Vector Database Selection for Hermes PoC

**Date:** 2024-07-26
**Author:** Gemini Assistant
**Status:** Accepted

## 1. Context

The Hermes project requires a vector database to implement the Retrieval-Augmented Generation (RAG) pattern for Task 3 (Handle Product Inquiry). The solution is a Proof-of-Concept (PoC) intended to run primarily within the Google Colaboratory (Colab) environment, interacting with product/email data from Google Sheets.

A key requirement from the notebook description is that the solution must scale to handle a potential catalog of **over 100,000 products** for the RAG task, without including the entire catalog in the LLM prompt.

The primary constraints and requirements are:

*   **Scalability:** Must handle 100,000+ product vector embeddings and metadata efficiently for similarity search.
*   **Colab Integration:** The database must be easily accessible from Python code running in Google Colab.
*   **Ease of Setup & Use (PoC Focus):** Minimal configuration and simple API preferred for rapid PoC development.
*   **Cost:** Must have a free tier suitable for storing and querying ~100k-200k vectors for the duration of the PoC.
*   **Core Functionality:** Ability to store vector embeddings and associated metadata, and perform efficient similarity searches.
*   **Open Source / Managed:** Either an easy-to-use OSS library *if* runnable within Colab limits *or* a managed service with a suitable free tier.

## 2. Options Considered

Based on common vector database solutions, the scalability requirement, and the possibility of using hosted free tiers accessible from Colab:

1.  **ChromaDB:** Open-source, AI-native vector database. Also potentially has hosted options.
2.  **FAISS:** Highly optimized similarity search library.
3.  **Pinecone:** Fully managed vector database service.
4.  **Weaviate:** Open-source vector database with a managed cloud offering (WCS).
5.  **Qdrant:** Open-source vector database with a managed cloud offering.
6.  **Milvus:** Open-source vector database with a managed cloud offering (Zilliz Cloud).

## 3. Comparison

| Feature                 | ChromaDB (Local) | FAISS (Local) | Pinecone (Managed) | Weaviate (Managed - WCS) | Qdrant (Managed) | Milvus (Managed - Zilliz) |
| :---------------------- | :--------------- | :------------ | :----------------- | :----------------------- | :--------------- | :------------------------ |
| **Type**                | DB (OSS)         | Library (OSS) | Managed Service    | Managed Service          | Managed Service  | Managed Service           |
| **Colab Suitability (Client)** | High             | High          | **High**           | High                     | High             | High                      |
| **Colab Suitability (DB @ 100k+ Vectors)** | **Low** (RAM Limit)| **Low** (RAM Limit)| **N/A (Hosted)**   | **N/A (Hosted)**         | **N/A (Hosted)** | **N/A (Hosted)**          |
| **Ease of Use (PoC)** | High (Local)     | Medium        | **Very High**      | High                     | High             | Medium-High               |
| **Scalability (100k+ Vectors)** | Low (Local)    | Low (Local)   | **High**           | High                     | High             | Very High                 |
| **Hosted Free Tier (PoC Scale)** | ? (Less Common) | N/A           | **Yes (Typically Sufficient)** | Yes (Check Limits)       | Yes (Often Generous) | Yes (Check Limits)        |
| **Metadata Handling**   | Built-in         | Manual        | Built-in           | Built-in                 | Built-in         | Built-in                  |
| **LLM Framework Int.**  | Good             | Core          | Very Good          | Good                     | Good             | Good                      |
| **Reference**           | [Chroma Docs](https://docs.trychroma.com/), [lakefs.io](https://lakefs.io/blog/12-vector-databases-2023/) | [FAISS GH](https://github.com/facebookresearch/faiss) | [Pinecone Docs](https://docs.pinecone.io/), [lakefs.io](https://lakefs.io/blog/12-vector-databases-2023/) | [Weaviate Docs](https://weaviate.io/developers/weaviate), [lakefs.io](https://lakefs.io/blog/12-vector-databases-2023/) | [Qdrant Docs](https://qdrant.tech/documentation/), [Medium](https://medium.com/tech-ai-made-easy/vector-database-comparison-pinecone-vs-weaviate-vs-qdrant-vs-faiss-vs-milvus-vs-chroma-2025-15bf152f891d) | [Milvus Docs](https://milvus.io/docs), [lakefs.io](https://lakefs.io/blog/12-vector-databases-2023/) |

**Notes:**
*   The 100k+ vector requirement makes running the database *locally* within Colab free tier (using ChromaDB in-memory or FAISS) highly impractical due to RAM limitations.
*   Hosted solutions with free tiers accessible from Colab are the most viable approach.
*   Pinecone, Weaviate Cloud, Qdrant Cloud, and Zilliz Cloud all offer potential free tiers.
*   Pinecone often stands out for its focus on ease of use and managed simplicity, ideal for quickly setting up a PoC.
*   Qdrant is also a strong candidate, noted for performance and often a generous free tier.
*   Weaviate and Milvus (via Zilliz) are powerful but might involve slightly more complexity compared to Pinecone for a basic PoC setup.

## 4. Decision

**Pinecone** is selected as the vector database for the Hermes PoC.

## 5. Rationale

Given the requirement to handle 100,000+ product vectors and the practical limitations of the Colab free tier, a hosted vector database with a suitable free tier is necessary. Pinecone provides the best balance for this PoC:

*   **Handles Scale:** Easily manages 100k+ vectors.
*   **Suitable Free Tier:** Pinecone's free tier typically accommodates the scale needed for this PoC (vector count, dimensionality - *subject to checking current terms*).
*   **Ease of Use:** Offers a very simple Python client API and abstracts away infrastructure management, accelerating PoC development from Colab.
*   **Managed Service:** No need to manage database setup or resources directly.
*   **Good Ecosystem Integration:** Well-integrated with Python and common LLM tools.

While Qdrant and Weaviate are strong alternatives, Pinecone's emphasis on simplicity makes it slightly preferable for minimizing setup time in this PoC context.

## 6. Next Steps

*   Add `pinecone-client` to the project's dependencies (`%pip install`).
*   Obtain a Pinecone API key (requires free account signup).
*   Configure the Pinecone client within the notebook using the API key and environment.
*   Implement the RAG pipeline in Task 3 using Pinecone for vector storage and retrieval (creating an index, upserting vectors, querying). 