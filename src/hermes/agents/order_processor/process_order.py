"""
Main function for processing customer order requests.
"""

from typing import Dict, Any, Optional, Literal
from src.hermes.model import KeyedConfigDict
from langsmith import traceable
import json

from src.hermes.config import HermesConfig
from src.hermes.utils.llm_client import get_llm_client

from .models import OrderProcessorOutput, ProcessedOrder, OrderProcessorInput
from .prompts import get_prompt


@traceable(
    name="Order Processor Agent",
    description="Process order requests, check inventory, update stock, and suggest alternatives.",
)
async def process_order(
    state: OrderProcessorInput,
    runnable_config: Optional[
        KeyedConfigDict[
            Literal["configurable"], Dict[Literal["hermes_config"], HermesConfig]
        ]
    ] = None,
) -> OrderProcessorOutput:
    """
    Processes a customer order request based on the email analysis.

    Args:
        state (OrderProcessorInput): Input data containing email analysis for the order.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        OrderProcessorOutput: The output model containing the processed order information.
    """
    hermes_config = HermesConfig.from_runnable_config(runnable_config)

    # Extract email_id from the input state
    if state.email_id:
        email_id = state.email_id
    elif isinstance(state.email_analysis, dict) and "email_id" in state.email_analysis:
        email_id = state.email_analysis["email_id"]
    else:
        email_id = "unknown"

    print(f"Processing order request for email {email_id}")

    # Get the order processor prompt template
    order_processor_prompt = get_prompt("order_processor")

    # Use a strong model for order processing since it involves complex logic
    llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.0)

    try:
        # Create the chain with template
        processing_chain = order_processor_prompt | llm.with_structured_output(
            ProcessedOrder
        )

        # Prepare email analysis for the prompt
        email_analysis_data = state.email_analysis

        # Process the order
        order_result: ProcessedOrder = await processing_chain.ainvoke(
            {"email_analysis": json.dumps(email_analysis_data, indent=2)}
        )

        # Make sure the email_id is set correctly in the result
        if order_result.email_id != email_id:
            order_result.email_id = email_id

        print(f"  Order processing for {email_id} complete.")
        print(f"  Status: {order_result.overall_status}")
        print(f"  Items: {len(order_result.ordered_items)}")
        print(f"  Total price: {order_result.total_price}")

        return OrderProcessorOutput(order_result=order_result)

    except Exception as e:
        print(f"Error processing order for email {email_id}: {e}")
        # Return a fallback result in case of error
        fallback_order = ProcessedOrder(
            email_id=email_id,
            overall_status="no_valid_products",
            ordered_items=[],
            message=f"Error during order processing: {str(e)}",
            stock_updated=False,
        )
        return OrderProcessorOutput(order_result=fallback_order)
