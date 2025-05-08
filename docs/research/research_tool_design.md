# Research: Tool Design for Hermes

## Question
What tools should each agent have access to? How should we implement the database tools for order processing? Should we use structured output from LLMs or rely on tools for data extraction?

## Research Notes

### Tools in the Data-Enrichment Example

The data-enrichment example uses a set of tools for information retrieval and processing:

```python
def search_tool(query: str, _: State, config: RunnableConfig) -> dict:
    # ... tool implementation ...
    return {"results": search_results, "query": query}

def scrape_tool(url: str, _: State, config: RunnableConfig) -> dict:
    # ... tool implementation ...
    return {"content": content}

@tool
def search_web(query: str) -> List[dict]:
    """Search the web for relevant content."""
    # ... implementation ...
    return results

@tool
def get_websites_from_search(query: str) -> List[dict]:
    """Search the web and return just websites (no snippets)."""
    # ... implementation ...
    return results

@tool
def scrape_website(url: str) -> str:
    """Scrape content from a website."""
    # ... implementation ...
    return content
```

Key features:
- Implementation of core functionality as plain Python functions
- Use of the `@tool` decorator to expose functionality to the LLM
- Additional parameters for state and config where needed
- Return values as structured dictionaries

The tools follow these patterns:
- They accept specific inputs (query string, URL)
- They have access to the State and RunnableConfig
- They return structured data (dictionaries)
- They include clear docstrings describing their purpose
- They're designed for specific functions (search, scrape)

### Tools Required for Hermes

Based on the assignment requirements and implementation draft, our Hermes system will need the following tools:

1. **Email Classification Tools**:
   - `classify_email`: Determines if an email is a product inquiry or order request

2. **Order Processing Tools**:
   - `extract_order_details`: Identifies products and quantities from email text
   - `check_stock`: Verifies product availability
   - `update_stock`: Updates inventory after order processing
   - `create_order`: Creates new orders with appropriate status

3. **Product Inquiry Tools**:
   - `search_products`: Searches the product catalog using vector embeddings
   - `get_product_details`: Retrieves complete information about a product
   - `get_related_products`: Finds similar or related products for recommendations

4. **Response Generation Tools**:
   - `generate_order_response`: Creates responses for order requests
   - `generate_inquiry_response`: Creates responses for product inquiries
   - `detect_language`: Identifies the language of the original email
   - `adapt_tone`: Adjusts response tone to match customer's style

### Database Implementation Approaches

1. **Vector Database Approach** (from the solution guide):
   - Use ChromaDB, Pinecone, or similar for product catalog
   - Create vector embeddings of product descriptions
   - Enable semantic search for product inquiries
   - Scale to 100,000+ products

2. **Direct Database Access** (from the implementation draft):
   - Use pandas DataFrames as the "database"
   - Create functions to query and update the DataFrame
   - Less scalable but simpler implementation for the POC

## Web Research on Tool Design Best Practices

Based on my web search for best practices in tool design for e-commerce and inventory management with LLMs:

1. **Specialized vs. General Tools**:
   - Most successful AI agent architectures use specialized tools for specific tasks rather than generic tools
   - Tools should have clear, narrow purposes to make them more predictable and reliable
   - Each tool should do one thing well rather than having multi-purpose tools

2. **Tool Design Patterns**:
   - Tools should accept and return structured data (JSON objects, dictionaries)
   - Tools should include detailed docstrings that explain their purpose and expected inputs/outputs
   - Tools should handle errors gracefully and return useful error messages
   - Tools should be designed for composition (output of one can be input to another)

3. **Best Practices for E-commerce Tools**:
   - Inventory management tools should verify stock before operations
   - Product search tools should support fuzzy matching for product IDs and names
   - Order processing tools should maintain transaction history
   - Response generators should adapt to customer tone and language

## Decision: Tool Design for Hermes

### Tool Structure

**Decision**: We will implement specialized tools for each agent in our system, following the patterns established in data-enrichment with these key aspects:
1. Use RunnableConfig and State access for all tools to ensure proper configuration and state management
2. Create specialized tools for each function rather than general-purpose tools
3. Return structured data from all tools for consistency
4. Use detailed docstrings to guide LLM tool use
5. Implement proper error handling in all tools

The supervisor agent will have access to high-level orchestration tools, while specialized agents will have access to domain-specific tools:

**Supervisor Agent Tools**:
- `route_to_classifier`: Routes initial email to classifier agent
- `route_to_processor`: Routes classified order requests to processor agent
- `route_to_generator`: Routes processed information to response generator agent

**Email Classifier Agent Tools**:
- `detect_language`: Identifies email language for proper processing
- `extract_email_metadata`: Extracts key information from email (sender, tone, etc.)
- `classify_email_intent`: Determines primary and secondary intents

**Order Processor Agent Tools**:
- `extract_product_references`: Identifies products mentioned in the email
- `resolve_product_id`: Matches product references to actual product IDs
- `check_inventory`: Checks if requested products are in stock
- `update_inventory`: Updates stock levels after order processing
- `create_order`: Creates an order with appropriate status
- `find_alternative_products`: Finds alternatives for out-of-stock items

**Response Generator Agent Tools**:
- `get_product_details`: Retrieves detailed information about products
- `generate_inquiry_response`: Creates responses for product inquiries
- `generate_order_response`: Creates responses for order requests
- `adapt_response_tone`: Adjusts response tone to match customer's style
- `translate_response`: Translates response to customer's original language if needed

### Database Implementation

**Decision**: We will implement a hybrid approach combining a vector database for product search with DataFrame manipulation for inventory management:

1. Use ChromaDB as the vector database for storing product embeddings and enabling semantic search
2. Create helper functions that abstract database operations, allowing easy switching between implementations
3. Implement transaction management to ensure stock updates are atomic and consistent
4. Include proper index creation and query optimization for performance

This approach balances the requirements for RAG implementation with the need for straightforward inventory management in the proof-of-concept.

### Structured Output vs. Tool-based Extraction

**Decision**: We will use a combination of structured output from LLMs and specialized tools:

1. Use structured output (JSON mode) when extracting initial information from emails (classification, product references)
2. Use tools for operations requiring external data access (inventory checks, product searches)
3. Create a validation layer to ensure extracted information matches expected schemas

This hybrid approach leverages the strengths of each method: structured output for initial extraction and tools for operations requiring integration with external systems or databases.

The decision is justified by:
1. The need to handle complex email structures with varying formats and language styles
2. The requirement to scale to a large product catalog (100,000+ products)
3. The importance of maintaining consistent inventory management
4. The necessity of adapting tone and language in responses

This tool design approach aligns with modern AI agent architecture best practices while addressing the specific requirements of our e-commerce email processing system. 