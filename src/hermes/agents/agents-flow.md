# Agents

This directory contains the implementation of the four specialized agents that form the Hermes system:

## 1. Email Analyzer Agent (email_analyzer.py)

This agent serves as the entry point for all customer emails. It:

- Identifies language
- Segments emails into inquiry, order, and personal statement parts
- Classifies emails as either "product inquiry" or "order request"
- Works with or without email subject lines
- Extracts product references using multiple strategies:
  - Direct ID matching
  - Name-based fuzzy matching
  - Context-based description matching
  - Handling of vague or formatted variations

The Email Analyzer establishes the context for all subsequent processing by producing a comprehensive `EmailAnalysisResult` that includes all product mentions found across all segments.

## 2. Product Resolver Agent (product_resolver.py)

This agent takes product mentions from the Email Analyzer and converts them to actual catalog products. It:

- Deduplicates product mentions from all segments
- Resolves product mentions to actual catalog products using:
  - Exact ID matching
  - Fuzzy name matching
  - Semantic vector search for description matching
- Provides confidence scores for each resolution
- Uses an LLM for disambiguation when multiple similar matches are found

The Product Resolver produces a `ResolvedProductsOutput` containing successfully resolved products and any unresolved mentions.

## 3. Order Processor Agent (order_processor.py)

This agent processes emails containing order requests. It:

- Uses resolved products from the Product Resolver
- Verifies stock availability for requested products
- Updates inventory levels for fulfilled orders
- Suggests alternatives for out-of-stock items based on:
  - Same category products
  - Season-appropriate alternatives
  - Complementary items
- Identifies and processes product promotions

The Order Processor produces a detailed `OrderProcessingResult` with information about the order's status and any issues encountered.

## 4. Inquiry Responder Agent (inquiry_responder.py)

This agent handles emails containing product inquiries. It:
- Uses resolved products from the Product Resolver
- Uses RAG (Retrieval-Augmented Generation) for semantic product search
- Answers specific customer questions about products
- Identifies related products that might interest the customer
- Handles season and occasion-specific product matching
- Processes mixed-intent emails that contain both inquiry and order segments

The Inquiry Responder produces an `InquiriesResponse` containing the answers for each inquiry.

## 5. Response Composer Agent (response_composer.py)

This agent takes the outputs from previous agents and creates the final response. It:
- Adapts tone and style to match the customer's communication
- Processes customer signals to personalize the response
- Ensures all questions and order aspects are addressed
- Generates natural-sounding, non-templated language
- Responds in the customer's original language
- Handles customer context, objections, and irrelevant information

The Response Composer produces the final response text that will be sent to the customer.

## LangGraph Workflow Implementation

The agent communication flow is implemented using LangGraph's functional API in `workflow.py`. This implementation:

- Uses the `@task` decorator to wrap each agent function
- Implements flexible routing based on email content
- Provides comprehensive error handling
- Maintains state throughout the workflow
- Uses memory checkpointing for potential continuation
- Follows a clear sequence of operations with conditional branches

The workflow is defined by the `hermes_workflow` function, which orchestrates the entire process from email analysis to final response generation.

## Agent Communication Architecture

```mermaid
flowchart TD
    Start([Start])
    Analyze[Email Analyzer]
    ProductResolver[Product Resolver]
    Order[Order Processor]
    Inquiry[Inquiry Responder]
    Compose[Response Composer]
    End([End])

    Start --> Analyze
    Analyze -->|Extract Product Mentions| ProductResolver
    ProductResolver -->|Has Order & Inquiry| Order & Inquiry
    ProductResolver -->|Has Order Only| Order
    ProductResolver -->|Has Inquiry Only| Inquiry
    ProductResolver -->|No Order/Inquiry| Compose
    Order --> Compose
    Inquiry --> Compose
    Compose --> End
```

# Hermes Agent Workflow

This document describes the flow of the Hermes agent system, showing how customer emails are processed through multiple specialized agents.

## Workflow Overview

The Hermes system uses a directed graph of specialized agents to process customer emails:

1. **Email Analyzer**: Analyzes and classifies the customer email, extracting intents, product mentions, and other key information.

2. **Product Resolver**: Takes product mentions from the Email Analyzer, deduplicates them, and resolves them against the product catalog to find exact matching products.

3. **Order Processor** (conditional): If the email contains an order request, processes the order using resolved products from the Product Resolver.

4. **Inquiry Responder** (conditional): If the email contains product inquiries, provides factual information about products using resolved products from the Product Resolver.

5. **Response Composer**: Combines outputs from the order processor and inquiry responder to generate a comprehensive response to the customer.

## Agent Descriptions

### Email Analyzer

- **Purpose**: Understand and extract structured information from customer emails
- **Input**: Raw email text 
- **Output**: Segmented analysis with intents, product mentions, and customer information
- **Implementation**: Uses LLM with structured output

### Product Resolver

- **Purpose**: Deduplicate and convert product mentions to actual catalog products
- **Input**: Product mentions from Email Analyzer
- **Output**: List of resolved products and unresolved mentions
- **Implementation**: Uses deduplication, exact matching, fuzzy matching, and embedding similarity

### Order Processor

- **Purpose**: Process order requests
- **Input**: Email analysis, resolved products
- **Output**: Order status with individual item details
- **Implementation**: Uses catalog tools, stock checking, and applies promotions

### Inquiry Responder

- **Purpose**: Provide factual answers to product inquiries
- **Input**: Email analysis, resolved products
- **Output**: Factual answers to customer questions
- **Implementation**: Uses RAG with vector search for product information

### Response Composer

- **Purpose**: Generate the final customer response
- **Input**: Outputs from Order Processor and/or Inquiry Responder
- **Output**: Complete customer response
- **Implementation**: Uses LLM with structured output

## State Management

The system maintains a comprehensive state object that accumulates outputs from each agent.
Nodes can access outputs from previous nodes, enabling contextual processing.

## Error Handling

Each agent includes error handling and fallback strategies. Errors are accumulated in the
state and can be used for diagnostic purposes.

```python {cell}
# In this section, we'll implement the core agents for our email processing system.
# Each agent focuses on a specific task in the workflow, allowing for modular design
# and clear separation of concerns.
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
``` 