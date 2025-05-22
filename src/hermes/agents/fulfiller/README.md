# Fulfiller Agent

The Fulfiller agent is responsible for processing customer order requests. It works with the output from the Stockkeeper agent and applies promotions based on configured specifications.

## Workflow

1. The Stockkeeper agent resolves product mentions from customer emails to actual catalog products
2. The Fulfiller agent receives the resolved products and processes them:
   - Checks stock availability
   - Creates order items for in-stock products
   - Suggests alternatives for out-of-stock items
   - Updates inventory levels
3. The `apply_promotion` tool processes the ordered items with promotion specifications
   - Applies applicable promotions (quantity discounts, free items, etc.)
   - Calculates final prices with promotions applied
4. The results are formatted into a `ProcessedOrder` that can be used to respond to the customer

## Usage

```python
from src.hermes.agents.stockkeeper import resolve_product_mentions
from src.hermes.agents.fulfiller import process_order
from src.hermes.model.promotions import PromotionSpec, PromotionConditions, PromotionEffects, DiscountSpec

# First, resolve product mentions using stockkeeper
stockkeeper_output = await resolve_product_mentions(classifier_output)

# Create promotion specifications
promotions = [
    PromotionSpec(
        conditions=PromotionConditions(min_quantity=2),
        effects=PromotionEffects(
            apply_discount=DiscountSpec(
                type="percentage", 
                amount=15.0
            )
        )
    ),
    # Add more promotion specs as needed
]

# Process the order with resolved products and promotions
processed_order = process_order(
    email_analysis=classifier_output,
    stockkeeper_output=stockkeeper_output,
    promotion_specs=promotions,
    email_id="customer-email-123"
)

# The processed_order now contains order items with promotions applied
```

## Promotion System

The promotion system uses a declarative approach with strongly-typed `PromotionSpec` objects that define:

1. **Conditions**: When a promotion should be applied (minimum quantity, product combinations, etc.)
2. **Effects**: What the promotion does (discounts, free items, free gifts, etc.)

This declarative approach makes it easy to:
- Add new promotion types
- Test promotion logic independently
- Apply multiple promotions in sequence
- Track which promotions were applied to which items

## Key Functionality

- **Stock Verification**: Checks if requested products are available in the required quantities
- **Inventory Management**: Updates stock levels for fulfilled orders
- **Alternative Products**: Suggests replacements for out-of-stock items based on category, season, and complementary factors
- **Promotion Processing**: Identifies and applies relevant product promotions

## Components

- `process_order.py`: Main entry point that processes an order request
- `models.py`: Pydantic models for input/output data
- `prompts.py`: LLM prompts for order processing

## Integration Points

The Order Processor Agent works within the Hermes system as follows:

1. Receives email analysis from the Email Analyzer Agent
2. Processes orders and updates inventory
3. Passes order processing results to the Response Composer Agent

The agent focuses specifically on order management, handling the business logic required to process customer purchase requests efficiently. 