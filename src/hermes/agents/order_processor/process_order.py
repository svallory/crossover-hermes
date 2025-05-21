"""
Main function for processing customer order requests.
"""

from typing import Optional, Dict, Any, Literal
import json

from src.hermes.config import HermesConfig
from src.hermes.utils.llm_client import get_llm_client
from src.hermes.model.enums import Agents
from src.hermes.tools.order_tools import (
    check_stock, update_stock, find_alternatives_for_oos,
    StockStatus, ProductNotFound, StockUpdateResult, extract_promotion, PromotionDetails,
    calculate_discount_price, DiscountResult
)
from src.hermes.tools.catalog_tools import find_product_by_id, Product

from .models import ProcessedOrder, OrderedItemStatus
from .prompts import get_prompt


def calculate_promotion_discount(
    llm, 
    original_price: float, 
    promotion_text: str, 
    quantity: int = 1
) -> float:
    """
    Calculate the discounted price using the dedicated tool or fallback to LLM.
    
    Args:
        llm: The LLM client to use if needed
        original_price: The original unit price
        promotion_text: The promotion text
        quantity: The number of items
        
    Returns:
        The discounted unit price
    """
    try:
        # First try using the dedicated calculation tool
        result = calculate_discount_price(
            tool_input=json.dumps({
                "original_price": original_price,
                "promotion_text": promotion_text,
                "quantity": quantity
            })
        )
        
        if isinstance(result, DiscountResult) and result.discount_applied:
            # The tool successfully applied a discount
            return result.discounted_price
        
        # If there was no discount or the tool didn't work properly,
        # try using the LLM as a fallback
        promotion_prompt = get_prompt("PROMOTION_CALCULATOR")
        prompt_data = {
            "original_price": f"{original_price:.2f}",
            "promotion_text": promotion_text,
            "quantity": quantity
        }
        
        promotion_response = llm.invoke(promotion_prompt.format(**prompt_data))
        promotion_response_text = str(promotion_response).strip()
        
        # Try to extract a numeric value from the response
        try:
            # Remove any non-numeric characters except decimal point
            clean_response = ''.join(c for c in promotion_response_text if c.isdigit() or c == '.')
            if clean_response and '.' in clean_response:
                discounted_price = float(clean_response)
                # Only apply if it's a valid discount
                if 0 < discounted_price < original_price:
                    return round(discounted_price, 2)
        except (ValueError, TypeError):
            pass
            
        # If we couldn't extract a valid discounted price, return the original
        return original_price
    
    except Exception as e:
        print(f"Error calculating discount: {e}")
        # Return the original price if any error occurs
        return original_price


def process_order(
    email_analysis: Dict[str, Any],
    email_id: str = "unknown",
    model_strength: Literal["weak", "strong"] = "strong",
    temperature: float = 0.0,
    hermes_config: Optional[HermesConfig] = None,
) -> ProcessedOrder:
    """
    Processes a customer order request based on the email analysis.
    Simplified version for notebook usage.

    Args:
        email_analysis: Dictionary containing the email analysis
        email_id: ID of the email being processed
        model_strength: Strength of the LLM to use ('strong' or 'weak')
        temperature: Temperature setting for the LLM
        hermes_config: Optional HermesConfig instance

    Returns:
        ProcessedOrder object with the order processing results
    """
    try:
        print(f"Processing order request for email {email_id}")

        # Get the order processor prompt template
        order_processor_prompt = get_prompt(Agents.ORDER_PROCESSOR)

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
        else:
            # If it's an OverallState object or something with model_dump
            if hasattr(email_analysis, "model_dump"):
                analysis_dict = email_analysis.model_dump()
            elif hasattr(email_analysis, "email_analysis") and hasattr(email_analysis.email_analysis, "model_dump"):
                analysis_dict = email_analysis.email_analysis.model_dump()
            else:
                raise ValueError(f"Cannot extract email analysis from object of type {type(email_analysis)}")

        # Create processing chain including error handling
        order_processing_chain = order_processor_prompt | llm.with_structured_output(ProcessedOrder)

        # Generate order processing result
        response_data = order_processing_chain.invoke(
            {"email_analysis": json.dumps(analysis_dict, indent=2)}
        )

        # Handle the response properly with type checking
        if isinstance(response_data, ProcessedOrder):
            processed_order = response_data
        else:
            # If we got a dict, convert it to ProcessedOrder with required fields
            if isinstance(response_data, dict):
                # Make sure required fields are included
                response_data["email_id"] = email_id
                if "overall_status" not in response_data:
                    response_data["overall_status"] = "processed"
                processed_order = ProcessedOrder(**response_data)
            else:
                # Fallback if we got something unexpected
                processed_order = ProcessedOrder(
                    email_id=email_id,
                    overall_status="no_valid_products",
                    ordered_items=[],
                    message="Unexpected response type from order processing",
                    stock_updated=False,
                )

        # Make sure the email_id is set correctly in the result
        if processed_order.email_id != email_id:
            processed_order.email_id = email_id

        # Process the ordered items - check actual stock and set status
        if processed_order.ordered_items:
            # Reset total price to recalculate with correct promotions
            total_price = 0.0
            
            for item in processed_order.ordered_items:
                # Check actual stock
                try:
                    # Call the stock checking tool
                    stock_result = check_stock(
                        tool_input=json.dumps({
                            "product_id": item.product_id, 
                            "requested_quantity": item.quantity
                        })
                    )
                    
                    # Get product details including any promotions
                    product_result = find_product_by_id(
                        tool_input=json.dumps({
                            "product_id": item.product_id
                        })
                    )
                    
                    # Extract promotion information if available and product result is valid
                    if isinstance(product_result, Product):
                        # Use the extract_promotion tool to get promotion details
                        try:
                            promotion_result = extract_promotion(
                                tool_input=json.dumps({
                                    "product_description": product_result.description,
                                    "product_name": product_result.name
                                })
                            )
                            
                            # If promotion exists and has valid data
                            if isinstance(promotion_result, PromotionDetails) and promotion_result.has_promotion:
                                # Update or set the promotion text
                                if promotion_result.promotion_text:
                                    item.promotion = promotion_result.promotion_text
                        except Exception as e:
                            print(f"Error extracting promotion for {item.product_id}: {e}")
                    
                    # Handle response based on type
                    if isinstance(stock_result, StockStatus):
                        # In stock - update status and decrement stock
                        if stock_result.is_available:
                            item.status = OrderedItemStatus.CREATED
                            item.stock = stock_result.current_stock
                            
                            # Update the stock
                            update_result = update_stock(
                                tool_input=json.dumps({
                                    "product_id": item.product_id, 
                                    "quantity_to_decrement": item.quantity
                                })
                            )
                            
                            if isinstance(update_result, StockUpdateResult) and update_result.status == "success":
                                processed_order.stock_updated = True
                        else:
                            # Out of stock - set status and available stock
                            item.status = OrderedItemStatus.OUT_OF_STOCK
                            item.stock = stock_result.current_stock
                            
                            # Find alternatives
                            alternatives_result = find_alternatives_for_oos(
                                tool_input=json.dumps({
                                    "original_product_id": item.product_id, 
                                    "limit": 2
                                })
                            )
                            
                            if isinstance(alternatives_result, list) and alternatives_result:
                                item.alternatives = alternatives_result
                    elif isinstance(stock_result, ProductNotFound):
                        # Product not found - set to out of stock
                        item.status = OrderedItemStatus.OUT_OF_STOCK
                        item.stock = 0
                    else:
                        # Unexpected result - set to out of stock
                        item.status = OrderedItemStatus.OUT_OF_STOCK
                        item.stock = 0
                        
                    # Process promotions for this item if available
                    if item.promotion and item.price is not None and item.status == OrderedItemStatus.CREATED:
                        promotion_text = item.promotion
                        if isinstance(promotion_text, dict) and "text" in promotion_text:
                            promotion_text = promotion_text["text"]
                        elif not isinstance(promotion_text, str):
                            promotion_text = str(promotion_text)
                            
                        # Calculate the discounted price using our helper function
                        original_price = item.price
                        discounted_price = calculate_promotion_discount(
                            llm=llm,
                            original_price=original_price, 
                            promotion_text=promotion_text,
                            quantity=item.quantity
                        )
                        
                        # Only update if we got a valid discounted price
                        if discounted_price < original_price:
                            item.price = discounted_price
                    
                    # Recalculate item total price based on potentially updated item price
                    if item.price is not None and item.status == OrderedItemStatus.CREATED:
                        item.total_price = round(item.price * item.quantity, 2)
                        total_price += item.total_price
                    
                except Exception as e:
                    print(f"Error processing order item {item.product_id}: {e}")
                    # Default to out of stock if there's an error
                    item.status = OrderedItemStatus.OUT_OF_STOCK
                    item.stock = 0
            
            # Update the total price with our recalculated value
            processed_order.total_price = round(total_price, 2)

        print(f"  Order processing for {email_id} complete.")
        print(f"  Status: {processed_order.overall_status}")
        print(f"  Items: {len(processed_order.ordered_items)}")
        print(f"  Total price: {processed_order.total_price}")

        return processed_order

    except Exception as e:
        # Return a basic ProcessedOrder with error information
        error_message = f"Error processing order: {str(e)}"
        print(error_message)
        return ProcessedOrder(
            email_id=email_id,
            overall_status="no_valid_products",
            ordered_items=[],
            message=error_message,
            stock_updated=False,
        )
