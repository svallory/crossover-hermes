# Order Processor Agent

The Order Processor is responsible for handling customer order requests extracted from emails. It verifies product availability, updates inventory, and suggests alternatives for out-of-stock items.

## Key Functionality

- **Stock Verification**: Checks if requested products are available in the required quantities
- **Inventory Management**: Updates stock levels for fulfilled orders
- **Alternative Products**: Suggests replacements for out-of-stock items based on category, season, and complementary factors
- **Promotion Processing**: Identifies and applies relevant product promotions

## Components

- `process_order.py`: Main entry point that processes an order request
- `models.py`: Pydantic models for input/output data
- `prompts.py`: LLM prompts for order processing

## Usage Example

```python
from src.hermes.agents.fulfiller import process_order, ProcessOrderInput

# Create input from email analysis
input_data = ProcessOrderInput(
    email_analysis={
        "email_id": "order-123",
        "products": [
            {"product_id": "ABC123", "name": "Winter Jacket", "quantity": 2}
        ]
    }
)

# Process the order
result = await process_order(input_data)

# Check results
print(f"Order status: {result.overall_status}")
for item in result.ordered_items:
    print(f"Item: {item.product_name}, Status: {item.status}")
    if item.status == "out_of_stock":
        print(f"Alternatives: {[alt.name for alt in item.alternatives]}")
```

## Integration Points

The Order Processor Agent works within the Hermes system as follows:

1. Receives email analysis from the Email Analyzer Agent
2. Processes orders and updates inventory
3. Passes order processing results to the Response Composer Agent

The agent focuses specifically on order management, handling the business logic required to process customer purchase requests efficiently. 