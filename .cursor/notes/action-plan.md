# Hermes Codebase Improvement Action Plan

This plan outlines the steps to address the issues identified in the `evaluation-report.md` to elevate the Hermes codebase to an ideal reference solution.

## Checklist

### 1. Model Definition Unification
- [x] **Identify all Pydantic models** used across agents and tools (e.g., `ProductReference`, `CustomerSignal`, `ToneAnalysis`, `EmailAnalysis`, `ProductInformation`, `QuestionAnswer`).
- [x] **Choose a central location for these models**: `src/state.py` or a new `src/models.py`. (Chose `src/state.py`)
- [x] **Consolidate definitions**: Move/redefine all shared models into the chosen central location.
- [x] **Update imports**: Modify all agent and tool files to import models from the central location.
- [x] **Remove duplicate/near-duplicate definitions** from their original files. (Note: Manual cleanup needed for commented blocks in `src/tools/order_tools.py` due to tool issues).
- [ ] **Verify consistency**: Ensure all parts of the codebase use the same, centralized model definitions.

### 2. Correct Tool Data Handling (Especially Order Tools)
- [x] **Identify tools loading data directly**: Focus on `src/tools/order_tools.py` (`check_stock`, `update_stock`, `find_alternatives_for_oos`).
- [x] **Modify tool signatures**: Ensure these tools accept `product_catalog_df` (and `vector_store` if needed) as arguments.
- [x] **Remove internal CSV loading**: Delete lines of code that read `products.csv` (or other data files) from within these tools.
- [x] **Update tool logic**: Ensure tools operate *solely* on the passed DataFrame arguments.
- [x] **Ensure `update_stock` modifies the passed DataFrame**: The changes must affect the DataFrame instance that is part of the agent's state, persisting within the pipeline's execution session for a single email.
- [ ] **Test stock update persistence**: Verify that stock changes made by `update_stock` are reflected in subsequent operations within the same email processing workflow.

### 3. Correct Primary Data Sourcing
- [x] **Review `src/process_emails.py` data loading**: Focus on how `product_catalog_df` and `emails_df` are sourced.
- [x] **Implement Google Sheets loading logic**: Add functionality to read product and email data primarily from the Google Spreadsheet specified in the assignment.
    - [x] Consider using libraries like `gspread` and `gspread-dataframe`. (Used direct CSV export link method from assignment).
- [x] **Update `src/process_emails.py`**: Replace or supplement local CSV loading with the new Google Sheets loading mechanism for primary data.
- [x] **Ensure `HermesState` is populated correctly**: The `product_catalog_df` (and email data) loaded from Google Sheets should be correctly passed into the `HermesState`.
- [x] **Remove/deprecate reliance on local CSVs** for primary input data if they are fully replaced. If kept as fallbacks, clearly document this. (Removed primary reliance).
- [x] **Update agent/tool access**: Modify agents (`src/agents/*`) and tools (`src/tools/*`) to access `product_catalog_df` and `vector_store` from the `HermesState` attributes (e.g., `state.get("product_catalog_df")`) rather than `state.metadata`. (Done for agents; tools accessing DataFrame already updated in Step 2). (Note: Manual cleanup/verification needed for state access in `src/agents/inquiry_responder.py` due to tool issues).

### 4. Clarity on LLM Usage in Tools/Agents & Configuration
- [ ] **Review `src/tools/response_tools.py`**:
    - [ ] **`analyze_tone`**: If intended to be LLM-driven, replace regex/keyword logic with an LLM call. Otherwise, add a comment clarifying its simplified nature for the assignment.
    - [ ] **`extract_questions`**: Same as `analyze_tone`.
    - [ ] **`generate_natural_response`**:
        - If this tool is meant to be the final LLM call for response generation, its implementation *must* invoke an LLM using appropriate prompts and the LLM client.
        - If it's a placeholder, ensure the `ResponseComposer` agent in `src/agents/response_composer.py` clearly shows its own LLM invocation (e.g., using `llm.ainvoke` with `response_composer_prompt`).
- [ ] **Review `src/llm_client.py`**:
    - [x] **Uncomment and verify `openai_api_base=config.llm_base_url`**: Ensure it correctly uses `config.llm_base_url` when the assignment-provided OpenAI API key and custom base URL are used.
    - [x] Test with the provided custom base URL and API key.
- [ ] **Review `src/config.py`**:
    - [x] Ensure `llm_base_url` (from `OPENAI_BASE_URL` env var) is correctly configured to default to or clearly guide setting the custom base URL from the assignment.
- [x] **Review `src/agents/email_classifier.py` `verify_email_analysis`**: Evaluate if the LLM call for corrections is always necessary versus improving the initial prompt. Add comments on this trade-off.
- [x] **Add comments** to any other simplified (non-LLM) tools explaining their placeholder status or rationale for simplification.

### 5. Enhanced Documentation for Reference Purposes
- [ ] **Review entire codebase** for areas needing clarification.
- [ ] **Add comments explaining design choices**: Especially for simplifications made due to assignment constraints (e.g., hardcoded complementary categories in `catalog_tools.py::find_related_products`).
- [ ] **Explain "hidden criteria" demonstrations**:
    - [ ] Comment the purpose of `TEST_FORCE_OUT_OF_STOCK` flag in `src/agents/order_processor.py`.
    - [ ] Document any other code specifically added to address `hidden-evaluation-criteria.md`.
- [ ] **Clarify simplifications in tools**: e.g., `extract_customer_name` in `response_composer.py`.
- [ ] **Improve comments on defaults in `src/config.py`**: Explain the source of default values.
- [ ] **Comment potential `gspread` exceptions** in `src/output.py`.

### 6. Demonstrate Testability in Notebook
- [ ] **Identify key functions and agents** that should be tested/demonstrated.
- [ ] **Design example calls**: Prepare input data for these examples.
- [ ] **Incorporate new cells in the main Python notebook**:
    - [ ] For each key component, add a cell demonstrating its usage.
    - [ ] Include assertions (e.g., `assert result == expected_output`) to validate outputs.
    - [ ] Show clear expected outputs if assertions are not used.
- [ ] **Cover edge cases**: Include examples from `hidden-evaluation-criteria.md` (e.g., multi-language, complex product references, vague references, mixed intents, tone adaptation).
- [ ] **Ensure the notebook runs end-to-end** with these test/demonstration cells.

### 7. Minor Code Refinements
- [x] **Address code duplications**:
    - [x] **`src/vectorstore.py`**: Refactor document creation logic in `create_product_vectorstore` and `create_product_vectorstore_batched` into a common helper function.
    - [x] Identify and refactor other minor duplications.
- [x] **Ensure consistent and precise type hinting**: Review all functions, methods, and Pydantic models.
- [x] **Ensure output formatting in `src/output.py` precisely matches assignment specifications**:
    - [x] Double-check all sheet names.
    - [x] Double-check all column headers and their order for each sheet against `assignment-instructions.md`.
    - [x] Verify data formatting for complex fields (e.g., alternatives in order processing).
- [x] **Replace "magic strings" with Enums/Constants**:
    - [x] Identify string literals used for classifications (e.g., `'product_inquiry'`, `'order_request'`), signal types, tone types, etc.
    - [x] Define Enums (e.g., in `src/models.py` or `src/state.py`) for these sets of values.
    - [x] Update the codebase to use these Enums/constants instead of string literals.
- [x] **Refine `llm_client.py` model detection**: Make the `gemini` vs `gpt` check more robust than just `model_name.lower()`.
- [x] **Link embedding dimensions to config**: In `src/vectorstore.py`, consider deriving `dimensions` from `embedding_model_name` in `HermesConfig` if variations are anticipated.
- [x] **State Handling Clarity in Agents**: Review agents to see where Pydantic models can be consistently reconstructed from state dicts at entry points for better type safety.
- [x] **Simplify `src/agents/inquiry_responder.py` `process_inquiry_node`**: If possible, break it into smaller helper functions.
- [x] **Refactor repetitive `ProductInformation` assembly** in `src/agents/inquiry_responder.py`.

### 8. Architectural Principles
- [ ] **Enforce separation between agents and tools**:
    - [ ] **LLM calls should only be made from agents, not from tools**: Review all tools and ensure they only contain deterministic computation.
    - [ ] **Tools that currently contain LLM calls or placeholders for them** (like `generate_natural_response`) should be refactored to move the LLM logic to the corresponding agent.
    - [ ] **Avoid using regex to process email content**: Replace regex-based processing (like in `analyze_tone` and `extract_questions`) with proper LLM-based processing in agents.
    - [ ] **Ensure clear documentation** of this architectural principle in affected files.

This checklist provides a structured approach to refining the Hermes codebase. 