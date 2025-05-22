# Hermes Architecture Documentation

This folder contains comprehensive documentation of the Hermes system architecture. Hermes is an automated customer service system that processes incoming emails, analyzes them for intent, and generates appropriate responses for product inquiries and order requests.

## Documentation Index

- [System Overview](overview.md) - High-level architecture and data flow
- [Agents](agents.md) - Detailed description of each agent's responsibilities and components
- [Workflow](workflow.md) - LangGraph workflow orchestration and state management
- [Infrastructure](infrastructure.md) - Core infrastructure components and data models

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              Hermes System                                  │
│                                                                            │
│  ┌─────────┐     ┌─────────────┐     ┌─────────┐     ┌─────────────┐      │
│  │         │     │             │     │         │     │             │      │
│  │ Customer├────►│  Classifier ├────►│   Stock ├────►│   Fulfiller │      │
│  │  Email  │     │   (Analyze) │     │  keeper │     │    (Order)  │      │
│  │         │     │             │     │(Resolve)│     │             │      │
│  └─────────┘     └─────────────┘     └────┬────┘     └───────┬─────┘      │
│                                           │                  │            │
│                                           │                  │            │
│                                           │                  │            │
│                                           ▼                  │            │
│                                    ┌─────────────┐          │            │
│                                    │             │          │            │
│                                    │   Advisor   │          │            │
│                                    │  (Inquiry)  │          │            │
│                                    │             │          │            │
│                                    └───────┬─────┘          │            │
│                                            │                │            │
│                                            │                │            │
│                                            │                │            │
│                                            ▼                ▼            │
│                                    ┌─────────────────────────┐           │
│                                    │                         │           │
│                                    │       Composer          │           │
│                                    │   (Generate Response)   │           │
│                                    │                         │           │
│                                    └────────────┬────────────┘           │
│                                                 │                        │
│                                                 ▼                        │
│                                    ┌─────────────────────────┐           │
│                                    │                         │           │
│                                    │    Customer Response    │           │
│                                    │                         │           │
│                                    └─────────────────────────┘           │
│                                                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

- **Classifier**: Analyzes emails to determine intent and extract product mentions
- **Stockkeeper**: Resolves product mentions to actual products in the catalog
- **Advisor**: Handles product inquiries using RAG to provide factual answers
- **Fulfiller**: Processes order requests, checking stock and applying promotions
- **Composer**: Generates the final natural language response

## Execution Flow

1. Email enters the system through the Classifier
2. Classifier extracts intent and product mentions
3. Stockkeeper resolves mentions to catalog products
4. Based on intent:
   - If inquiry: Advisor processes questions and generates answers
   - If order: Fulfiller processes the order
   - If both: Both agents process their respective parts
5. Composer generates the final response
6. Response is returned to the customer

## Key Technologies

- **LangGraph**: For workflow orchestration
- **ChromaDB**: Vector database for semantic product search
- **Language Models**: Various LLMs for different agent tasks
- **Pydantic**: For structured data representation

## Source Code References

All documentation is based on analysis of the source code in the `src/hermes` directory, particularly:

- `src/hermes/agents/` - Agent implementations
- `src/hermes/model/` - Core data models
- `src/hermes/data_processing/` - Data loading and processing
- `src/hermes/tools/` - Utility tools used by agents 