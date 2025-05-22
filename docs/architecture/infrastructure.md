# Hermes Infrastructure

This document details the core infrastructure components that support the Hermes system.

## Vector Store

The `VectorStore` class in `vector_store.py` provides a singleton interface for interacting with ChromaDB:

**Key Responsibilities**:
- Initializes the ChromaDB database (in-memory or persistent)
- Creates and populates the product catalog collection
- Provides semantic search functionality for products
- Supports filtering by product attributes

**Implementation Details**:
- Uses OpenAI embeddings to vectorize product data
- Processes product data in batches for efficiency
- Singleton pattern ensures consistent database state

## Data Loading

The `load_data.py` file manages data acquisition for the system:

**Key Functions**:
- `load_sheet` - Fetches data from Google Sheets
- `load_products_df` - Loads product catalog data (with memoization)
- `load_email_df` - Loads email data for testing/training

**Data Sources**:
- Product catalog - Contains all available products with details
- Email dataset - Used for testing and development

## Core Data Models

### Product Models (`product.py`)

- `Product` - Represents a single product with details:
  - `product_id`, `name`, `description`, `category`
  - `product_type`, `seasons`, `base_price`, `stock`
  - Optional promotion information

- `AlternativeProduct` - For product recommendations:
  - Includes the product, similarity score, and recommendation reason

### Order Models (`order.py`)

- `OrderLineStatus` - Enum for item processing status (CREATED, OUT_OF_STOCK)
- `OrderLine` - Represents a single ordered item:
  - Product information (`product_id`, `description`)
  - Quantity and pricing (`quantity`, `base_price`, `unit_price`, `total_price`)
  - Processing information (`status`, `stock`, `alternatives`)
  - Promotion details (`promotion_applied`, `promotion_description`)

- `Order` - Represents a complete customer order:
  - `email_id`, `overall_status`, `lines` (list of OrderLine)
  - `total_price`, `total_discount`, `stock_updated`

### Promotion Models (`promotions.py`)

The promotion system uses a declarative approach:

- `PromotionConditions` - Defines when a promotion applies:
  - `min_quantity`, `applies_every`, `product_combination`

- `PromotionEffects` - Defines what the promotion does:
  - `free_items`, `free_gift`, `apply_discount`

- `DiscountSpec` - Specifies how a discount is applied:
  - `type` (percentage or fixed), `amount`, target product

- `PromotionSpec` - Combines conditions and effects:
  - Links conditions (when to apply) with effects (what to do)

### Error Models (`errors.py`)

- `ProductNotFound` - Signals a product could not be located:
  - `message`, `query_product_id`, `query_product_name`

### Enumerations (`enums.py`)

- `Agents` - Names of agents (CLASSIFIER, STOCKKEEPER, etc.)
- `Nodes` - LangGraph node names (Classifier, Stockkeeper, etc.)
- `ProductCategory` - Product categories (ACCESSORIES, BAGS, etc.)
- `Season` - Seasons for product availability (SPRING, SUMMER, etc.)

## LLM Integration

While not fully detailed in the notes, the system integrates with language models through:

- `get_llm_client` utility for obtaining appropriate LLM instances
- Model strength configuration (weak/strong) for different agent needs
- Structured output formatting for consistent agent outputs
- Different prompt templates for specialized tasks 