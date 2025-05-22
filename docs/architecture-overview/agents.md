# Hermes Agents

Hermes uses a system of specialized agents, each designed to handle a specific aspect of customer email processing. Below is a detailed overview of each agent, including their inputs, outputs, and responsibilities.

## Email Analyzer Agent (classifier)

**Purpose**: Analyzes and classifies customer emails to extract structured information.

**Input**: 
- `ClassifierInput`: Email ID, subject, and message content.

**Output**: 
- `ClassifierOutput`: Contains `EmailAnalysis` with:
  - Primary intent ("product inquiry" or "order request")
  - Language detection
  - Email segments (inquiry, order, personal statements)
  - Product mentions with extracted details
  - Customer signals

**Responsibilities**:
- Identify email language and primary intent
- Extract customer information
- Segment emails into functional parts
- Identify product mentions using various strategies
- Establish context for downstream processing

**Implementation**:
- Uses a weak LLM model for initial classification
- Produces a structured output format for consistent downstream processing

## Product Resolver Agent (stockkeeper)

**Purpose**: Resolves mentioned products to catalog items.

**Input**:
- `StockkeeperInput`: Contains the classifier output with product mentions

**Output**:
- `StockkeeperOutput`: Contains:
  - List of resolved products
  - List of unresolved mentions
  - Confidence scores and resolution methods

**Responsibilities**:
- Deduplicate product mentions from all email segments
- Match mentioned products to actual catalog items using:
  - Exact ID matching
  - Fuzzy name matching
  - Semantic vector search for descriptions
- Track resolution method and confidence

**Implementation**:
- Uses vector search for semantic matching of product descriptions
- Employs cascading resolution strategy for optimal matching

## Order Processor Agent (fulfiller)

**Purpose**: Processes order requests and manages inventory.

**Input**:
- `FulfillerInput`: Contains classifier output and stockkeeper resolved products

**Output**:
- `FulfillerOutput`: Contains:
  - `Order` with complete order processing results
  - Status for each ordered item
  - Price calculations and promotions applied

**Responsibilities**:
- Verify stock availability for requested products
- Apply relevant promotions and discounts
- Update inventory levels for fulfilled orders
- Suggest alternatives for out-of-stock items
- Calculate prices and discounts

**Implementation**:
- Uses order_tools for stock checking and updates
- Uses promotion_tools to apply appropriate discounts
- Tracks individual item status and overall order status

## Inquiry Responder Agent (advisor)

**Purpose**: Provide factual answers to product inquiries.

**Input**:
- `AdvisorInput`: Contains previous agent outputs with resolved products

**Output**:
- `AdvisorOutput`: Contains:
  - Factual answers to product inquiries
  - Reference information from product catalog

**Responsibilities**:
- Extract and analyze customer questions about products
- Retrieve relevant product information
- Generate factual, accurate responses to inquiries

**Implementation**:
- Uses RAG (Retrieval Augmented Generation) techniques
- Leverages vector search to find relevant product information
- Generates responses grounded in product facts

## Response Composer Agent (composer)

**Purpose**: Generate the final customer response email.

**Input**:
- `ComposerInput`: Contains all previous agent outputs

**Output**:
- `ComposerOutput`: Contains:
  - `ComposedResponse` with the final email response text

**Responsibilities**:
- Combine outputs from order processor and inquiry responder
- Generate a cohesive, natural language response
- Include all relevant order details, answers, and next steps
- Maintain appropriate tone and style

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