# Hermes Agents

Hermes uses a system of specialized agents, each designed to handle a specific aspect of customer email processing. Below is a detailed overview of each agent, including their inputs, outputs, responsibilities, and implementation details.

## Classifier (Email Analyzer)

**Purpose**: Analyzes incoming customer emails to extract structured information.

**Key Responsibilities**:
- Identifies email language and primary intent (inquiry, order)
- Segments the email into logical sections (inquiry, order, personal statements)
- Extracts product mentions with confidence scores
- Identifies customer signals (urgency, sentiment)
- Recognizes potential customer PII

**Input**: 
- `ClassifierInput`: Email ID, subject, and message content.

**Output**: 
- `ClassifierOutput`: Contains `EmailAnalysis` with:
  - Primary intent ("product inquiry" or "order request")
  - Language detection
  - Email segments (inquiry, order, personal statements)
  - Product mentions with extracted details
  - Customer signals

**Key Components**:
- `agent.py` - Main function: `analyze_email`
- `models.py` - Data models: `ClassifierInput`, `ClassifierOutput`, `EmailAnalysis`, `Segment`, `ProductMention`
- `prompts.py` - LLM prompt template for email analysis

**Implementation**:
- Uses a weak LLM model for initial classification
- Produces a structured output format for consistent downstream processing

## Stockkeeper (Product Resolver)

**Purpose**: Resolves mentioned products to catalog items.

**Key Responsibilities**:
- Resolves product mentions using exact ID match, fuzzy name matching, or vector search
- Handles ambiguity and deduplication using LLM for complex cases
- Assigns confidence scores to resolved products
- Identifies unresolved mentions
- Deduplicate product mentions from all email segments

**Input**:
- `StockkeeperInput`: Contains the classifier output with product mentions

**Output**:
- `StockkeeperOutput`: Contains:
  - List of resolved products
  - List of unresolved mentions
  - Confidence scores and resolution methods
  - Metadata about the resolution process

**Key Components**:
- `agent.py` - Main function: `resolve_product_mentions`
- `models.py` - Data models: `StockkeeperInput`, `StockkeeperOutput`
- `prompts.py` - LLM prompts for disambiguation, deduplication, and alternatives

**Implementation**:
- Uses vector search for semantic matching of product descriptions
- Employs cascading resolution strategy (exact ID → fuzzy name → LLM disambiguation)
- Uses a DataFrame loaded from product catalog data

## Advisor (Inquiry Responder)

**Purpose**: Provide factual answers to product inquiries.

**Key Responsibilities**:
- Extracts customer questions from email analysis
- Leverages RAG with product catalog vector store
- Provides factual answers to product inquiries
- Identifies related products objectively
- Tracks unanswered questions

**Input**:
- `AdvisorInput`: Contains previous agent outputs with resolved products

**Output**:
- `AdvisorOutput`: Contains:
  - Factual answers to product inquiries
  - Reference information from product catalog
  - List of unanswered questions
  - Related products

**Key Components**:
- `agent.py` - Main function: `respond_to_inquiry`
- `models.py` - Data models: `AdvisorInput`, `AdvisorOutput`, `InquiryAnswers`, `QuestionAnswer`
- `prompts.py` - RAG prompt template for inquiry resolution

**Implementation**:
- Uses RAG (Retrieval Augmented Generation) techniques
- Leverages vector search to find relevant product information
- Generates responses grounded in product facts
- Uses a "strong" model with product information context

## Fulfiller (Order Processor)

**Purpose**: Processes order requests and manages inventory.

**Key Responsibilities**:
- Verifies stock availability for requested products
- Updates inventory levels for fulfilled orders
- Processes ordered items with individual status tracking
- Applies promotions based on specifications
- Suggests alternatives for out-of-stock items
- Calculates total prices with promotions applied

**Input**:
- `FulfillerInput`: Contains classifier output and stockkeeper resolved products

**Output**:
- `FulfillerOutput`: Contains:
  - `Order` with complete order processing results
  - Status for each ordered item
  - Price calculations and promotions applied

**Key Components**:
- `agent.py` - Main function: `process_order`
- `models.py` - Data models: `FulfillerInput`, `FulfillerOutput`
- `prompts.py` - LLM prompts for order processing and promotion calculation

**Implementation**:
- Uses order_tools for stock checking and updates
- Uses promotion_tools to apply appropriate discounts
- Tracks individual item status and overall order status

**External Tools**:
- `check_stock` - Verifies product availability
- `update_stock` - Updates inventory levels
- `find_alternatives_for_oos` - Suggests alternatives for out-of-stock items
- `apply_promotion` - Applies promotional rules to the order

## Composer (Response Generator)

**Purpose**: Generate the final customer response email.

**Key Responsibilities**:
- Analyzes customer communication style for tone matching
- Synthesizes information from previous agents
- Plans response structure based on content
- Personalizes response using customer signals
- Ensures all questions/order aspects are addressed
- Generates natural language in customer's language

**Input**:
- `ComposerInput`: Contains all previous agent outputs

**Output**:
- `ComposerOutput`: Contains:
  - `ComposedResponse` with the final email response text
  - Response tone and structure information
  - List of response points addressing customer needs

**Key Components**:
- `agent.py` - Main function: `compose_response`
- `models.py` - Data models: `ComposerInput`, `ComposerOutput`, `ComposedResponse`, `ResponseTone`, `ResponsePoint`
- `prompts.py` - LLM prompt template for response composition

**Implementation**:
- Uses a strong LLM for natural language generation
- Combines order details and inquiry answers into a unified response
- Personalized based on customer information

## Agent Communication

The agents communicate through the LangGraph state management system. Each agent's output becomes part of the overall state object (`OverallState`), and subsequent agents have access to this accumulated state. This allows for contextual processing where later agents can leverage insights from earlier agents.

## Model Selection Strategy

Hermes employs a tiered approach to model selection:

- **Weak Models**: Used for simpler, structuring tasks (classification)
- **Strong Models**: Used for complex, generation tasks (composing responses)

This optimization balances performance and cost, using more powerful models only where their capabilities are most needed. 