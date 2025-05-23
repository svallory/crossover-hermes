"""Main function for processing customer order requests."""

import json
from typing import Any, Literal, cast

from hermes.agents.stockkeeper.models import StockkeeperOutput
from hermes.config import HermesConfig
from hermes.model.enums import Agents
from hermes.model.order import OrderLine, Order, OrderLineStatus
from hermes.model.promotions import (
    PromotionSpec, 
    PromotionConditions, 
    PromotionEffects,
    DiscountSpec
)
from hermes.tools.catalog_tools import Product, find_product_by_id
from hermes.tools.order_tools import (
    ProductNotFound,
    StockStatus,
    StockUpdateResult,
    check_stock,
    update_stock,
    find_alternatives_for_oos,
)
from hermes.tools.promotion_tools import apply_promotion
from hermes.utils.llm_client import get_llm_client

from .prompts import get_prompt

def process_order(
    email_analysis: dict[str, Any],
    stockkeeper_output: StockkeeperOutput,
    promotion_specs: list[PromotionSpec],
    email_id: str = "unknown",
    model_strength: Literal["weak", "strong"] = "strong",
    temperature: float = 0.0,
    hermes_config: HermesConfig | None = None,
) -> Order:
    """Processes a customer order request based on the email analysis and stockkeeper results.

    Args:
        email_analysis: Dictionary containing the email analysis
        stockkeeper_output: Output from the stockkeeper agent with resolved products
        promotion_specs: List of promotion specifications to apply
        email_id: ID of the email being processed
        model_strength: Strength of the LLM to use ('strong' or 'weak')
        temperature: Temperature setting for the LLM
        hermes_config: Optional HermesConfig instance

    Returns:
        Order object with the order processing results
    """
    try:
        print(f"Processing order request for email {email_id}")

        # Get the order processor prompt template
        fulfiller_prompt = get_prompt(Agents.FULFILLER)

        # Use specified model for order processing
        if hermes_config is None:
            hermes_config = HermesConfig()

        llm = get_llm_client(config=hermes_config, model_strength=model_strength, temperature=temperature)

        # Handle OverallState or dictionary properly - extract just what we need
        analysis_dict = {}
        if isinstance(email_analysis, dict):
            # Extract the relevant parts without the full OverallState
            if "email_analysis" in email_analysis:
                # Handle nested structures
                if hasattr(email_analysis["email_analysis"], "model_dump"):
                    analysis_dict = email_analysis["email_analysis"].model_dump()
                else:
                    analysis_dict = email_analysis["email_analysis"]
            else:
                # Use the dict directly
                analysis_dict = email_analysis
        # If it's an OverallState object or something with model_dump
        elif hasattr(email_analysis, "model_dump"):
            analysis_dict = email_analysis.model_dump()
        elif hasattr(email_analysis, "email_analysis") and hasattr(email_analysis.email_analysis, "model_dump"):
            analysis_dict = email_analysis.email_analysis.model_dump()
        else:
            raise ValueError(f"Cannot extract email analysis from object of type {type(email_analysis)}")

        # Create processing chain including error handling
        order_processing_chain = fulfiller_prompt | llm.with_structured_output(Order)

        # Generate order processing result
        response_data = order_processing_chain.invoke({
            "email_analysis": json.dumps(analysis_dict, indent=2),
            "resolved_products": json.dumps(stockkeeper_output.model_dump(), indent=2)
        })

        # Handle the response properly with type checking
        if isinstance(response_data, Order):
            processed_order = response_data
        # If we got a dict, convert it to Order with required fields
        elif isinstance(response_data, dict):
            # Make sure required fields are included
            response_data["email_id"] = email_id
            if "overall_status" not in response_data:
                response_data["overall_status"] = "processed"
            processed_order = Order(**response_data)
        else:
            # Fallback if we got something unexpected
            processed_order = Order(
                email_id=email_id,
                overall_status="no_valid_products",
                lines=[],
                message="Unexpected response type from order processing",
                stock_updated=False,
                total_discount=0.0
            )

        # Make sure the email_id is set correctly in the result
        if processed_order.email_id != email_id:
            processed_order.email_id = email_id

        # Process the ordered items - check actual stock and set status
        if processed_order.lines:
            # Reset total price to recalculate with correct promotions
            total_price = 0.0
            order_items = []

            for line in processed_order.lines:
                # Check actual stock
                try:
                    # Call the stock checking tool
                    stock_result = check_stock(
                        tool_input=json.dumps({"product_id": line.product_id, "requested_quantity": line.quantity})
                    )

                    # Get product details
                    product_result = find_product_by_id(tool_input=json.dumps({"product_id": line.product_id}))

                    # Handle response based on type
                    if isinstance(stock_result, StockStatus):
                        # In stock - update status and decrement stock
                        if stock_result.is_available:
                            line.status = OrderLineStatus.CREATED
                            line.stock = stock_result.current_stock

                            # Create an order item dictionary for promotion processing
                            if isinstance(product_result, Product):
                                order_item = {
                                    "product_id": line.product_id,
                                    "description": line.description,
                                    "base_price": line.base_price or 0.0,
                                    "quantity": line.quantity
                                }
                                order_items.append(order_item)

                            # Update the stock
                            update_result = update_stock(
                                tool_input=json.dumps(
                                    {"product_id": line.product_id, "quantity_to_decrement": line.quantity}
                                )
                            )

                            if isinstance(update_result, StockUpdateResult) and update_result.status == "success":
                                processed_order.stock_updated = True
                                
                            # Add to the total price (before promotions)
                            if line.total_price is not None:
                                total_price += line.total_price
                                
                        else:
                            # Out of stock - set status and available stock
                            line.status = OrderLineStatus.OUT_OF_STOCK
                            line.stock = stock_result.current_stock

                            # Find alternatives
                            alternatives_result = find_alternatives_for_oos(
                                tool_input=json.dumps({"original_product_id": line.product_id, "limit": 2})
                            )

                            if isinstance(alternatives_result, list) and alternatives_result:
                                line.alternatives = alternatives_result
                    elif isinstance(stock_result, ProductNotFound):
                        # Product not found - set to out of stock
                        line.status = OrderLineStatus.OUT_OF_STOCK
                        line.stock = 0
                    else:
                        # Unexpected result - set to out of stock
                        line.status = OrderLineStatus.OUT_OF_STOCK
                        line.stock = 0

                except Exception as e:
                    print(f"Error processing item {line.product_id}: {e}")
                    # Set to out of stock in case of error
                    line.status = OrderLineStatus.OUT_OF_STOCK
                    line.stock = 0

            # Apply promotions if we have items in stock
            if order_items:
                try:
                    # Call the apply_promotion tool
                    order_result = apply_promotion(
                        tool_input=json.dumps({
                            "ordered_items": order_items,
                            "promotion_specs": [p.model_dump() for p in promotion_specs],
                            "email_id": email_id
                        })
                    )
                    
                    # Update the ordered items with promotion information from the result
                    if isinstance(order_result, Order):
                        # Update the lines with promotion information
                        for line in processed_order.lines:
                            for order_line in order_result.lines:
                                if line.product_id == order_line.product_id:
                                    # Add promotion information to the item
                                    if order_line.promotion_applied:
                                        promotion_desc = order_line.promotion_description
                                        if promotion_desc is not None:
                                            # Always create a PromotionSpec object since that's what OrderLine expects
                                            # Create a simple PromotionSpec with the promotion description
                                            line.promotion = PromotionSpec(
                                                conditions=PromotionConditions(min_quantity=1),
                                                effects=PromotionEffects(
                                                    free_gift=promotion_desc
                                                )
                                            )
                                    
                                    # Update price with promotional pricing
                                    if order_line.unit_price is not None:
                                        line.unit_price = order_line.unit_price
                                    if order_line.total_price is not None:
                                        line.total_price = order_line.total_price
                                    break
                        
                        # Update overall order with discount information
                        processed_order.total_discount = order_result.total_discount
                        processed_order.total_price = sum(
                            line.total_price for line in processed_order.lines 
                            if line.status == OrderLineStatus.CREATED and line.total_price is not None
                        )
                except Exception as e:
                    print(f"Error applying promotions: {e}")
                    # Use original prices if promotion application fails
                    processed_order.total_price = total_price
            else:
                # No items in stock, set total price to 0
                processed_order.total_price = 0.0

            # Determine overall status based on item statuses
            in_stock_count = sum(1 for line in processed_order.lines if line.status == OrderLineStatus.CREATED)
            total_count = len(processed_order.lines)
            
            if total_count == 0:
                processed_order.overall_status = "no_valid_products"
            elif in_stock_count == 0:
                processed_order.overall_status = "out_of_stock"
            elif in_stock_count < total_count:
                processed_order.overall_status = "partially_fulfilled"
            else:
                processed_order.overall_status = "created"

        return processed_order

    except Exception as e:
        print(f"Error processing order: {e}")
        # Return a basic error response
        return Order(
            email_id=email_id,
            overall_status="no_valid_products",
            lines=[],
            message=f"Error processing order: {str(e)}",
            stock_updated=False,
            total_discount=0.0
        )
