# ITD-003: Product Name/ID Mapping Strategy for Hermes PoC

**Date:** 2024-07-26
**Author:** Gemini Assistant
**Status:** Revised

## 1. Context

Task 2 (Process Order Requests) requires identifying specific products mentioned in customer emails and mapping them to their unique `product ID` in the `products_df`. Customer emails often contain ambiguous, informal, partial product names/descriptions, or slight variations/typos (e.g., "blue summer dress", "Sleek Wallet", `CBT 89 01`). Analysis of `input/emails.csv` confirms that relying on product codes alone is insufficient. A reliable strategy is needed to bridge this gap and ensure accurate order processing.

This mapping needs to occur within the order processing loop (Task 2.1) after an LLM extracts the likely product mention and quantity.

## 2. Requirements

*   **Accuracy:** High precision in mapping ambiguous mentions to the correct `product ID`.
*   **Robustness:** Handle variations in naming, typos, plurals, and incomplete descriptions.
*   **Integration:** Fit seamlessly into the Python/pandas workflow and planned LLM calls.
*   **Scalability:** Method should be reasonably efficient for searching against the product catalog.
*   **Efficiency (PoC):** Prefer simpler solutions appropriate for a PoC.
*   **Assessment Alignment:** Employ techniques demonstrating effective use of combined AI (LLM) and other relevant methods (like fuzzy matching) as appropriate for assessment criteria.

## 3. Options Considered

1.  **Direct LLM Extraction & Mapping:**
    *   **Method:** Modify the Task 2.1 prompt for GPT-4o to directly identify and output the corresponding `product ID`.
    *   **Pros:** Simplest integration (single LLM call).
    *   **Cons:** Relies heavily on prompt engineering, struggles with typos/precise name variations, potential hallucination, context challenges for large catalogs, doesn't showcase combined techniques well.

2.  **LLM Extraction (Mention) + Fuzzy String Matching:**
    *   **Method:** Use GPT-4o to extract the *product name/description mention* and quantity. Then, use a library like `thefuzz` to calculate the similarity score between the extracted mention and all names in `products_df['name']`. Select the `product ID` with the highest score above a threshold.
    *   **Pros:** Clear separation of concerns (LLM for extraction, code for matching), robust to typos/minor variations, good assessment fit.
    *   **Cons:** Adds a dependency (`thefuzz`), requires tuning a similarity threshold, less effective for purely semantic differences vs. name similarity.

3.  **LLM Extraction (Mention) + Embedding Similarity Search:**
    *   **Method:** Use GPT-4o to extract the mention. Embed this text. Search the Pinecone index for the most similar product embedding.
    *   **Pros:** Reuses RAG infrastructure, excels at semantic matching.
    *   **Cons:** Adds vector search latency/cost to order processing, potentially less precise for exact name matching than fuzzy search, overkill if name matching is sufficient.

4.  **LLM Extraction (Mention) + Secondary LLM Mapping Call:**
    *   **Method:** Use one LLM call to extract the mention, a second LLM call to perform the mapping.
    *   **Pros:** Can provide more targeted context for mapping.
    *   **Cons:** Doubles LLM calls per item (cost, latency), complex.

## 4. Comparison

| Feature                 | Direct LLM Map (1) | Fuzzy Match (2)  | Embedding Sim (3) | Secondary LLM (4) |
| :---------------------- | :----------------- | :--------------- | :---------------- | :---------------- |
| **Accuracy (Semantic)** | Medium-High        | Low              | **High**          | Medium-High       |
| **Accuracy (Typos)**    | Medium             | **High**         | Medium            | Medium            |
| **Complexity**          | Low                | **Medium**       | Medium-High       | High              |
| **Cost / Latency**      | Low (1 LLM)        | **Low** (Fast code)| Medium (Vec Srch) | High (2 LLMs)     |
| **Dependencies**        | None extra         | `thefuzz`        | None extra        | None extra        |
| **Assessment Fit**      | Low                | **High**         | Medium            | Low               |

## 5. Decision

**Option 2: LLM Extraction (Mention) + Fuzzy String Matching** is selected as the primary strategy for the Hermes PoC.

## 6. Rationale

Given the observed nature of the input data (inconsistent product codes, presence of names/descriptions/typos) and the assessment requirement to demonstrate effective use of LLM capabilities combined with other techniques, Option 2 provides the best balance:

*   **Robustness:** Fuzzy matching directly addresses the need to handle typos and minor name variations effectively.
*   **Assessment Alignment:** This approach clearly combines LLM power (for initial understanding and extraction) with a standard, explainable matching algorithm (fuzzy logic), demonstrating a practical workflow.
*   **Simplicity:** While adding a dependency (`thefuzz`), the core logic is relatively straightforward compared to embedding search for every order item or multiple LLM calls.
*   **Performance:** Fuzzy matching against the product name list should be sufficiently fast for the PoC scale.

Option 1 (Direct LLM Mapping) is deemed too unreliable for variations and less suitable for the assessment goals. Option 3 (Embedding Search) is likely overkill and less precise for name matching in the order context. Option 4 is too complex and costly.

## 7. Next Steps

*   Install the `thefuzz` library (and potentially `python-Levenshtein` for speed). Add `%pip install thefuzz python-Levenshtein` to the notebook setup.
*   Refine the prompt for Task 2.1 (Order Processing) to focus on extracting the *product mention* (name/description) and quantity, outputting JSON like `[{"product_mention": "...", "quantity": ...}]`.
*   Implement the fuzzy matching logic using `thefuzz.process.extractOne` or similar to find the best match for each `product_mention` against `products_df['name']`.
*   Choose and implement a suitable similarity score threshold (e.g., 85) to determine a successful match.
*   Handle cases where no match meets the threshold (status: `mapping_failed`).
*   Update `plan.md` to reflect this revised strategy (specifically the Task 2.1 prompt example and mapping step). 