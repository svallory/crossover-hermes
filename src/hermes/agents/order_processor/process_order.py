"""
Main function for processing customer order requests.
"""

from typing import Optional, Literal
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
import json

from src.hermes.config import HermesConfig
from src.hermes.utils.llm_client import get_llm_client
from src.hermes.model import WorkflowNodeOutput, Agents
from src.hermes.utils.errors import create_node_response

from .models import OrderProcessorOutput, ProcessedOrder, OrderProcessorInput
from .prompts import get_prompt


@traceable(
    run_type="chain",
    name="Order Processor Agent",
)
async def process_order(
    state: OrderProcessorInput,
    runnable_config: Optional[RunnableConfig] = None,
) -> WorkflowNodeOutput[Literal[Agents.ORDER_PROCESSOR], OrderProcessorOutput]:
    """
    Processes a customer order request based on the email analysis.

    Args:
        state (OrderProcessorInput): Input data containing email analysis for the order.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {Agents.PROCESS_ORDER: OrderProcessorOutput} or {"errors": Error}
    """
    try:
        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        # Extract email_id from the input state
        if state.email_id:
            email_id = state.email_id
        elif isinstance(state.email_analyzer.email_analysis, dict) and "email_id" in state.email_analyzer.email_analysis:
            email_id = state.email_id
        else:
            email_id = "unknown"

        print(f"Processing order request for email {email_id}")

        # Get the order processor prompt template
        order_processor_prompt = get_prompt(Agents.ORDER_PROCESSOR)

        # Use a strong model for order processing since it involves complex logic
        llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.0)

        try:
            # Create processing chain including error handling
            order_processing_chain = order_processor_prompt | llm.with_structured_output(ProcessedOrder)

            # Prepare email analysis for the prompt
            email_analysis_data = state.email_analyzer.email_analysis

            # Generate order processing result
            response_data = await order_processing_chain.ainvoke(
                {"email_analysis": json.dumps(email_analysis_data, indent=2)}
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

            print(f"  Order processing for {email_id} complete.")
            print(f"  Status: {processed_order.overall_status}")
            print(f"  Items: {len(processed_order.ordered_items)}")
            print(f"  Total price: {processed_order.total_price}")

            return create_node_response(
                Agents.ORDER_PROCESSOR,
                OrderProcessorOutput(order_result=processed_order)
            )

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
            return create_node_response(
                Agents.ORDER_PROCESSOR,
                OrderProcessorOutput(order_result=fallback_order)
            )

    except Exception as e:
        # Return errors in the format expected by LangGraph
        return create_node_response(Agents.ORDER_PROCESSOR, e)
