# Agents

This directory contains the implementation of the specialized agents that form the Hermes system:

## 1. Email Analyzer Agent (classifier.py)

This agent serves as the entry point for all customer emails. It:

- Identifies language and analyzes the email's primary intent
- Extracts customer PII and signals
- Segments emails into inquiry, order, and personal statement parts
- Classifies emails as either "product inquiry" or "order request"
- Works with or without email subject lines
- Extracts product references using multiple strategies:
  - Direct ID matching
  - Name-based fuzzy matching
  - Context-based description matching
  - Handling of vague or formatted variations

The Email Analyzer establishes the context for all subsequent processing by producing a comprehensive `EmailAnalysis` that includes all product mentions found across all segments.

## 2. Product Resolver Agent (stockkeeper.py)

This agent takes product mentions from the Email Analyzer and converts them to actual catalog products. It:

- Deduplicates product mentions from all segments
- Resolves product mentions to actual catalog products using:
  - Exact ID matching (highest priority)
  - Fuzzy name matching using word similarity
  - Semantic vector search for description matching
- Provides confidence scores for each resolution
- Uses an LLM for disambiguation when multiple similar matches are found
- Tracks resolution metadata including method and confidence
- Collects unresolved product mentions for downstream processing

The Product Resolver produces a `ResolvedProductsOutput` containing successfully resolved products and any unresolved mentions.

## 3. Order Processor Agent (fulfiller.py)

This agent processes emails containing order requests. It:

- Uses resolved products from the Product Resolver
- Verifies stock availability for requested products
- Updates inventory levels for fulfilled orders
- Processes ordered items with individual status tracking
- Applies promotions using a declarative specification system
- Suggests alternatives for out-of-stock items based on:
  - Same category products
  - Season-appropriate alternatives
  - Complementary items
- Calculates total prices with promotions applied
- Provides detailed order status information

The Order Processor produces a detailed `ProcessedOrder` with information about the order's status and any issues encountered.

## 4. Inquiry Responder Agent (advisor.py)

This agent handles emails containing product inquiries. It:
- Uses resolved products from the Product Resolver
- Uses RAG (Retrieval-Augmented Generation) for semantic product search
- Extracts and classifies questions from inquiry segments
- Answers specific customer questions about products with factual information
- Identifies related products that might interest the customer based on objective criteria
- Handles season and occasion-specific product matching
- Processes mixed-intent emails that contain both inquiry and order segments
- Tracks unanswerable questions due to missing information

The Inquiry Responder produces an `InquiryAnswers` object containing factual, objective answers to customer questions.

## 5. Response Composer Agent (composer.py)

This agent takes the outputs from previous agents and creates the final response. It:
- Analyzes customer communication style to determine appropriate tone
- Adapts tone and style to match the customer's communication patterns
- Plans a logical response structure with appropriate greeting and closing
- Processes customer signals to personalize the response
- Ensures all questions and order aspects are addressed
- Generates natural-sounding, non-templated language
- Responds in the customer's original language
- Creates an appropriate subject line for the response email
- Provides structured response points for analysis

The Response Composer produces a `ComposedResponse` containing the final, personalized response text that will be sent to the customer.

## LangGraph Workflow Implementation

The agent communication flow is implemented using LangGraph's state graph API in the `workflow` directory. This implementation:

- Uses a `StateGraph` to define the workflow
- Implements sophisticated routing based on email content
- Maintains a comprehensive `OverallState` throughout the workflow
- Provides node wrapper functions to adapt agent interfaces
- Adds conditional routing based on email intent
- Tracks errors across the entire workflow
- Creates clean integration points between agents

The workflow is defined by the `workflow` object, which orchestrates the entire process from email analysis to final response generation.

## Agent Communication Architecture

```mermaid
flowchart TD
    Start([Start])
    Analyze[Email Analyzer]
    Stockkeeper[Product Resolver]
    Order[Order Processor]
    Inquiry[Inquiry Responder]
    Compose[Response Composer]
    End([End])

    Start --> Analyze
    Analyze -->|Extract Product Mentions| Stockkeeper
    Stockkeeper -->|Has Order & Inquiry| Order & Inquiry
    Stockkeeper -->|Has Order Only| Order
    Stockkeeper -->|Has Inquiry Only| Inquiry
    Stockkeeper -->|No Order/Inquiry| Compose
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
- **Input**: Raw email text with optional subject line
- **Output**: `EmailAnalysis` with intents, product mentions, and customer information
- **Implementation**: Uses LLM with structured output parsing

### Product Resolver

- **Purpose**: Deduplicate and convert product mentions to actual catalog products
- **Input**: Product mentions from Email Analyzer
- **Output**: `ResolvedProductsOutput` with resolved products and unresolved mentions
- **Implementation**: Uses cascading resolution strategy with vector search

### Order Processor

- **Purpose**: Process order requests and apply promotions
- **Input**: Email analysis, resolved products
- **Output**: `ProcessedOrder` with order status and item details
- **Implementation**: Uses stock checking tools and promotion specifications

### Inquiry Responder

- **Purpose**: Provide factual answers to product inquiries
- **Input**: Email analysis, resolved products
- **Output**: `InquiryAnswers` with factual answers to customer questions
- **Implementation**: Uses RAG with vector search for product information

### Response Composer

- **Purpose**: Generate the final personalized customer response
- **Input**: Outputs from all previous agents
- **Output**: `ComposedResponse` with complete email response
- **Implementation**: Uses strong LLM for natural language generation

## State Management

The system maintains a comprehensive `OverallState` object that accumulates outputs from each agent.
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