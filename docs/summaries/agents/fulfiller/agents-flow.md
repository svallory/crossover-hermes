## File: src/hermes/agents/agents-flow.md

This file provides a high-level overview of the Hermes agent system.

**Key Components:**

*   **Email Analyzer Agent (`classifier.py`):**
    *   Entry point for emails.
    *   Identifies language, primary intent, PII, signals.
    *   Segments emails (inquiry, order, personal statement).
    *   Classifies as "product inquiry" or "order request".
    *   Extracts product references (direct ID, fuzzy name, context-based description).
    *   Output: `EmailAnalysis` (comprehensive, with all product mentions).
*   **Product Resolver Agent (`stockkeeper.py`):**
    *   Input: Product mentions from Email Analyzer.
    *   Deduplicates and resolves mentions to catalog products (exact ID, fuzzy name, semantic vector search).
    *   Provides confidence scores.
    *   Uses LLM for disambiguation.
    *   Output: `ResolvedProductsOutput` (resolved products, unresolved mentions).
*   **Order Processor Agent (`fulfiller.py`):**
    *   Input: Resolved products from Product Resolver.
    *   Processes order requests.
    *   Verifies stock, updates inventory.
    *   Tracks item status.
    *   Applies promotions.
    *   Suggests alternatives for out-of-stock items.
    *   Calculates total price.
    *   Output: `ProcessedOrder` (detailed order status).
*   **Inquiry Responder Agent (`advisor.py`):**
    *   Input: Resolved products from Product Resolver.
    *   Handles product inquiries.
    *   Uses RAG for semantic product search.
    *   Extracts and classifies questions.
    *   Answers questions factually.
    *   Identifies related products.
    *   Handles mixed-intent emails.
    *   Output: `InquiryAnswers` (factual answers).
*   **Response Composer Agent (`composer.py`):**
    *   Input: Outputs from previous agents.
    *   Analyzes customer communication style for tone.
    *   Adapts tone and style.
    *   Plans response structure.
    *   Personalizes response using customer signals.
    *   Ensures all questions/order aspects are addressed.
    *   Generates natural language.
    *   Responds in customer's language.
    *   Creates subject line.
    *   Output: `ComposedResponse` (final personalized response text).

**Workflow:**

*   Implemented using LangGraph's state graph API (`workflow` directory).
*   Uses `StateGraph` and `OverallState`.
*   Conditional routing based on email intent.
*   Mermaid diagram illustrates the flow: Start -> Analyze -> Stockkeeper -> (Order and/or Inquiry or Compose) -> Compose -> End.

**Key Inputs/Outputs (High-Level):**

*   **Input:** Raw email text (optional subject).
*   **Output:** `ComposedResponse` (final email response).

**Models Used (General Mention):**
*   LLMs are used by Email Analyzer, Product Resolver (for disambiguation), Inquiry Responder (RAG), and Response Composer. Specific models not detailed in this file. 