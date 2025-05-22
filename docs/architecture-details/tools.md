# Hermes Tools

The Hermes system includes several specialized tool modules that agents use to perform specific operations. These tools encapsulate functionality related to the product catalog, order processing, and promotions.

## Catalog Tools (`catalog_tools.py`)

Tools for searching and retrieving product information from the catalog.

### Key Functions:

- **`find_product_by_id`**: Retrieves a product from the catalog by its ID.
- **`find_product_by_name`**: Searches for products with names similar to the provided query.
- **`search_products_by_description`**: Performs semantic search on product descriptions.
- **`get_product_details`**: Retrieves comprehensive details for a specific product.

### Implementation:
- Uses a combination of exact matching, fuzzy matching, and vector search
- Integrates with the vector store for semantic similarity searches
- Returns structured `Product` objects with complete product information

## Order Tools (`order_tools.py`)

Tools for managing inventory and processing orders.

### Key Functions:

- **`check_stock`**: Verifies if a product has sufficient inventory for a requested quantity.
- **`update_stock`**: Decrements stock levels when an order is fulfilled.
- **`find_alternatives_for_oos`**: Suggests alternative products when an item is out of stock.
- **`extract_promotion`**: Identifies promotional offers in product descriptions.
- **`calculate_discount_price`**: Computes discounted prices based on promotions.

### Implementation:
- Provides real-time inventory management capabilities
- Includes validation to prevent errors in stock updates
- Uses pattern matching to identify promotions in text
- Returns `StockStatus` objects with availability information

### Error Handling:
- `ProductNotFound`: When a requested product doesn't exist
- Status codes in `StockUpdateResult` for tracking operation outcomes

## Promotion Tools (`promotion_tools.py`)

Tools for applying promotions and discounts to orders.

### Key Functions:

- **`apply_promotion`**: Processes a list of ordered items and applies eligible promotions.

### Promotion Types Supported:
- Percentage discounts (e.g., "25% off")
- Fixed amount discounts
- Quantity-based offers (buy X, get Y free)
- Free gifts with purchase
- Product combination offers

### Implementation:
- Takes order items and promotion specifications as input
- Applies relevant promotions based on conditions
- Calculates discounted prices and total discount amount
- Returns a fully processed `Order` object with all promotions applied

## Integration with Agents

These tools are used by the agents at various stages of the workflow:

1. **Product Resolver** uses catalog tools to match mentioned products to catalog items
2. **Order Processor** uses:
   - Order tools to check stock and update inventory
   - Promotion tools to apply discounts
3. **Inquiry Responder** uses catalog tools to retrieve product information

## Tool Design Principles

1. **Separation of Concerns**: Each tool has a specific, focused purpose
2. **Strong Typing**: Tools use Pydantic models for structured inputs and outputs
3. **Error Handling**: Each tool includes comprehensive validation and error reporting
4. **Reusability**: Tools are designed to be used across multiple agents
5. **JSON Serialization**: Tools accept and return serializable data for LLM compatibility

## Implementation Details

The tools are implemented as LangChain tools with JSON string inputs and structured outputs. This design allows them to be easily integrated with the LLM-based agents, providing a bridge between the language models and structured business logic. 