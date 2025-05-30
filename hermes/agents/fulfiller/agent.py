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


@traceable(run_type="chain", name="Order Processing Agent")
async def run_fulfiller(
    state: FulfillerInput, runnable_config: RunnableConfig
) -> WorkflowNodeOutput[Literal[Agents.FULFILLER], FulfillerOutput]:
    """Process customer order requests with stock checking and promotion application.

    Args:
        state: The input model containing classifier output and stockkeeper results
        runnable_config: Configuration for the runnable

    Returns:
        A WorkflowNodeOutput containing the processed order or an error

    """
    try:
        hermes_config = HermesConfig.from_runnable_config(runnable_config)
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
                "resolved_products": [
                    product.model_dump()
                    for product in stockkeeper_output.resolved_products
                ],
                "unresolved_mentions": [
                    mention.model_dump()
                    for mention in stockkeeper_output.unresolved_mentions
                ],
            },
            retry_prompt_template=DEFAULT_RETRY_TEMPLATE,
        )

        order_response = Order.model_validate(llm_response)

        # Ensure email_id is set
        if not order_response.email_id:
            order_response.email_id = analysis_dict.get("email_id", "unknown")

        # Process each order item for stock checking and inventory updates
        processed_items = []
        total_amount = 0.0

        for item in order_response.lines:
            # Check stock availability
            stock_status = check_stock(item.product_id, item.quantity)

            if isinstance(stock_status, StockStatus) and stock_status.is_available:
                # Update stock levels
                update_result = update_stock(item.product_id, item.quantity)

                if update_result == StockUpdateStatus.SUCCESS:
                    item.status = OrderLineStatus.CREATED
                    order_response.stock_updated = True
                    total_amount += (item.unit_price or item.base_price) * item.quantity
                else:
                    item.status = OrderLineStatus.OUT_OF_STOCK
                    # Find alternatives for out-of-stock items
                    alternatives_result = find_alternatives(
                        original_product_id=item.product_id, limit=3
                    )
                    if isinstance(alternatives_result, list):
                        item.alternatives = alternatives_result
            else:
                item.status = OrderLineStatus.OUT_OF_STOCK
                # Find alternatives for out-of-stock items
                alternatives_result = find_alternatives(
                    original_product_id=item.product_id, limit=3
                )
                if isinstance(alternatives_result, list):
                    item.alternatives = alternatives_result

            processed_items.append(item)

        # Update the order with processed items
        order_response.lines = processed_items
        order_response.total_price = total_amount

        # Extract promotion specs from the resolved products instead of using hardcoded ones
        promotion_specs = []
        for product in stockkeeper_output.resolved_products:
            if product.promotion is not None:
                promotion_specs.append(product.promotion)

        # Apply promotions to the order if any promotion specs were found
        if promotion_specs:
            final_order = apply_promotion(
                order=order_response,
                promotion_specs=promotion_specs,
            )
        else:
            # No promotions to apply, use the order as-is
            final_order = order_response

        # Create the output
        output = FulfillerOutput(
            order_result=final_order,
        )

        return create_node_response(Agents.FULFILLER, output)

    except Exception as e:
        raise RuntimeError(
            f"Fulfiller: Error during processing for email {state.email.email_id}"
        ) from e
