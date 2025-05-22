# Hermes Data Models

The Hermes system uses a set of structured data models (Pydantic classes) to represent and validate data throughout the workflow. These models define the shape and constraints of data flowing between agents.

> **Note**: For detailed code examples and complete data structures, please refer to [Data Flow](data-flow.md).

## Core Models

### `Order` (`order.py`)

The central model representing a complete customer order with processing results.

**Key Fields**:
- `email_id`: Identifier for the email containing the order request
- `overall_status`: Status of the entire order (created, out_of_stock, partially_fulfilled, no_valid_products)
- `lines`: List of `OrderLine` items in this order
- `total_price`: Calculated total price for all available items
- `total_discount`: Total discount amount applied
- `message`: Additional information about processing results
- `stock_updated`: Flag indicating whether stock levels were updated

### `OrderLine` (`order.py`)

Represents a single line item in an order.

**Key Fields**:
- **Core fields**: `product_id`, `description`, `quantity` 
- **Price fields**: `base_price`, `unit_price`, `total_price`
- **Status fields**: `status`, `stock`
- **Promotion fields**: `promotion_applied`, `promotion_description`, `promotion`
- **Alternative products**: `alternatives` - List of alternative products if out of stock

### `Product` (`product.py`)

Represents a product in the catalog.

**Key Fields**:
- `id`: Unique product identifier
- `name`: Product name
- `description`: Detailed product description
- `price`: Current product price
- `category`: Product category
- `attributes`: Additional product attributes
- `seasons`: List of seasons when the product is available
- `stock`: Current inventory level
- `promotion`: Information about any active promotion

### `AlternativeProduct` (`product.py`)

Represents an alternative product suggestion.

**Key Fields**:
- `product_id`: Identifier of the alternative product
- `name`: Name of the alternative product
- `price`: Price of the alternative product
- `similarity_score`: Score indicating similarity to the requested product
- `reason`: Explanation of why this alternative is suggested

### `PromotionSpec` (`promotions.py`)

Defines a promotion and its application conditions.

**Key Fields**:
- `conditions`: `PromotionConditions` object defining when the promotion applies
- `effects`: `PromotionEffects` object defining what the promotion does

#### `PromotionConditions`
- `min_quantity`: Minimum quantity required to activate the promotion
- `product_combination`: List of product IDs that must be purchased together
- `applies_every`: Apply promotion every N items

#### `PromotionEffects`
- `apply_discount`: Discount specification (percentage or fixed amount)
- `free_items`: Number of free items given with qualifying purchase
- `free_gift`: Description of a free gift with purchase

## Agent Input/Output Models

Each agent has specialized input and output models for structured interaction. See [Data Flow](data-flow.md) for complete implementation details.

### Classifier Models
- `ClassifierInput`: Email ID, subject, and message
- `ClassifierOutput`: Email analysis results, primary intent, and segments
- `EmailAnalysis`: Detailed analysis of the email content
- `Segment`: Logical section of the email (inquiry, order, personal)
- `ProductMention`: Reference to a product found in the email

### Stockkeeper Models
- `StockkeeperInput`: Contains classifier output for product resolution
- `StockkeeperOutput`: Resolved products and unresolved mentions

### Fulfiller Models
- `FulfillerInput`: Contains classifier and stockkeeper output
- `FulfillerOutput`: Complete order processing results

### Advisor Models
- `AdvisorInput`: Contains classifier and stockkeeper output for inquiry processing
- `AdvisorOutput`: Factual answers to product inquiries
- `InquiryAnswers`: Collection of question-answer pairs
- `ExtractedQuestion`: Question identified in the email
- `QuestionAnswer`: Pairing of question and factual answer

### Composer Models
- `ComposerInput`: Contains all previous agent outputs
- `ComposerOutput`: Final composed response for the customer
- `ComposedResponse`: Structured response with tone and content information
- `ResponseTone`: Enumeration of possible response tones
- `ResponsePoint`: Individual point to address in the response

## Workflow State Models

### `OverallState`

Comprehensive state object that tracks the progression of an email through the workflow.

**Key Fields**:
- Email metadata: `email_id`, `subject`, `message`
- Agent outputs: `classifier`, `stockkeeper`, `fulfiller`, `advisor`, `composer`
- `errors`: Dictionary tracking errors from each agent

## Utility Models

### `Error` (`error.py`)

Represents an error that occurred during processing.

**Key Fields**:
- `message`: Description of the error
- `source`: The agent or component where the error occurred

### Enumerations (`enums.py`)

Defines enumerated types used across the system:

- `Agents`: Names of agents in the workflow (classifier, stockkeeper, etc.)
- `Nodes`: LangGraph node names (Classifier, Stockkeeper, etc.)
- `ProductCategory`: Product categories (ACCESSORIES, BAGS, etc.)
- `Season`: Seasons for product availability (SPRING, SUMMER, etc.)
- `ResponseTone`: Tone options for customer responses

## Model Design Principles

1. **Validation**: Models enforce data validation using Pydantic
2. **Progressive Enrichment**: Models start with minimal fields and are progressively enriched
3. **Clear Documentation**: Fields include descriptive documentation
4. **Type Safety**: Strong typing used throughout to catch errors early
5. **Default Values**: Sensible defaults provided where appropriate
6. **Serialization**: Models are JSON-serializable for LLM compatibility

The models serve as both a contract between components and a validation mechanism to ensure data integrity throughout the system's workflow. 