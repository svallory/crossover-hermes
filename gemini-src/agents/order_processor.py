""" {cell}
## Order Processor Agent

This module implements the Order Processor Agent for the Hermes system.
This agent is activated when an email is classified as an "order_request".
Its core responsibilities include:

1.  **Interpreting Order Details**: Taking the `EmailAnalysis` (specifically the
    `product_references` list) and using an LLM with `order_processor_prompt` to
    create a more structured preliminary order plan. This step helps resolve ambiguities
    and confirm quantities before interacting with inventory.
2.  **Product Validation and Stock Checking**: For each item in the preliminary plan:
    -   Validating the product ID (e.g., using `find_product_by_id` tool).
    -   Checking current stock levels using the `check_stock` tool.
3.  **Inventory Updates**: If an item is in stock and the order proceeds, the `update_stock`
    tool is called to decrement the inventory.
4.  **Handling Out-of-Stock Items**: If an item is out of stock, it's marked accordingly.
    The `find_alternatives_for_oos` tool may be called to suggest replacements.
5.  **Promotion Extraction**: The `extract_promotion` tool is used to check for any
    special offers on the ordered products.
6.  **Result Compilation**: All outcomes (fulfilled items, OOS items, alternatives,
    promotions, total price) are compiled into an `OrderProcessingResult` Pydantic model.
7.  **Verification**: The final `OrderProcessingResult` may undergo a verification step
    to ensure consistency and accuracy (as mentioned in `reference-agent-flow.md`).

The agent orchestrates LLM calls for interpretation and multiple tool calls for data
retrieval and state changes (inventory updates).
"""

import json # For parsing JSON strings if necessary, and serializing for prompts
from typing import List, Optional, Dict, Any, Union
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableConfig

# Placeholder imports - these would be actual imports from other project modules
# from ..state import HermesState
# from ..config import HermesConfig
# from ..prompts.order_processor import order_processor_prompt
# from ..tools.catalog_tools import find_product_by_id, find_product_by_name # etc.
# from ..tools.order_tools import check_stock, update_stock, find_alternatives_for_oos, extract_promotion
# from .email_classifier import EmailAnalysis # Assuming EmailAnalysis Pydantic model is here or in a shared models file

# --- Pydantic Models for Structured Output (as per reference-agent-flow.md) ---

class OrderItem(BaseModel):
    """Represents a single item within an order, detailing its processing status."""
    product_id: str = Field(description="Confirmed Product ID of the item.")
    product_name: str = Field(description="Confirmed name of the product.")
    quantity_requested: int = Field(description="Quantity originally requested by the customer.")
    quantity_fulfilled: int = Field(default=0, description="Quantity that can be fulfilled from stock.")
    status: str = Field(description="Processing status: e.g., 'created', 'out_of_stock', 'partially_fulfilled', 'product_not_found', 'ambiguous_reference'.")
    unit_price: Optional[float] = Field(default=None, description="Unit price of the product at the time of order.")
    promotion_details: Optional[str] = Field(default=None, description="Text describing any applicable promotion.")
    original_reference_text: Optional[str] = Field(default=None, description="The original text snippet from the email for this item.")

class AlternativeProductSuggestion(BaseModel):
    """Details of an alternative product suggested for an out-of-stock item."""
    original_product_id: str
    original_product_name: str
    suggested_alternative_product_id: str
    suggested_alternative_product_name: str
    stock_available: int
    price: Optional[float]
    reason_for_suggestion: Optional[str] = Field(default="Similar item in stock.")

class OrderProcessingResult(BaseModel):
    """Comprehensive result of processing an order request."""
    email_id: str = Field(description="The ID of the email this order pertains to.")
    order_items: List[OrderItem] = Field(description="List of all items processed for the order.")
    overall_order_status: str = Field(description="Overall status: e.g., 'fully_fulfilled', 'partially_fulfilled', 'fully_out_of_stock', 'failed_to_process'.")
    total_price_fulfilled: float = Field(default=0.0, description="Total price for items that are fulfilled.")
    out_of_stock_items_count: int = Field(default=0, description="Number of unique product types that were out of stock or partially out of stock.")
    suggested_alternatives: List[AlternativeProductSuggestion] = Field(default_factory=list, description="List of suggested alternatives for out-of-stock items.")
    processing_notes: List[str] = Field(default_factory=list, description="Any notes or issues encountered during processing.")

# --- Agent Node Function ---

async def process_order_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    LangGraph node function for the Order Processor Agent.
    Processes product references from EmailAnalysis, interacts with catalog/inventory tools,
    and compiles an OrderProcessingResult.
    """
    print("--- Calling Order Processor Agent Node ---")
    # hermes_config = HermesConfig.from_runnable_config(config.get("configurable", {}) if config else {})
    # llm = ChatOpenAI(model=hermes_config.llm_model_name, temperature=hermes_config.llm_temperature, ...)
    
    email_id = state.get("email_id")
    email_analysis: Optional[Dict[str, Any]] = state.get("email_analysis") # This is a dict from EmailAnalysis.model_dump()
    
    if not email_analysis or not email_analysis.get("product_references"):
        print("No product references found in email analysis. Skipping order processing.")
        # Create a minimal result indicating no action taken or an issue
        error_result = OrderProcessingResult(
            email_id=email_id,
            order_items=[],
            overall_order_status="failed_to_process",
            processing_notes=["No product references were extracted by the Email Analyzer."]
        )
        return {"order_result": error_result.model_dump()}

    # Placeholder: Simulate tools and product_catalog_df that would be available in the agent's environment
    # product_catalog_df = load_product_catalog() # This would be loaded once and passed around
    # tools = {
    #     "find_product_by_id": find_product_by_id_tool_impl, # Actual tool functions
    #     "check_stock": check_stock_tool_impl,
    #     "update_stock": update_stock_tool_impl,
    #     "find_alternatives_for_oos": find_alternatives_for_oos_tool_impl,
    #     "extract_promotion": extract_promotion_tool_impl
    # }

    print(f"Processing order for email ID: {email_id}")
    product_references_from_analyzer = email_analysis.get("product_references", [])
    
    # Step 1: Use LLM to get a preliminary order plan (as per order_processor_prompt)
    # preliminary_order_plan_json_str = await (order_processor_prompt | llm | StrOutputParser()).ainvoke({
    #     "language": email_analysis.get("language", "English"),
    #     "email_analyzer_reasoning": email_analysis.get("reasoning", ""),
    #     "product_references_json": json.dumps(product_references_from_analyzer)
    # }, config=config)
    # preliminary_order_plan = json.loads(preliminary_order_plan_json_str) # Assuming LLM returns parsable JSON
    # planned_items = preliminary_order_plan.get("items", [])
    
    # --- MOCK Preliminary Plan (replaces LLM call for now) ---
    # Convert analyzer references directly for mock, assuming they are somewhat clean
    planned_items = []
    for ref in product_references_from_analyzer:
        planned_items.append({
            "resolved_product_id": ref.get("product_id"),
            "resolved_product_name": ref.get("product_name", ref.get("reference_text")),
            "requested_quantity": ref.get("quantity", 1),
            "original_reference_text": ref.get("reference_text"),
            "status_message": "Needs stock check" if ref.get("product_id") else "Ambiguous reference, needs ID resolution/tool call"
        })
    # --- END MOCK ---

    processed_order_items: List[OrderItem] = []
    suggested_alternatives_list: List[AlternativeProductSuggestion] = []
    processing_notes_list: List[str] = []
    total_fulfilled_price = 0.0
    oos_items_count = 0

    # Step 2: Process each item in the planned_items list
    for item_plan in planned_items:
        print(f"Processing planned item: {item_plan.get('resolved_product_name')}")
        # Mock product details and tool calls
        # In real implementation, call tools like find_product_by_id, check_stock, etc.
        product_id = item_plan.get("resolved_product_id")
        product_name = item_plan.get("resolved_product_name")
        requested_qty = item_plan.get("requested_quantity", 1)
        mock_item_price = 25.00 # Default mock price
        mock_promotion = None

        if not product_id: # Product ID was not resolved by analyzer or initial LLM plan step
            # Potentially call find_product_by_name tool here if name is available
            processing_notes_list.append(f"Could not resolve Product ID for item: '{product_name}'. Requires catalog search.")
            processed_order_items.append(OrderItem(
                product_id="UNKNOWN", product_name=product_name, quantity_requested=requested_qty,
                status="ambiguous_reference", original_reference_text=item_plan.get("original_reference_text")
            ))
            continue
        
        # Mock: Assume product found by ID and has details
        # product_details = tools["find_product_by_id"](product_id, product_catalog_df)
        # if isinstance(product_details, ProductNotFound):
        #     processed_order_items.append(OrderItem(product_id=product_id, product_name=product_name, quantity_requested=requested_qty, status="product_not_found"))
        #     continue
        # product_name = product_details.name # Update name from catalog
        # mock_item_price = product_details.price if product_details.price else 25.00
        # mock_promotion_obj = tools["extract_promotion"](product_details.description, product_name)
        # mock_promotion = mock_promotion_obj.promotion_text if mock_promotion_obj.has_promotion else None

        # Mock stock check
        # stock_status_result = tools["check_stock"](product_id, product_catalog_df, requested_qty)
        stock_available = 10 # Mock available stock
        if product_id == "OUTOFSTOCK001": stock_available = 0
        
        fulfilled_qty = 0
        item_status = ""

        if stock_available >= requested_qty:
            # Simulate update_stock tool call
            # update_result = tools["update_stock"](product_id, requested_qty, product_catalog_df)
            # if update_result.status == "success":
            fulfilled_qty = requested_qty
            item_status = "created"
            total_fulfilled_price += fulfilled_qty * mock_item_price
            # else: item_status = "inventory_update_failed"; processing_notes_list.append(f"Failed to update stock for {product_id}")
        elif stock_available > 0: # Partial fulfillment
            # update_result = tools["update_stock"](product_id, stock_available, product_catalog_df)
            # if update_result.status == "success":
            fulfilled_qty = stock_available
            item_status = "partially_fulfilled"
            total_fulfilled_price += fulfilled_qty * mock_item_price
            oos_items_count += 1
            processing_notes_list.append(f"Partially fulfilled {product_name} ({fulfilled_qty}/{requested_qty}).")
            # Try to find alternatives for the remaining quantity
            # alternatives = tools["find_alternatives_for_oos"](product_id, product_catalog_df, limit=1)
            # if alternatives and not isinstance(alternatives, ProductNotFoundModel): suggested_alternatives_list.append(...) 
            # else: item_status = "inventory_update_failed"; processing_notes_list.append(f"Failed to update stock for partial {product_id}")
        else: # Fully out of stock
            item_status = "out_of_stock"
            oos_items_count += 1
            # alternatives = tools["find_alternatives_for_oos"](product_id, product_catalog_df, limit=1)
            # if alternatives and not isinstance(alternatives, ProductNotFoundModel): suggested_alternatives_list.append(...) 
            if product_id == "OUTOFSTOCK001": # Mock alternative suggestion
                suggested_alternatives_list.append(AlternativeProductSuggestion(
                    original_product_id=product_id, original_product_name="Sold Out Item",
                    suggested_alternative_product_id="INSTOCKALT002", suggested_alternative_product_name="Similar Available Item",
                    stock_available=20, price=22.50
                ))

        processed_order_items.append(OrderItem(
            product_id=product_id, product_name=product_name, quantity_requested=requested_qty,
            quantity_fulfilled=fulfilled_qty, status=item_status, unit_price=mock_item_price,
            promotion_details=mock_promotion, original_reference_text=item_plan.get("original_reference_text")
        ))

    overall_status = "fully_fulfilled"
    if any(item.status == "partially_fulfilled" for item in processed_order_items): overall_status = "partially_fulfilled"
    if all(item.status == "out_of_stock" for item in processed_order_items if item.product_id != "UNKNOWN"): overall_status = "fully_out_of_stock"
    if not processed_order_items or all(item.status in ["ambiguous_reference", "product_not_found"] for item in processed_order_items):
        overall_status = "failed_to_process"
        if not any("No product references" in note for note in processing_notes_list): # Avoid duplicate
             processing_notes_list.append("Could not process any items from the order request.")

    final_result = OrderProcessingResult(
        email_id=email_id,
        order_items=processed_order_items,
        overall_order_status=overall_status,
        total_price_fulfilled=total_fulfilled_price,
        out_of_stock_items_count=oos_items_count,
        suggested_alternatives=suggested_alternatives_list,
        processing_notes=processing_notes_list
    )

    # Verification step (placeholder, as per reference-agent-flow.md)
    # verified_result = verify_order_processing_output(final_result, llm, config)
    # print(f"Order Processing Result: {verified_result.model_dump_json(indent=2)}")
    # return {"order_result": verified_result.model_dump()}
    
    print(f"Order Processing Result: {final_result.overall_order_status}")
    return {"order_result": final_result.model_dump()}


""" {cell}
### Agent Implementation Notes:

- **Pydantic Models**: Defines `OrderItem`, `AlternativeProductSuggestion`, and `OrderProcessingResult` to structure the agent's findings and final output.
- **Agent Node Function (`process_order_node`)**:
    - Retrieves `EmailAnalysis` from the state.
    - **LLM for Preliminary Plan (Commented Out/Mocked)**: The ideal flow involves an LLM call using `order_processor_prompt` to convert raw `product_references` into a `preliminary_order_plan`. This plan helps disambiguate items before tool calls. This is currently mocked.
    - **Tool Orchestration Loop**: The core of the agent iterates through planned items, simulating calls to various catalog and inventory tools (`find_product_by_id`, `check_stock`, `update_stock`, `find_alternatives_for_oos`, `extract_promotion`). The actual tool calls are commented out and replaced by mock logic.
        - **Crucial**: The actual implementation would need access to the tool functions and the `product_catalog_df`.
    - **State Updates**: It carefully tracks fulfilled quantities, prices, out-of-stock items, and suggested alternatives.
    - **Result Compilation**: Aggregates all information into an `OrderProcessingResult` object.
- **Mock Logic**: The current code heavily relies on mock logic for LLM calls and tool interactions. **These mocks must be replaced with actual LLM invocations and tool calls using the tools defined in `src/tools/`**.
- **Inventory Management**: The `update_stock` tool call is critical. How this modification is persisted or reflected in the shared `product_catalog_df` across the entire application (if processing multiple emails) is a key consideration for a full implementation.
- **Verification (Placeholder)**: A verification step for `OrderProcessingResult` is mentioned in `reference-agent-flow.md` and commented out here. This would ensure the logical consistency of the order summary.
- **Complexity**: This agent is inherently more complex due to its interaction with multiple tools and the stateful nature of inventory. Robust error handling for tool calls and edge cases (e.g., product not found, API errors) is essential.
""" 