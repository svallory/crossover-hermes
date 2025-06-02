"""Main function for processing customer order requests."""

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from .models import FulfillerInput, FulfillerOutput
from hermes.agents.stockkeeper.models import StockkeeperOutput
from hermes.config import HermesConfig
from hermes.model.order import Order, OrderLineStatus
from hermes.tools.catalog_tools import (
    find_alternatives,
)
from hermes.tools.order_tools import (
    check_stock,
    update_stock,
    StockUpdateStatus,
    StockStatus,
)
from hermes.tools.promotion_tools import apply_promotion
from hermes.utils.response import create_node_response
from hermes.utils.llm_client import get_llm_client
from hermes.utils.tool_error_handler import ToolCallRetryHandler, DEFAULT_RETRY_TEMPLATE
from hermes.workflow.types import WorkflowNodeOutput
from hermes.model.enums import Agents
from .prompts import FULFILLER_PROMPT
from hermes.utils.logger import logger, get_agent_logger

CLARIFICATION_MARKER = "[CLARIFICATION NEEDED:"


@traceable(run_type="chain", name="Order Processing Agent")
async def run_fulfiller(
    state: FulfillerInput, config: RunnableConfig
) -> WorkflowNodeOutput[Literal[Agents.FULFILLER], FulfillerOutput]:
    """Process customer order requests with stock checking and promotion application.

    Args:
        state: The input model containing classifier output and stockkeeper results
        config: Configuration for the runnable

    Returns:
        A WorkflowNodeOutput containing the processed order or an error

    """
    agent_name = Agents.FULFILLER.value.capitalize()
    email_id = state.email.email_id
    logger.info(
        get_agent_logger(
            agent_name, f"Processing order for email [cyan]{email_id}[/cyan]"
        )
    )

    try:
        hermes_config = HermesConfig.from_runnable_config(config)
        llm = get_llm_client(
            config=hermes_config,
            schema=Order,
            tools=[],
            model_strength="strong",
            temperature=0.0,
        )

        # Extract email analysis - LangGraph guarantees type safety
        analysis_dict = state.classifier.email_analysis.model_dump()

        # Extract stockkeeper output
        stockkeeper_output: StockkeeperOutput = state.stockkeeper

        # Create the chain for order processing
        chain = FULFILLER_PROMPT | llm

        # Use the retry handler
        retry_handler = ToolCallRetryHandler(max_retries=2, backoff_factor=0.0)

        # Process the order using the LLM
        llm_response = await retry_handler.retry_with_tool_calling(
            chain=chain,
            input_data={
                "email_analysis": analysis_dict,
                "candidate_products_for_mention": [
                    {
                        "original_mention": mention.model_dump(),
                        "candidates": [p.model_dump(exclude_none=True) for p in prods],
                    }
                    for mention, prods in stockkeeper_output.candidate_products_for_mention
                ],
                "unresolved_mentions": [
                    mention.model_dump()
                    for mention in stockkeeper_output.unresolved_mentions
                ],
            },
            retry_prompt_template=DEFAULT_RETRY_TEMPLATE,
        )

        # DISABLED TO TEST IF THE NEW PROMPT SOLVES THIS
        # # Pre-validation cleanup for OrderLine.promotion issues
        # if isinstance(llm_response, dict) and "lines" in llm_response:
        #     for line_idx, line_dict in enumerate(llm_response.get("lines", [])):
        #         if isinstance(line_dict, dict) and "promotion" in line_dict and line_dict["promotion" ] is not None:
        #             promo_spec_data = line_dict["promotion"]
        #             if isinstance(promo_spec_data, dict):
        #                 conditions_data = promo_spec_data.get("conditions")
        #                 effects_data = promo_spec_data.get("effects")
        #
        #                 # Determine if conditions are effectively empty
        #                 empty_conditions = False
        #                 if conditions_data is None: # Explicitly null conditions
        #                     empty_conditions = True
        #                 elif isinstance(conditions_data, dict):
        #                     # Check if all known condition fields are absent or None
        #                     if not any(conditions_data.get(f) for f in ["min_quantity", "applies_every", "product_combination"]):
        #                         empty_conditions = True
        #
        #                 # Determine if effects are effectively empty
        #                 empty_effects = False
        #                 if effects_data is None: # Explicitly null effects
        #                     empty_effects = True
        #                 elif isinstance(effects_data, dict):
        #                     if not any(effects_data.get(f) for f in ["free_items", "free_gift", "apply_discount"]):
        #                         empty_effects = True
        #
        #                 # If an LLM provides a promotion spec, but it's effectively empty (both conditions and effects are empty)
        #                 # then it likely means no promotion should be applied. This is a safeguard.
        #                 if (empty_conditions and empty_effects) or \
        #                    (empty_conditions and not promo_spec_data.get("effects")): # Handles cases where effects might be missing entirely if conditions were empty
        #                     logger.warning(
        #                         get_agent_logger(
        #                             agent_name,
        #                             f"OrderLine {line_idx} for product '{line_dict.get('product_id', 'unknown')}' had an effectively empty PromotionSpec (empty conditions and effects). Setting promotion to None."
        #                         )
        #                     )
        #                     line_dict["promotion"] = None
        #                 elif empty_conditions and not empty_effects:
        #                      logger.warning(
        #                         get_agent_logger(
        #                             agent_name,
        #                             f"OrderLine {line_idx} for product '{line_dict.get('product_id', 'unknown')}' had empty conditions but non-empty effects. This is likely invalid. Setting promotion to None as a safeguard."
        #                         )
        #                     )
        #                      line_dict["promotion"] = None # Invalid state, nullify

        order_response = Order.model_validate(llm_response)

        # Ensure email_id is set
        if not order_response.email_id:
            order_response.email_id = analysis_dict.get("email_id", "unknown")

        # Process each order item for stock checking and inventory updates
        processed_items = []
        total_amount = 0.0
        needs_clarification_present = any(
            CLARIFICATION_MARKER in item.description
            for item in order_response.lines
            if item.description
        )

        for item in order_response.lines:
            # Skip stock check and updates for items needing clarification
            if item.description and CLARIFICATION_MARKER in item.description:
                item.status = (
                    OrderLineStatus.OUT_OF_STOCK
                )  # Confirm status as per prompt convention
                item.alternatives = []  # Ensure no alternatives are added here
                processed_items.append(item)
                continue  # Skip to next item, do not add to total_amount or update stock

            # Check stock availability
            stock_status = check_stock(item.product_id, item.quantity)

            if isinstance(stock_status, StockStatus) and stock_status.is_available:
                # Update stock levels
                update_result = update_stock(item.product_id, item.quantity)
                # item.stock = stock_status.current_stock # Old logic

                if update_result == StockUpdateStatus.SUCCESS:
                    item.status = OrderLineStatus.CREATED
                    # Set item.stock to the stock *after* this line's quantity is decremented
                    item.stock = stock_status.current_stock - item.quantity
                    order_response.stock_updated = True
                    total_amount += (item.unit_price or item.base_price) * item.quantity
                else:
                    # Update failed (e.g. stock changed between check and update, or product not found by update_stock)
                    item.status = OrderLineStatus.OUT_OF_STOCK
                    # Stock remains what it was when checked, as the decrement failed.
                    item.stock = stock_status.current_stock
                    # Find alternatives for out-of-stock items
                    alternatives_result = find_alternatives.invoke(
                        {
                            "original_product_id": item.product_id,
                            "limit": 3,
                        }
                    )
                    if isinstance(alternatives_result, list):
                        item.alternatives = alternatives_result
            else:  # Not available from the start
                item.status = OrderLineStatus.OUT_OF_STOCK
                if isinstance(stock_status, StockStatus):
                    item.stock = (
                        stock_status.current_stock
                    )  # Stock was already insufficient or zero
                else:  # ProductNotFound from check_stock
                    item.stock = (
                        0  # Product not found, so effectively 0 stock for this item
                    )
                    # Ensure alternatives are still sought if appropriate for ProductNotFound
                    if item.product_id:  # Check if product_id was set on the item
                        alternatives_result = find_alternatives.invoke(
                            {
                                "original_product_id": item.product_id,
                                "limit": 3,
                            }
                        )
                        if isinstance(alternatives_result, list):
                            item.alternatives = alternatives_result
                    else:  # No product_id, cannot find alternatives
                        item.alternatives = []

            processed_items.append(item)

        # Update the order with processed items
        order_response.lines = processed_items
        order_response.total_price = total_amount

        # Determine overall_status based on new logic in prompt
        # The LLM should set this, but we can have a fallback/adjustment logic if needed.
        # For now, we trust the LLM to follow prompt guideline 9 for overall_status.
        # If items needing clarification are the *only* items, LLM should set to "needs_clarification"
        # If there are resolved_products, their status determines overall_status mainly.

        # Extract promotion specs from the ORDER LINES created by the LLM
        # The LLM should have been instructed to include promotion details from the selected candidate
        # in the OrderLine it generated.
        promotion_specs = []
        for line in (
            order_response.lines
        ):  # Iterate over lines in the order potentially modified by stock checks
            if line.promotion:  # Assuming OrderLine model has a 'promotion' field of type PromotionSpec | None
                promotion_specs.append(line.promotion)

        # Apply promotions to the order if any promotion specs were found
        if promotion_specs:
            final_order = apply_promotion(
                order=order_response,
                promotion_specs=promotion_specs,
            )
        else:
            # No promotions to apply, use the order as-is
            final_order = order_response

        # Create the final FulfillerOutput
        fulfiller_output = FulfillerOutput(
            order_result=final_order,
            unresolved_mentions=state.stockkeeper.unresolved_mentions,
            stockkeeper_metadata=state.stockkeeper.metadata,
            candidate_products_for_mention=state.stockkeeper.candidate_products_for_mention,
        )

        logger.info(
            get_agent_logger(
                agent_name,
                f"Order processing complete for email [cyan]{email_id}[/cyan]. Order status: [yellow]{final_order.overall_status}[/yellow]",
            )
        )

        return create_node_response(Agents.FULFILLER, fulfiller_output)

    except Exception as e:
        error_message = f"Error in {agent_name} for email {email_id}: {e}"
        logger.error(get_agent_logger(agent_name, error_message), exc_info=True)
        raise RuntimeError(
            f"Fulfiller: Error during processing for email {state.email.email_id}"
        ) from e
