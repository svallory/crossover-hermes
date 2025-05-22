# Hermes System Architecture

## Overview

Hermes is an automated customer service system that processes incoming customer emails, extracts relevant information, and generates appropriate responses. It uses a pipeline of specialized agents, each responsible for a specific aspect of email processing, coordinated through a LangGraph workflow.

The system handles two primary use cases:
1. **Product inquiries** - Answering customer questions about products
2. **Order processing** - Handling customer order requests

## System Components

### Agents

1. **Classifier (Email Analyzer)** - Analyzes incoming emails to determine intent, extract product mentions, and segment the content.
2. **Stockkeeper (Product Resolver)** - Resolves product mentions to actual products in the catalog.
3. **Advisor (Inquiry Responder)** - Handles product inquiries using RAG to provide factual answers.
4. **Fulfiller (Order Processor)** - Processes order requests, checking stock and applying promotions.
5. **Composer (Response Generator)** - Generates the final response email combining outputs from previous agents.

### Core Infrastructure

- **Vector Store** - ChromaDB-based vector database for semantic product search.
- **Workflow Management** - LangGraph-based orchestration of agent interactions.
- **Data Models** - Pydantic models for structured data representation throughout the system.

## Data Flow

1. Customer email enters the system and is passed to the Classifier.
2. Classifier analyzes the email, determining intent (inquiry, order, or both) and extracting product mentions.
3. Stockkeeper resolves product mentions to actual products in the catalog.
4. Based on the email intent:
   - For inquiries: Advisor processes questions and generates factual answers.
   - For orders: Fulfiller processes the order request, checking stock and applying promotions.
5. Composer generates a natural language response combining all relevant information.
6. Final response is returned to the customer.

## Key Design Patterns

- **Agent-based Architecture** - Specialized components with clearly defined responsibilities.
- **Retrieval Augmented Generation (RAG)** - Used for product inquiries to ensure factual accuracy.
- **Workflow Orchestration** - LangGraph manages the state and flow between agents.
- **Structured Data** - Pydantic models ensure type safety and data consistency.

## Technology Stack

- **Language Models** - Various LLMs with different strengths for different tasks.
- **Vector Database** - ChromaDB for semantic search.
- **Workflow Engine** - LangGraph for agent orchestration.
- **Data Structures** - Pydantic for structured data models. 