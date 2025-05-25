# Tools

This module provides specialized tools for our agents to interact with external systems and data.

## Organization

We've organized tools by their primary purpose:

1. **Catalog Tools** (`catalog_tools.py`):
   - For looking up and searching products in the catalog
   - Includes vector search capabilities for semantic retrieval

2. **Order Tools** (`order_tools.py`):
   - For inventory management (checking stock, updating quantities)
   - For finding alternatives to out-of-stock items
   - For extracting promotions from product descriptions

3. **Response Tools** (`response_tools.py`):
   - For analyzing customer communication tone
   - For extracting questions from text
   - For generating natural language responses

## Design Principles

Our tools follow these key design principles:

1. **Clearly Defined Purpose**: Each tool has a single, focused responsibility.

2. **LLM-Friendly Documentation**: We provide detailed docstrings with clear parameters and return values, helping LLMs understand how to use the tools.

3. **Strong Typing**: Using Pydantic models for inputs and outputs ensures robustness.

4. **Error Handling**: Tools return structured error objects instead of raising exceptions, making error flows more predictable.

5. **Statelessness**: Tools generally don't maintain state between calls, with the exception of required resources like database connections.

## Order Tools Implementation Notes

The order tools provide essential functionality for inventory management and order processing:

1. **Stock Management**:
   - `check_stock`: Verifies if a product has enough inventory for a requested quantity
   - `update_stock`: Decrements stock when an order is fulfilled, with validation to prevent errors

2. **Out-of-Stock Handling**:
   - `find_alternatives_for_oos`: Suggests alternative products when an item is unavailable
   - This improves customer satisfaction by offering options instead of just saying "out of stock"

3. **Promotion Detection**:
   - `extract_promotion`: Uses regex pattern matching to identify different types of promotions:
     - Percentage discounts (e.g., "25% off")
     - Buy-one-get-one offers
     - Free items
     - Limited-time offers
   - The promotion information is included in customer responses

4. **Promotion Calculation**:
   - `calculate_discount_price`: Calculates the actual discounted price based on promotion text
   - Handles various promotion types with different calculation methods
   - Returns detailed explanations of how discounts were applied

5. **Error Handling**: Each tool includes comprehensive validation and returns structured error objects:
   - `ProductNotFound`: When a requested product doesn't exist
   - Status codes in `StockUpdateResult`: For various operational outcomes

6. **Helper Functions**: The `extract_promotion_text` helper extracts full sentences containing promotions for natural-sounding responses.

These tools are designed to be called by the Fulfiller agent agent when processing customer order requests,
ensuring accurate inventory management and detailed order information.

**Scalability Note**: While pandas DataFrames are suitable for the current scale of this project,
for significantly larger product catalogs (e.g., 100,000+ products), direct DataFrame operations
for every lookup/update, especially stock updates, might become a performance bottleneck.
In such production scenarios, a dedicated database (SQL or NoSQL) for structured product data
and stock management, used in conjunction with the vector store, would be a more scalable approach.