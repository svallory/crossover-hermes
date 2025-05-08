# ITD-005: Agent Architecture for Project Hermes

**Date:** 2024-07-28
**Author:** AI Team
**Status:** Proposed

## 1. Overview

This document defines the agent architecture for Project Hermes, consolidating insights from multiple architecture explorations. The system processes customer emails for a fashion retail store, classifying them, extracting relevant signals, processing orders, answering inquiries, and generating appropriate responses.

## 2. Architecture Diagram

```
                   ┌─────────────────────┐
                   │    Email Input      │
                   └─────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │ Classification &    │
                   │ Signal Extraction   │
                   └─────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │   Product Matcher   │
                   └─────────────────────┘
                             │
                             ▼
          ┌─────────────────┴─────────────────┐
          │                                   │
          ▼                                   ▼
┌─────────────────────┐            ┌─────────────────────┐
│   Order Processing  │            │  Inquiry Processing │
│        Agent        │            │        Agent        │
└─────────────────────┘            └─────────────────────┘
          │                                   │
          │                                   │
          └─────────────────┬─────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │  Response Composer  │
                  │        Agent        │
                  └─────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │  Final Response     │
                  └─────────────────────┘
```

## 3. Agent Definitions and Responsibilities

### 3.1 Classification & Signal Extraction Agent

**Purpose**: Analyze incoming emails to determine primary intent and extract all relevant customer signals.

**Inputs**:
- Email content (subject + body)
- Signal taxonomy from sales-email-intelligence-guide.md

**Processing**:
- Classify email as "order", "inquiry", or "hybrid" (with order taking precedence)
- Extract all signals present in the email (product references, emotional cues, personal context, etc.)
- Map each signal to the specific phrases in the email that triggered it

**Outputs**:
```json
{
  "type": "order" | "inquiry" | "hybrid",
  "primary_type": "order" | "inquiry",  // For hybrid emails
  "confidence": 0.95,  // Classification confidence score
  "signals": {
    "product_reference": ["Chelsea boots", "CBT8901"],
    "purchase_intent": ["want to order", "looking to buy"],
    "emotion": ["excited about", "can't wait"],
    "customer_context": ["for my new job", "anniversary gift"],
    "empathy_trigger": ["my previous one broke after 2 years"],
    "personal_information": ["my name is David"]
    // Additional signals as defined in sales-email-intelligence-guide.md
  }
}
```

**Implementation Notes**:
- Uses GPT-4o with a prompt that includes the signal taxonomy
- Focuses on high recall for signals (catch as many as possible)
- For hybrid emails, ensure all signals are captured regardless of whether they relate to orders or inquiries

### 3.2 Product Matcher Agent

**Purpose**: Identify specific products mentioned in the email through direct references or descriptive characteristics.

**Inputs**:
- Classification & signal extraction results
- Product catalog
- Vector embeddings of product descriptions (for similarity search)

**Processing**:
- Match explicit product codes (e.g., "CBT8901") directly to catalog
- Use fuzzy matching for product names (e.g., "Chelsea boots" → "Chelsea Boots")
- Use vector similarity search for descriptive references (e.g., "black boots for work")
- Separate identifiable product references into order items and inquiry items
- For each product, determine if it's part of an order request or an inquiry

**Outputs**:
```json
{
  "order_items": [
    {
      "product_id": "CBT8901",
      "product_name": "Chelsea Boots",
      "quantity": 1,
      "confidence": 0.98,
      "original_mention": "Chelsea boots",
      "match_method": "fuzzy_name_match"
    }
  ],
  "inquiry_items": [
    {
      "product_id": "LTH1098",
      "product_name": "Leather Backpack",
      "confidence": 0.85,
      "original_mention": "leather bag for laptop",
      "match_method": "vector_similarity",
      "questions": ["Does it have organizational pockets?"]
    }
  ],
  "unmatched_mentions": [
    {
      "mention": "red scarf with tassels",
      "likely_intent": "inquiry"
    }
  ]
}
```

**Implementation Notes**:
- Vector embeddings for products should be pre-computed
- Uses a tiered matching approach: exact ID → fuzzy name → vector similarity
- Sets confidence thresholds for matches to avoid incorrect product assignments
- Carefully extracts quantity information for order items

### 3.3 Order Processing Agent

**Purpose**: Process order requests by checking inventory and determining fulfillment status.

**Inputs**:
- Product matcher results (specifically order_items)
- Current inventory status

**Processing**:
- Check each order item against current inventory
- Determine if the order can be fulfilled based on requested quantity
- Update inventory for fulfilled items
- Identify alternatives for out-of-stock items (based on category, price range, etc.)

**Outputs**:
```json
{
  "processed_items": [
    {
      "product_id": "CBT8901",
      "product_name": "Chelsea Boots",
      "quantity": 1,
      "status": "created" | "out_of_stock" | "partial_fulfillment",
      "available_quantity": 2,  // If partial_fulfillment
      "alternatives": [  // If out_of_stock or partial_fulfillment
        {
          "product_id": "RBT0123",
          "product_name": "Rugged Boots",
          "similarity": 0.85
        }
      ]
    }
  ],
  "unfulfilled_items_for_inquiry": [
    {
      "product_id": "CBT8901",
      "product_name": "Chelsea Boots",
      "original_request": "Chelsea boots",
      "inquiry_type": "alternatives_needed"
    }
  ]
}
```

**Implementation Notes**:
- Maintains stateful inventory tracking
- Converts unfulfilled orders to inquiries about alternatives
- Uses product categories and attributes to find suitable alternatives

### 3.4 Inquiry Processing Agent

**Purpose**: Answer customer questions about products and provide relevant information.

**Inputs**:
- Product matcher results (specifically inquiry_items)
- Unfulfilled order items requiring alternatives
- Product catalog with detailed descriptions
- Signals from Classification & Signal Extraction

**Processing**:
- Answer specific questions about products using RAG (retrieval augmented generation)
- Find suitable alternatives for out-of-stock items
- Provide recommendations based on customer signals
- Identify upsell/cross-sell opportunities based on signals

**Outputs**:
```json
{
  "inquiry_responses": [
    {
      "product_id": "LTH1098",
      "product_name": "Leather Backpack",
      "original_question": "Does it have organizational pockets?",
      "answer": "Yes, our Leather Backpack features multiple compartments, including a padded laptop sleeve, perfect for keeping your items organized.",
      "source": "product_description"
    }
  ],
  "alternative_suggestions": [
    {
      "for_product_id": "CBT8901",
      "for_product_name": "Chelsea Boots",
      "alternatives": [
        {
          "product_id": "RBT0123",
          "product_name": "Rugged Boots",
          "reason": "Similar style and use case, currently in stock"
        }
      ]
    }
  ],
  "upsell_opportunities": [
    {
      "based_on_signal": "customer_context: for my new job",
      "suggestion": {
        "product_id": "LTH2109",
        "product_name": "Leather Messenger Bag",
        "reason": "Complements professional attire for new job context"
      }
    }
  ]
}
```

**Implementation Notes**:
- Uses RAG to ensure accurate product information
- Leverages customer signals to personalize recommendations
- Ensures all suggestions are in-stock items
- Follows upselling guidelines from sales-email-intelligence-guide.md

### 3.5 Response Composer Agent

**Purpose**: Generate a cohesive, personalized email response that addresses all customer needs.

**Inputs**:
- Original email content
- Classification & signal extraction results
- Order processing results
- Inquiry processing results
- Sales-email-intelligence-guide.md guidelines

**Processing**:
- Combine order confirmation and inquiry responses into a cohesive whole
- Apply appropriate tone and style based on customer signals
- Structure response to prioritize most important information
- Include empathetic elements for relevant emotional signals
- Format product information clearly
- Add appropriate upsells/cross-sells where relevant

**Outputs**:
- Complete, formatted email response that addresses all aspects of the customer's email

**Implementation Notes**:
- Follows the Natural Communication Guidelines from sales-email-intelligence-guide.md
- Uses different response templates based on email type (order, inquiry, hybrid)
- Handles transitions between topics smoothly in hybrid emails
- Adapts tone to match customer's communication style

## 4. Data Flow and Integration

### 4.1 End-to-End Processing Sequence

1. **Email Input**:
   - Parse email subject and body
   - Prepare for classification & signal extraction

2. **Classification & Signal Flow**:
   - Extract signals from raw email
   - Classification determines primary processing path
   - Signals influence all subsequent processing

3. **Product Reference Resolution**:
   - Map customer's language to specific catalog items
   - Disambiguate vague references where possible

4. **Parallel Processing**:
   - Orders and inquiries processed simultaneously
   - Unfulfilled orders can generate new inquiries

5. **Unified Response Generation**:
   - Collate all processing results
   - Generate cohesive response addressing all aspects

### 4.2 Cross-Agent Communication

This architecture uses a context-enrichment pattern where each agent adds to a growing context object:

```
Email → Classification/Signals → Product Matching → Order/Inquiry Processing → Response Composition
       └─── Enriched Context Object ───────────────────────────────────────────────────────────────┘
```

Each agent receives the original inputs plus the outputs of previous agents, allowing for progressively more informed decisions.

## 5. Implementation Considerations

### 5.1 LLM Usage Efficiency

- **Prompt Engineering**: Each agent requires carefully crafted prompts with clear instructions
- **Token Optimization**: Structure prompts to minimize token usage while maintaining clarity
- **Context Management**: As context grows through the pipeline, strategic trimming may be needed

### 5.2 Error Handling and Edge Cases

- **Low Confidence Classifications**: If classification confidence is below threshold, default to treating as inquiry
- **Ambiguous Product References**: If product matcher has low confidence, include clarification in response
- **No Matches Found**: If no products match customer references, generate appropriate clarification response
- **Non-Fashion Inquiries**: Politely redirect to fashion-related topics
- **Multiple Languages**: Detect language and process accordingly (if supported)

### 5.3 Agent Coordination

- **Data Schema Consistency**: Ensure agents share consistent data schemas for seamless handoffs
- **Stateful Processing**: Maintain order state and inventory updates throughout the pipeline
- **Signal Propagation**: Ensure signals extracted early influence later processing steps

### 5.4 Evaluation Metrics

For each agent and the system as a whole, establish metrics for:
- **Accuracy**: Correct classification, matching, order processing, etc.
- **Completeness**: All customer needs addressed
- **Naturalness**: Response reads like it was written by a human
- **Relevance**: Recommendations and upsells match customer context

## 6. Alternative Approaches Considered

### 6.1 Two-Agent Architecture

**Description**: Simpler architecture with just Classification and Response Generation.

**Advantages**:
- Simpler implementation
- Fewer LLM calls (lower cost)
- Less complex handoffs

**Disadvantages**:
- Less specialized optimization for different tasks
- More complex prompts for each agent
- Higher risk of missing signals or nuanced handling

### 6.2 Four-Agent Architecture without Product Matcher

**Description**: Similar to proposed architecture but without dedicated Product Matcher.

**Advantages**:
- Fewer LLM calls
- Reduced complexity

**Disadvantages**:
- Less accurate product matching
- More complex Order Processing agent
- Potentially poorer handling of ambiguous product references

### 6.3 Single Pipeline with Role-Switching

**Description**: One LLM instance that adapts its role based on the current processing stage.

**Advantages**:
- Consistent model behavior
- Potentially lower cost by reusing the same context
- Simpler implementation

**Disadvantages**:
- Less specialized handling
- Risk of context limit constraints
- Less flexibility for task-specific optimization

## 7. Decision Rationale

The five-agent architecture balances:

1. **Specialization**: Each agent focuses on specific tasks they can excel at
2. **Flexibility**: Clear separation of concerns allows for targeted improvements
3. **Robustness**: Modular design helps isolate and address errors
4. **Context Utilization**: Each stage builds on previous context effectively
5. **Natural Language Handling**: Specialized prompts for each stage optimize for their specific tasks
6. **Efficient Processing**: Parallel handling of orders and inquiries

By separating Product Matching from other concerns, we enable more sophisticated matching techniques (vector search, fuzzy matching) while keeping other agents focused on their core responsibilities.

## 8. Implementation Sequence

1. Develop and test Classification & Signal Extraction Agent
2. Implement Product Matcher with vector embedding capabilities
3. Develop Order Processing Agent with inventory management
4. Create Inquiry Processing Agent with RAG capabilities
5. Build Response Composer with guidance from sales-email-intelligence-guide.md
6. Integrate agents into end-to-end pipeline
7. Test with sample emails from diverse scenarios
8. Optimize prompts and thresholds based on performance

## 9. Potential Challenges and Mitigations

| Challenge | Mitigation |
|-----------|------------|
| Signal extraction missing key signals | Optimize prompt with comprehensive examples; implement monitoring for missed signals |
| Vector search not finding relevant products | Pre-process product descriptions to enhance embedding quality; add fallback matching strategies |
| Token limit constraints as context grows | Implement strategic summarization of context between agents; trim less relevant information |
| Response composer creating unnatural language | Apply "Natural Communication Guidelines"; include example human responses in prompt |
| Hybrid emails not handling both aspects well | Create specific hybrid email testing dataset; optimize transitions between topics |
| Hallucinated product information | Strictly ground inquiry responses in product catalog data; implement fact-checking |

## 10. Conclusion

This five-agent architecture provides a robust framework for processing fashion retail emails, balancing specialization with efficient processing. The clear separation of concerns enables focused optimization while the enriched context flow ensures each agent has the information needed for informed decisions.

The architecture addresses the complexities of hybrid emails, empathy requirements, and product matching challenges while providing a clear implementation path. It efficiently leverages LLM capabilities while maintaining appropriate guardrails for accurate, helpful customer service. 