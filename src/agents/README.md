# Agents

This directory contains the implementation of the four specialized agents that form the Hermes system:

## 1. Email Analyzer Agent (email_classifier.py)

This agent serves as the entry point for all customer emails. It:
- Classifies emails as either "product inquiry" or "order request"
- Identifies language and analyzes communication tone
- Extracts product references (IDs, names, descriptions)
- Detects customer signals based on sales intelligence framework

The Email Analyzer establishes the context for all subsequent processing by producing a comprehensive `EmailAnalysis` that guides the workflow.

## 2. Order Processor Agent (order_processor.py)

This agent processes emails classified as order requests. It:
- Resolves product references to specific catalog items
- Verifies stock availability for requested products
- Updates inventory levels for fulfilled orders
- Suggests alternatives for out-of-stock items

The Order Processor produces a detailed `OrderProcessingResult` with information about the order's status and any issues encountered.

## 3. Inquiry Responder Agent (inquiry_responder.py)

This agent handles emails classified as product inquiries. It:
- Uses RAG (Retrieval-Augmented Generation) to find relevant product information
- Answers specific customer questions about products
- Identifies related products that might interest the customer
- Extracts key information for the response

The Inquiry Responder produces an `InquiryResponse` containing answers and product information.

## 4. Response Composer Agent (response_composer.py)

This agent takes the outputs from previous agents and creates the final response. It:
- Adapts tone and style to match the customer's communication
- Processes customer signals to personalize the response
- Ensures all questions and order aspects are addressed
- Generates natural-sounding, non-templated language

The Response Composer produces the final response text that will be sent to the customer.

## Agent Communication Architecture

```
Email Input
    │
    ▼
Email Analyzer
    │
    ├────────────┐
    │            │
    ▼            ▼
Order Processor  Inquiry Responder
    │            │
    │            │
    ▼            ▼
    └───► Response Composer
              │
              ▼
         Final Response
```

```python {cell}
# In this section, we'll implement the core agents for our email processing system.
# Each agent focuses on a specific task in the workflow, allowing for modular design
# and clear separation of concerns.
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
``` 