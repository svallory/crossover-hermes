# Fulfiller Agent

The Fulfiller agent is responsible for processing customer order requests. It works with the output from the Stockkeeper agent and applies promotions based on configured specifications.

## Workflow

1. The Stockkeeper agent resolves product mentions from customer emails to actual catalog products
2. The Fulfiller agent receives the resolved products and processes them:
   - Checks stock availability using simplified `check_stock()` function
   - Creates order items for in-stock products with `OrderLineStatus.CREATED`
   - Sets out-of-stock items to `OrderLineStatus.OUT_OF_STOCK`
   - Updates inventory levels using `update_stock()` function
   - Suggests alternatives for out-of-stock items
3. The `apply_promotion` tool processes the ordered items with promotion specifications
   - Applies applicable promotions (quantity discounts, free items, etc.)
   - Calculates final prices with promotions applied
4. The results are formatted into an `Order` that can be used to respond to the customer

## Simplified Order Tools

The order processing uses streamlined tools optimized for the assignment scope:

### `check_stock(product_id, requested_quantity) -> StockStatus | ProductNotFound`

Returns only the essential information:
- `is_available: bool` - Whether the requested quantity is available
- `current_stock: int` - Current stock level for display

### `update_stock(product_id, quantity_to_decrement) -> StockUpdateStatus`

Returns a simple enum status:
- `StockUpdateStatus.SUCCESS` - Stock updated successfully
- `StockUpdateStatus.INSUFFICIENT_STOCK` - Not enough stock available
- `StockUpdateStatus.PRODUCT_NOT_FOUND` - Product ID not found

## Usage

The Fulfiller agent is integrated into the LangGraph workflow and uses the standardized agent pattern:

```python
from hermes.agents.fulfiller import run_fulfiller
from hermes.agents.fulfiller.models import FulfillerInput, FulfillerOutput

# Create input with classifier and stockkeeper outputs
fulfiller_input = FulfillerInput(
    email_id="customer-email-123",
    classifier=classifier_output,  # From classifier agent
    stockkeeper=stockkeeper_output  # From stockkeeper agent
)

# Process the order through the LangGraph workflow
result = await run_fulfiller(
    state=fulfiller_input,
    runnable_config=config
)

# The result contains the processed order with promotions applied
processed_order = result.fulfiller.processed_order
```

## LangGraph Integration

The agent leverages LangGraph's type safety guarantees:
- **Type-safe inputs**: LangGraph validates `FulfillerInput` before execution
- **Direct property access**: Uses `state.classifier.email_analysis.model_dump()` safely
- **Structured outputs**: Returns `WorkflowNodeOutput[Agents.FULFILLER, FulfillerOutput]`
- **Error handling**: Graceful error propagation through the workflow

## Assignment Requirements Fulfilled

The Fulfiller agent meets all assignment requirements:

1. **Verify product availability in stock** ✅
   - Uses `check_stock()` to verify availability
   - Returns boolean `is_available` status

2. **Create order lines with appropriate status** ✅
   - Sets `OrderLineStatus.CREATED` for available items
   - Sets `OrderLineStatus.OUT_OF_STOCK` for unavailable items

3. **Update stock levels after processing** ✅
   - Uses `update_stock()` to decrement inventory
   - Tracks success with `StockUpdateStatus.SUCCESS`

4. **Record each product request from emails** ✅
   - Processes all resolved products from stockkeeper
   - Maintains quantity and product details

## Key Functionality

- **Stock Verification**: Checks if requested products are available in the required quantities
- **Inventory Management**: Updates stock levels for fulfilled orders using enum-based status tracking
- **Alternative Products**: Suggests replacements for out-of-stock items based on category, season, and complementary factors
- **Promotion Processing**: Identifies and applies relevant product promotions

## Components

- `agent.py`: Main entry point with `run_fulfiller()` function for LangGraph integration
- `models.py`: Pydantic models for input/output data (`FulfillerInput`, `FulfillerOutput`)
- `prompts.py`: LLM prompts for order processing

## Integration Points

The Fulfiller Agent works within the Hermes system as follows:

1. Receives email analysis from the Classifier Agent via `FulfillerInput.classifier`
2. Receives resolved products from the Stockkeeper Agent via `FulfillerInput.stockkeeper`
3. Processes orders and updates inventory using simplified, type-safe tools
4. Returns structured output to the LangGraph workflow for the Composer Agent

The agent focuses specifically on order management, handling the business logic required to process customer purchase requests efficiently with minimal complexity suitable for the assignment scope. The implementation leverages LangGraph's type safety guarantees for clean, maintainable code.