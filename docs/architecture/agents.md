# Hermes Agents

This document details each agent in the Hermes system, including their responsibilities, inputs, outputs, and key components.

## Classifier (Email Analyzer)

**Purpose**: Analyzes incoming customer emails to extract structured information.

**Key Responsibilities**:
- Identifies email language and primary intent (inquiry, order)
- Segments the email into logical sections
- Extracts product mentions with confidence scores
- Identifies customer signals (urgency, sentiment)
- Recognizes potential customer PII

**Input**: `ClassifierInput` - Email subject and message
**Output**: `ClassifierOutput` containing `EmailAnalysis`

**Key Components**:
- `agent.py` - Main function: `analyze_email`
- `models.py` - Data models: `ClassifierInput`, `ClassifierOutput`, `EmailAnalysis`, `Segment`, `ProductMention`
- `prompts.py` - LLM prompt template for email analysis

**LLM Usage**: Uses a "weak" model strength configured via `HermesConfig`

## Stockkeeper (Product Resolver)

**Purpose**: Resolves product mentions to actual products in the catalog.

**Key Responsibilities**:
- Resolves product mentions using exact ID match, fuzzy name matching, or vector search
- Handles ambiguity and deduplication using LLM for complex cases
- Assigns confidence scores to resolved products
- Identifies unresolved mentions

**Input**: `StockkeeperInput` - Contains `ClassifierOutput`
**Output**: `StockkeeperOutput` - List of resolved `Product` objects and unresolved mentions

**Key Components**:
- `agent.py` - Main function: `resolve_product_mentions`
- `models.py` - Data models: `StockkeeperInput`, `StockkeeperOutput`
- `prompts.py` - LLM prompts for disambiguation, deduplication, and alternatives

**Key Methods**:
- Cascading resolution strategy (exact ID → fuzzy name → LLM disambiguation)
- Uses DataFrame loaded from product catalog data

## Advisor (Inquiry Responder)

**Purpose**: Processes customer product inquiries using RAG to provide factual answers.

**Key Responsibilities**:
- Extracts customer questions from email analysis
- Leverages RAG with product catalog vector store
- Provides factual answers to product inquiries
- Identifies related products objectively
- Tracks unanswered questions

**Input**: `AdvisorInput` - Contains `ClassifierOutput` and optional `StockkeeperOutput`
**Output**: `AdvisorOutput` containing `InquiryAnswers`

**Key Components**:
- `agent.py` - Main function: `respond_to_inquiry`
- `models.py` - Data models: `AdvisorInput`, `AdvisorOutput`, `InquiryAnswers`, `QuestionAnswer`
- `prompts.py` - RAG prompt template for inquiry resolution

**LLM Usage**: Uses a "strong" model with product information context

## Fulfiller (Order Processor)

**Purpose**: Processes customer order requests, handling stock verification and promotions.

**Key Responsibilities**:
- Verifies stock availability for requested products
- Updates inventory levels for fulfilled orders
- Processes ordered items with individual status tracking
- Applies promotions based on specifications
- Suggests alternatives for out-of-stock items
- Calculates total prices with promotions applied

**Input**: `FulfillerInput` - Contains `ClassifierOutput` and optional `StockkeeperOutput`
**Output**: `FulfillerOutput` containing `Order`

**Key Components**:
- `agent.py` - Main function: `process_order`
- `models.py` - Data models: `FulfillerInput`, `FulfillerOutput`
- `prompts.py` - LLM prompts for order processing and promotion calculation

**External Tools**:
- `check_stock` - Verifies product availability
- `update_stock` - Updates inventory levels
- `find_alternatives_for_oos` - Suggests alternatives for out-of-stock items
- `apply_promotion` - Applies promotional rules to the order

## Composer (Response Generator)

**Purpose**: Generates the final customer response email.

**Key Responsibilities**:
- Analyzes customer communication style for tone matching
- Synthesizes information from previous agents
- Plans response structure based on content
- Personalizes response using customer signals
- Ensures all questions/order aspects are addressed
- Generates natural language in customer's language

**Input**: `ComposerInput` - Contains outputs from all previous agents
**Output**: `ComposerOutput` containing `ComposedResponse`

**Key Components**:
- `agent.py` - Main function: `compose_response`
- `models.py` - Data models: `ComposerInput`, `ComposerOutput`, `ComposedResponse`, `ResponseTone`, `ResponsePoint`
- `prompts.py` - LLM prompt template for response composition

**LLM Usage**: Configured based on `HermesConfig` 