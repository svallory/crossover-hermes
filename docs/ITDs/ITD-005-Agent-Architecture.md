# ITD-005: Agent Architecture for Project Hermes

**Date:** 2024-07-28
**Updated:** 2024-12-XX (Implementation Review)
**Author:** AI Team
**Status:** Implemented

## 1. Overview

This document defines the agent architecture for Project Hermes, as implemented using LangGraph StateGraph workflow orchestration. The system processes customer emails for a fashion retail store using a five-agent workflow: classifying emails, resolving product mentions, processing orders, answering inquiries, and generating appropriate responses.

The architecture leverages LangGraph's professional workflow management capabilities to coordinate specialized agents with conditional routing, parallel execution, and comprehensive state management.

## 2. Architecture Diagram

```
                   ┌─────────────────────┐
                   │    Email Input      │
                   │  (ClassifierInput)  │
                   └─────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │    CLASSIFIER       │
                   │   (analyze_email)   │
                   └─────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │   STOCKKEEPER       │
                   │ (resolve_products)  │
                   └─────────────────────┘
                             │
                             ▼
          ┌─────────────────┴─────────────────┐
          │         Conditional Routing       │
          │    (route_resolver_result)        │
          └─────────────────┬─────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   FULFILLER     │   │ FULFILLER +     │   │    ADVISOR      │
│ (process_order) │   │    ADVISOR      │   │(respond_inquiry)│
│                 │   │  (parallel)     │   │                 │
└─────────────────┘   └─────────────────┘   └─────────────────┘
        │                   │                   │
        │                   │                   │
        └─────────────────┬─────────────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │     COMPOSER        │
                │ (compose_response)  │
                └─────────────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │  Final Response     │
                │   (OverallState)    │
                └─────────────────────┘
```

## 3. Agent Definitions and Responsibilities

### 3.1 Classifier Agent (analyze_email)

**Purpose**: Analyze incoming emails to determine primary intent and extract all relevant customer signals.

**Implementation**: `hermes/agents/classifier/agent.py:analyze_email()`

**Inputs**:
- `ClassifierInput`: email_id, subject, message
- LangGraph configuration with HermesConfig

**Processing**:
- Classify email as "order", "product inquiry", or hybrid (with detailed intent analysis)
- Extract comprehensive signals (product references, emotional cues, personal context, etc.)
- Map each signal to specific phrases that triggered it
- Handle complex multi-intent scenarios

**Outputs**:
```python
ClassifierOutput:
  email_analysis: EmailAnalysis
    primary_intent: "order" | "product inquiry"
    secondary_intents: List[str]
    product_mentions: List[ProductMention]
    signals: Dict[str, List[str]]
    confidence: float
```

**LangGraph Integration**:
- Node: `Nodes.CLASSIFIER`
- Entry point: Connected from `START`
- Output: Updates `OverallState.classifier`

### 3.2 Stockkeeper Agent (resolve_product_mentions)

**Purpose**: Identify and resolve specific products mentioned in emails through multi-tiered matching strategy.

**Implementation**: `hermes/agents/stockkeeper/agent.py:resolve_product_mentions()`

**Inputs**:
- `StockkeeperInput`: Contains classifier output with product mentions
- Access to product catalog and vector store

**Processing**:
- **Tier 1**: Exact product ID matching (`get_product_by_id`)
- **Tier 2**: Fuzzy name matching using `thefuzz` library (`find_products_by_name_wrapper`)
- **Tier 3**: Semantic vector search via ChromaDB (`search_products_semantically`)
- **LLM Disambiguation**: For ambiguous cases with multiple candidates
- Confidence scoring with thresholds (EXACT_MATCH_THRESHOLD=0.95, SIMILAR_MATCH_THRESHOLD=0.75)
- Deduplication of similar product mentions

**Outputs**:
```python
StockkeeperOutput:
  resolved_products: List[ResolvedProduct]
    product: Product
    confidence: float
    original_mention: ProductMention
    resolution_method: str
  unresolved_mentions: List[ProductMention]
  processing_errors: List[str]
```

**LangGraph Integration**:
- Node: `Nodes.STOCKKEEPER`
- Input: Requires classifier output
- Output: Updates `OverallState.stockkeeper`
- Routing: Triggers conditional routing logic

### 3.3 Fulfiller Agent (process_order)

**Purpose**: Process order requests by checking inventory and determining fulfillment status.

**Implementation**: `hermes/agents/fulfiller/agent.py:process_order()`

**Inputs**:
- Email analysis from classifier
- Resolved products from stockkeeper
- Promotion specifications from configuration
- Current inventory data

**Processing**:
- Check resolved products against current inventory
- Determine fulfillment status for each requested item
- Apply promotion logic and pricing
- Update inventory for fulfilled items
- Generate alternatives for out-of-stock items
- Create order records for successful fulfillments

**Outputs**:
```python
FulfillerOutput:
  order_result: OrderResult
    order_items: List[OrderItem]
    unfulfilled_items: List[UnfulfilledItem]
    total_cost: float
    applied_promotions: List[Promotion]
    order_status: str
```

**LangGraph Integration**:
- Node: `Nodes.FULFILLER`
- Conditional Execution: Based on routing logic
- Parallel Execution: Can run concurrently with ADVISOR
- Output: Updates `OverallState.fulfiller`

### 3.4 Advisor Agent (respond_to_inquiry)

**Purpose**: Answer customer questions about products using RAG and provide recommendations.

**Implementation**: `hermes/agents/advisor/agent.py:respond_to_inquiry()`

**Inputs**:
- Overall workflow state including classifier and stockkeeper outputs
- Access to ChromaDB vector store for RAG
- Product catalog for detailed information

**Processing**:
- Generate inquiry responses using RAG with ChromaDB
- Answer specific product questions with retrieved context
- Provide alternatives for unavailable products
- Generate personalized recommendations based on customer signals
- Handle unresolved product mentions with suggestions

**Outputs**:
```python
AdvisorOutput:
  inquiry_responses: List[InquiryResponse]
  recommendations: List[ProductRecommendation]
  alternatives: List[AlternativesSuggestion]
  unresolved_responses: List[UnresolvedResponse]
```

**LangGraph Integration**:
- Node: `Nodes.ADVISOR`
- Conditional Execution: Based on routing logic
- Parallel Execution: Can run concurrently with FULFILLER
- Output: Updates `OverallState.advisor`

### 3.5 Composer Agent (compose_response)

**Purpose**: Generate cohesive, personalized email responses that address all customer needs.

**Implementation**: `hermes/agents/composer/agent.py:compose_response()`

**Inputs**:
- Complete workflow state including all agent outputs
- Original email content and customer signals
- Configuration for response formatting

**Processing**:
- Combine order confirmations and inquiry responses
- Apply appropriate tone based on customer signals and context
- Structure response to prioritize most important information
- Include empathetic elements for relevant emotional signals
- Format product information clearly and professionally
- Handle transitions between topics smoothly for hybrid emails

**Outputs**:
```python
ComposerOutput:
  final_response: str
  response_sections: List[ResponseSection]
  tone_analysis: ToneAnalysis
  included_elements: List[str]
```

**LangGraph Integration**:
- Node: `Nodes.COMPOSER`
- Input: Requires outputs from FULFILLER and/or ADVISOR
- Final Node: Connects to `END`
- Output: Updates `OverallState.composer`

## 4. LangGraph Workflow Implementation

### 4.1 StateGraph Configuration

```python
# Graph definition with typed state and configuration
graph_builder = StateGraph(OverallState, input=ClassifierInput, config_schema=HermesConfig)

# Agent nodes
graph_builder.add_node(Nodes.CLASSIFIER, analyze_email_node)
graph_builder.add_node(Nodes.STOCKKEEPER, resolve_products_node)
graph_builder.add_node(Nodes.FULFILLER, process_order_node)
graph_builder.add_node(Nodes.ADVISOR, respond_to_inquiry)
graph_builder.add_node(Nodes.COMPOSER, compose_response)

# Sequential flow
graph_builder.add_edge(START, Nodes.CLASSIFIER)
graph_builder.add_edge(Nodes.CLASSIFIER, Nodes.STOCKKEEPER)

# Conditional routing based on email intent
graph_builder.add_conditional_edges(
    Nodes.STOCKKEEPER,
    route_resolver_result,
    [Nodes.FULFILLER, Nodes.ADVISOR],
)

# Convergence to final composition
graph_builder.add_edge(Nodes.FULFILLER, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.ADVISOR, Nodes.COMPOSER)
graph_builder.add_edge(Nodes.COMPOSER, END)
```

### 4.2 Conditional Routing Logic

```python
def route_resolver_result(state: OverallState) -> list[Hashable] | Hashable:
    """Route after product resolution based on email intents."""
    classifier = state.classifier
    if classifier is not None:
        analysis = classifier.email_analysis

        return (
            Nodes.ADVISOR
            if analysis.primary_intent == "product inquiry"
            else [Nodes.FULFILLER, Nodes.ADVISOR]
            if analysis.has_inquiry()
            else Nodes.FULFILLER
        )
    return END
```

### 4.3 State Management

```python
class OverallState(BaseModel):
    """Comprehensive workflow state with type safety."""
    email_id: str
    subject: str | None = None
    message: str

    # Agent outputs
    classifier: ClassifierOutput | None = None
    stockkeeper: StockkeeperOutput | None = None
    fulfiller: FulfillerOutput | None = None
    advisor: AdvisorOutput | None = None
    composer: ComposerOutput | None = None

    # Error tracking
    errors: Annotated[dict[Agents, Error], merge_errors] = Field(default_factory=dict)
```

## 5. Data Flow and Integration

### 5.1 End-to-End Processing Sequence

1. **Email Input**: `ClassifierInput` with email_id, subject, message
2. **Classification**: Extract intents, signals, and product mentions
3. **Product Resolution**: Multi-tiered matching with confidence scoring
4. **Conditional Routing**:
   - Pure orders → FULFILLER only
   - Pure inquiries → ADVISOR only
   - Hybrid emails → FULFILLER + ADVISOR (parallel)
5. **Specialized Processing**: Order fulfillment and/or inquiry responses
6. **Response Composition**: Unified, coherent email response

### 5.2 Parallel Execution Benefits

- **Performance**: Concurrent processing of orders and inquiries
- **User Experience**: Faster response times for complex emails
- **Resource Utilization**: Efficient use of LLM and database resources
- **Scalability**: Natural scaling for high-volume email processing

### 5.3 Error Isolation and Recovery

- **Per-Agent Error Handling**: Failures isolated to individual agents
- **State Preservation**: Successful agent outputs preserved despite partial failures
- **Graceful Degradation**: System continues operation with reduced functionality
- **Comprehensive Logging**: Detailed error tracking in workflow state

## 6. Implementation Advantages

### 6.1 Professional Workflow Management

- **Type Safety**: Pydantic models ensure data contract consistency
- **Observability**: LangSmith integration for workflow monitoring
- **Debugging**: Clear execution traces and state inspection
- **Configuration**: Centralized configuration management via HermesConfig

### 6.2 Agent Specialization Benefits

- **Clear Separation**: Each agent focuses on its core competency
- **Independent Development**: Agents can be developed and tested separately
- **Specialized Optimization**: Task-specific prompt engineering and logic
- **Maintainable Architecture**: Changes isolated to relevant agents

### 6.3 Scalability and Extensibility

- **Additional Agents**: Easy addition of new specialized agents
- **Complex Routing**: Support for sophisticated conditional logic
- **State Accumulation**: Rich context available to downstream agents
- **Production Ready**: Architecture suitable for enterprise deployment

## 7. Key Implementation Details

### 7.1 Tool Integration

- **Direct Function Calls**: Agents use regular Python functions rather than `@tool` decorators for better control
- **Catalog Tools**: Dedicated tools for product lookup, fuzzy matching, and semantic search
- **Vector Store**: ChromaDB integration via `get_vector_store()` with global caching

### 7.2 Multi-Tiered Product Resolution

- **Exact Match**: Direct product ID lookup with 95% confidence threshold
- **Fuzzy Matching**: Name-based matching using `thefuzz` library
- **Semantic Search**: Vector similarity via ChromaDB embeddings
- **LLM Disambiguation**: AI-powered resolution of ambiguous cases

### 7.3 Configuration Management

- **HermesConfig**: Centralized configuration schema
- **Environment Variables**: Secure API key management
- **Promotion Specs**: Configurable business rules
- **Model Selection**: Weak/strong model strategy for cost optimization

## 8. Alternative Approaches Considered

### 8.1 Custom Sequential Implementation

**Advantages**: Full control, minimal dependencies, simpler debugging
**Disadvantages**: Complex state management, manual error handling, no parallel execution, limited scalability

**Decision**: Rejected due to complexity of multi-agent coordination

### 8.2 Three-Agent Architecture

**Advantages**: Simpler with fewer handoffs, reduced complexity
**Disadvantages**: Less specialized optimization, complex prompts, reduced modularity

**Decision**: Rejected in favor of specialized agent responsibilities

### 8.3 Generic Workflow Engines

**Advantages**: Mature workflow features, enterprise capabilities
**Disadvantages**: Overkill for agent coordination, complex setup, not LLM-optimized

**Decision**: Rejected in favor of agent-specific LangGraph patterns

## 9. Decision Rationale

The five-agent LangGraph architecture provides optimal balance of:

1. **Specialization**: Each agent optimized for specific tasks
2. **Professional Architecture**: Production-ready workflow management
3. **Performance**: Parallel execution and efficient resource utilization
4. **Maintainability**: Clear separation of concerns and type-safe interfaces
5. **Scalability**: Support for complex routing and additional agents
6. **Observability**: Comprehensive monitoring and debugging capabilities

## 10. Production Considerations

### 10.1 Performance Optimization

- **Model Selection**: Weak models for classification, strong models for generation
- **Caching**: Vector store caching and result memoization
- **Parallel Execution**: Concurrent agent processing where possible
- **Resource Management**: Efficient database connection pooling

### 10.2 Error Handling Strategy

- **Circuit Breakers**: Prevent cascade failures across agents
- **Retry Logic**: Configurable retry strategies for transient failures
- **Fallback Responses**: Graceful degradation for partial system failures
- **Monitoring**: Comprehensive error tracking and alerting

### 10.3 Security and Compliance

- **Input Validation**: Pydantic model validation for all inputs
- **API Key Management**: Secure credential handling
- **Data Privacy**: Customer data protection throughout workflow
- **Audit Logging**: Comprehensive activity logging for compliance

## 11. Conclusion

The LangGraph-based five-agent architecture successfully addresses the complexity of processing fashion retail emails while maintaining professional software engineering standards. The implementation demonstrates:

- **Robust Multi-Agent Coordination**: Sophisticated workflow management with conditional routing and parallel execution
- **Production-Ready Architecture**: Type-safe state management, comprehensive error handling, and professional observability
- **Specialized Agent Design**: Each agent optimized for its specific domain with clear responsibilities
- **Future-Proof Scalability**: Architecture supports additional agents, complex routing, and enterprise deployment requirements

The architecture efficiently balances specialization with coordination, providing a maintainable foundation for sophisticated customer email processing in production environments.