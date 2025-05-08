""" {cell}
## Order Processor Agent Prompts

This module defines prompts for the Order Processor Agent.
This agent is responsible for handling emails classified as "order_request".
Its tasks include:
- Validating and resolving product references received from the Email Analyzer.
- Checking product availability against current inventory (likely via tool calls).
- Determining the status of each requested item (e.g., "created", "out_of_stock").
- Compiling a summary of the order processing, including fulfilled items, out-of-stock items,
  and any suggested alternatives.

The prompts here might be used to guide an LLM in interpreting the structured product
references, deciding which inventory tools to call, or summarizing the results of tool calls
into the `OrderProcessingResult` Pydantic model.
"""

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

# --- System Message --- 
ORDER_PROCESSOR_SYSTEM_MESSAGE = """
You are an Order Processing Specialist for "Hermes", a fashion retail company.
Your task is to process a list of product references extracted from a customer's email and determine the order details.
You will be provided with the extracted product references and context from the email analysis.

Your goals are:
1.  Verify each product reference. If a reference is ambiguous (e.g., multiple products match a vague name, or a product ID is invalid), note this.
2.  For each valid product, determine the quantity requested.
3.  Prepare a structured list of items to be checked against inventory. This list will then be used by other tools to check stock and create the order.

Output Format:
Provide your output as a JSON object that represents a preliminary order plan. This plan should include a list of items, where each item has:
- `resolved_product_id`: (string | null) The best guess for the product ID. Null if unresolvable.
- `resolved_product_name`: (string) The name of the product as understood.
- `requested_quantity`: (int) The quantity requested.
- `original_reference_text`: (string) The text from the email that this item corresponds to.
- `status_message`: (string) Any notes, e.g., "Needs stock check", "Ambiguous reference, requires clarification", "Product ID seems invalid".

Example of an item in the list:
{
  "resolved_product_id": "LTH0976",
  "resolved_product_name": "Leather Bifold Wallet",
  "requested_quantity": 2,
  "original_reference_text": "LTH0976 Leather Bifold Wallets",
  "status_message": "Needs stock check"
}

If a product reference is too vague to resolve to a specific product ID confidently without further catalog search (which is done by a separate tool), mark `resolved_product_id` as null and explain in `status_message`.
Focus on interpreting the provided `product_references` list. Do not try to access external tools or inventory yourself; that is a subsequent step.
"""

# --- Human Message Template ---
ORDER_PROCESSOR_HUMAN_TEMPLATE = """
An email has been analyzed and the following product references were extracted. Please process them into a preliminary order plan.

Email Analysis Context:
- Customer language: {language}
- Overall email reasoning by analyzer: {email_analyzer_reasoning}

Extracted Product References (from Email Analyzer):
```json
{product_references_json}
```

Your JSON output for the preliminary order plan:
"""

# --- Construct ChatPromptTemplate ---
order_processor_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(ORDER_PROCESSOR_SYSTEM_MESSAGE),
    HumanMessagePromptTemplate.from_template(ORDER_PROCESSOR_HUMAN_TEMPLATE)
])

order_processor_prompt.input_variables = ["language", "email_analyzer_reasoning", "product_references_json"]

""" {cell}
### Prompts for the Order Processor Agent

This module contains LangChain `ChatPromptTemplate`(s) that could be used by the `Order Processor Agent`. The `Order Processor Agent` primarily relies on tools to perform its tasks (e.g., `check_stock`, `update_stock`, `find_product_by_id`). However, LLM prompts might be useful in specific scenarios:

1.  **Order Details Confirmation/Structuring**: If the product references extracted by the `Email Analyzer Agent` are complex or slightly ambiguous, an LLM could be used to confirm and structure these details before calling inventory tools. This ensures tools are called with accurate information.
2.  **Alternative Selection Logic**: While tools can find potential alternatives for out-of-stock items, an LLM could help in selecting the most suitable alternative based on nuanced understanding of the customer's original request or implied preferences.
3.  **Summarizing Complex Order Outcomes**: If an order involves multiple items with different statuses (some fulfilled, some out-of-stock, some with alternatives), an LLM could help summarize this complex outcome into a structured format for the `Response Composer Agent`.

Given the design in `reference-agent-flow.md` where the `OrderProcessorAgent` directly uses tools based on structured `EmailAnalysis` output, the need for extensive LLM prompting within this agent is minimized. The prompts here are conceptual placeholders for tasks that might require LLM reasoning if tool inputs/outputs need further refinement.

The primary Pydantic model this agent aims to populate is `OrderProcessingResult` (defined in `reference-agent-flow.md` and to be implemented in `src/agents/order_processor.py`).
"""

# --- Prompt for Verifying and Structuring Order Items --- 
# This is a conceptual prompt. The Email Analyzer should ideally provide clean ProductReferences.
# This prompt could be used if those references need further LLM-based validation or structuring
# before tool calls for inventory checking.

VERIFY_ORDER_ITEMS_SYSTEM_MESSAGE_CONTENT = """
You are an assistant that helps verify and structure product items for an order based on an initial analysis of a customer email. Your goal is to prepare a clean list of items, quantities, and any identified product IDs or names for inventory checking.

Given a list of product references extracted from an email, review each one. If a product ID is clearly identified, prioritize it. If only a name or description is available, ensure it's captured accurately.
Confirm the quantity for each item, defaulting to 1 if not specified.

Output a JSON list of objects, where each object has:
- `product_id`: (string, optional) The specific product ID, if confidently identified.
- `product_name`: (string, optional) The product name mentioned or inferred.
- `reference_text`: (string) The original text snippet from the email referring to this item.
- `quantity`: (int) The requested quantity.
- `notes`: (string, optional) Any ambiguities or points requiring attention for this item.

Example Input (product_references list from EmailAnalysis):
```json
[
  {{
    "reference_text": "2 LTH0976 wallets",
    "reference_type": "product_id",
    "product_id": "LTH0976",
    "product_name": "Leather Bifold Wallet",
    "quantity": 2,
    "confidence": 0.95,
    "excerpt": "2 LTH0976 wallets"
  }},
  {{
    "reference_text": "that blue t-shirt you showed last week",
    "reference_type": "description",
    "product_id": null,
    "product_name": "blue t-shirt",
    "quantity": 1,
    "confidence": 0.7,
    "excerpt": "that blue t-shirt you showed last week"
  }}
]
```

Expected JSON Output Structure:
```json
[
  {{
    "product_id": "LTH0976",
    "product_name": "Leather Bifold Wallet",
    "reference_text": "2 LTH0976 wallets",
    "quantity": 2,
    "notes": null
  }},
  {{
    "product_id": null,
    "product_name": "blue t-shirt",
    "reference_text": "that blue t-shirt you showed last week",
    "quantity": 1,
    "notes": "Product ID not specified, name is descriptive. Requires resolution against catalog."
  }}
]
```
Focus on extracting the necessary details to proceed with inventory checks and order processing.
"""

VERIFY_ORDER_ITEMS_HUMAN_MESSAGE_TEMPLATE_CONTENT = """
Please verify and structure the following product references for order processing. Provide the output ONLY as a JSON list of objects, matching the specified structure.

Extracted Product References:
```json
{product_references_json_string}
```

Your structured JSON list:
"""

# This prompt is more for internal data structuring and might not always be needed
# if the Email Analyzer's output is already sufficiently structured.
verify_order_items_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(VERIFY_ORDER_ITEMS_SYSTEM_MESSAGE_CONTENT),
    HumanMessagePromptTemplate.from_template(VERIFY_ORDER_ITEMS_HUMAN_MESSAGE_TEMPLATE_CONTENT)
])

# --- Prompt for Structuring Order Processing Result --- (Conceptual)
# This prompt would be used if the agent needs to synthesize multiple tool outputs
# (e.g., stock checks, alternative findings) into the final OrderProcessingResult Pydantic model.

STRUCTURE_ORDER_PROCESSING_RESULT_SYSTEM_MESSAGE_CONTENT = """
You are an assistant that compiles order processing information into a structured JSON output conforming to the `OrderProcessingResult` Pydantic model.

**Pydantic Model for `OrderProcessingResult` (summary):**
```json
{{
  "email_id": "(string)",
  "order_items": [
    {{
      "product_id": "(string)",
      "product_name": "(string)",
      "quantity": {{int}},
      "status": "(must be 'created' or 'out_of_stock')",
      "unit_price": {{float}},
      "promotion": "(string, optional, e.g., '10% off')"
    }}
  ],
  "fulfilled_items": {{int}},
  "out_of_stock_items": {{int}},
  "total_price": {{float, for fulfilled items}},
  "recommended_alternatives": [
    {{
      "original_product_id": "(string)",
      "original_product_name": "(string)",
      "alternative_product_id": "(string)",
      "alternative_product_name": "(string)",
      "alternative_stock": {{int}},
      "alternative_price": {{float}},
      "reason": "(string, e.g., 'Same category, in stock')"
    }}
  ]
}}
```

Given the original email ID, the list of processed items (with their status and prices), and any recommended alternatives for out-of-stock items, generate the complete JSON object.
Calculate `fulfilled_items`, `out_of_stock_items`, and `total_price` based on the `order_items` list.
Ensure all monetary values are floats with two decimal places where appropriate.
"""

STRUCTURE_ORDER_PROCESSING_RESULT_HUMAN_MESSAGE_TEMPLATE_CONTENT = """
Please structure the following order processing details into the `OrderProcessingResult` JSON format.

Email ID: {email_id}

Processed Items (list of dictionaries, each item has product_id, product_name, requested_quantity, final_status ('created' or 'out_of_stock'), unit_price, identified_promotion):
```json
{processed_items_json_string}
```

Recommended Alternatives (list of dictionaries, each with original_product_id, original_product_name, alternative_product_id, alternative_product_name, alternative_stock, alternative_price, reason):
```json
{recommended_alternatives_json_string}
```

Your complete `OrderProcessingResult` JSON object:
"""

structure_order_processing_result_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(STRUCTURE_ORDER_PROCESSING_RESULT_SYSTEM_MESSAGE_CONTENT),
    HumanMessagePromptTemplate.from_template(STRUCTURE_ORDER_PROCESSING_RESULT_HUMAN_MESSAGE_TEMPLATE_CONTENT)
])

""" {cell}
### Notes on Order Processor Prompts:

-   **Minimal Prompts**: The `Order Processor Agent` is envisioned to be heavily tool-driven. The `Email Analyzer Agent` should provide sufficiently structured `ProductReference` data so that the `Order Processor` can directly use tools like `find_product_by_id`, `check_stock`, etc.
-   **`verify_order_items_prompt`**: This prompt is a contingency. If `ProductReference` items from the analyzer are ever ambiguous for direct tool use (e.g., quantity needs parsing from text like "a pair of socks"), this prompt could help an LLM to clean them up. However, the primary responsibility for clear extraction lies with the `Email Analyzer`.
-   **`structure_order_processing_result_prompt`**: This prompt is more likely to be useful. After the agent has called various tools (e.g., multiple stock checks, alternative lookups), it might have a collection of disparate data points. This prompt helps an LLM consolidate all that information into the final, structured `OrderProcessingResult` Pydantic model, which is then passed to the `Response Composer Agent`. This ensures data consistency and completeness.
-   **Pydantic Model Adherence**: Both conceptual prompts emphasize generating JSON that adheres to specific Pydantic model structures (`OrderItem`-like list for the first, `OrderProcessingResult` for the second). This is critical for seamless data flow and validation in the LangGraph pipeline.

In practice, the necessity and complexity of these prompts would depend on how robust the tool interactions are and how well the `Email Analyzer Agent` pre-processes the information. The goal is to use LLMs for tasks requiring nuanced understanding or complex structuring, and tools for deterministic operations.
""" 