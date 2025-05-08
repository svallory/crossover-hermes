# ITD-002: Embedding Model Selection for Hermes PoC

**Date:** 2024-07-26
**Author:** Gemini Assistant
**Status:** Accepted

## 1. Context

The Hermes project requires an embedding model to convert product information (name, description, category, season) into vector representations. These embeddings are essential for Task 3 (Handle Product Inquiry), enabling Retrieval-Augmented Generation (RAG) by searching a vector database (Pinecone, per [ITD-001](./ITD-001-Vector-DB-Selection.md)) for relevant product context based on customer query similarity.

The chosen model needs to:
*   Generate high-quality embeddings that capture semantic relationships between product attributes and potential customer queries.
*   Be easily integrable into the Python notebook running in Google Colab.
*   Handle the embedding process for potentially 100,000+ products efficiently.
*   Be cost-effective for a Proof-of-Concept (PoC).

## 2. Options Considered

1.  **OpenAI Embedding Models:**
    *   Models: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`.
    *   Type: Managed API Service.
    *   Pros: High performance, simple API (client already needed for GPT-4o), no model hosting required.
    *   Cons: API cost per token, potential network latency.
2.  **Sentence Transformers (via Hugging Face):**
    *   Models: `all-MiniLM-L6-v2`, `all-mpnet-base-v2`, etc.
    *   Type: Open-Source Library / Pre-trained Models.
    *   Pros: Free to use (compute cost only), runs locally within Colab, excellent performance, wide model variety.
    *   Cons: Requires library install (`sentence-transformers`), model download/loading, potential Colab resource limits (RAM/GPU) for large models or datasets.
3.  **Other Fine-tuned or Specialized Models (e.g., from Hugging Face Hub):**
    *   Models: Various domain-specific or task-specific models.
    *   Type: Open-Source Library / Models.
    *   Pros: Potentially higher performance on specific tasks if a relevant model exists.
    *   Cons: Increased complexity in selection, integration, and management; fine-tuning is out of scope for this PoC.

## 3. Comparison

| Feature                 | OpenAI Embeddings (`text-embedding-3-small`) | Sentence Transformers (`all-mpnet-base-v2`) |
| :---------------------- | :------------------------------------------- | :---------------------------------------- |
| **Type**                | Managed API                                  | OSS Library + Model                       |
| **Embedding Quality**   | Very High                                    | High                                      |
| **Ease of Integration** | **Very High** (Existing client)              | High (Requires new library install/load)  |
| **Colab Suitability**   | High (API calls)                             | High (Runs locally, resource dependent)   |
| **Cost (PoC Scale)**    | **Very Low** (Est. ~$0.20 for 100k products) | Free (Compute only)                       |
| **Scalability (Embed)** | High (Managed Service)                       | Medium (Depends on Colab resources)       |
| **Dependency Mgmt**     | Minimal (Uses existing `openai` lib)         | Adds `sentence-transformers`              |

**Notes:**
*   The estimated cost for OpenAI's `text-embedding-3-small` for 100k products (assuming ~100 tokens avg. text) is negligible (~$0.20), well within PoC constraints and likely the provided API key quota.
*   While Sentence Transformers are free, the added dependency and local resource management slightly increase complexity compared to leveraging the existing OpenAI setup.
*   `text-embedding-3-small` offers a good balance of performance and cost compared to `large` or older models like `ada-002`.

## 4. Decision

**OpenAI's `text-embedding-3-small` model** is selected for generating product embeddings.

## 5. Rationale

Using OpenAI embeddings, specifically `text-embedding-3-small`, offers the most streamlined path for this PoC:

*   **Simplicity:** Leverages the existing `openai` client already required for GPT-4o interactions, minimizing new dependencies and setup.
*   **Performance:** Provides state-of-the-art embedding quality suitable for capturing product nuances for RAG.
*   **Cost-Effectiveness:** The cost for embedding the entire catalog once is extremely low and manageable.
*   **Managed Service:** Offloads the model hosting and inference computation, simplifying the notebook code and avoiding potential Colab resource bottlenecks during the embedding process for a large catalog.

This choice aligns with the project's goal of using integrated LLM tools effectively and efficiently for the PoC.

## 6. Next Steps

*   Ensure the `openai` library is installed (already planned).
*   Use the configured `OpenAI` client to call the embeddings endpoint with the `text-embedding-3-small` model.
*   Implement logic to concatenate relevant product fields (name, description, category, season) into a single text string before generating the embedding for each product.
*   Pass the generated vectors to the Pinecone client ([ITD-001](./ITD-001-Vector-DB-Selection.md)) for indexing.
*   Update the `plan.md` to reflect this decision. 