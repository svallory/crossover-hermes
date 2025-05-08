# Hermes Project: Solution Guide for Interviewers

## Overview

This document provides guidance for interviewers on the Hermes project assignment, highlighting key requirements, implicit clues, and implementation recommendations. Use this to evaluate candidate solutions based on demonstrated AI and LLM tool knowledge.

## Core Requirements Analysis

### Explicit Requirements

1. **Email Classification**
   - Classify emails as "product inquiry" or "order request"
   - Output: email-classification sheet with columns: email ID, category
   - **Test Examples**: 
     - Clear order: E001 "I want to order all the remaining LTH0976 Leather Bifold Wallets"
     - Clear inquiry: E011 "What era are they inspired by exactly? The 1950s, 1960s?"

2. **Order Processing**
   - Verify product availability in stock
   - Create orders with status "created" or "out of stock"
   - Update stock levels after processing orders
   - Generate appropriate responses for orders
   - Output: order-status and order-response sheets
   - **Test Examples**:
     - Multi-item order: E007 "Please send me 5 CLF2109 Cable Knit Beanies and 2 pairs of FZZ1098 Fuzzy Slippers"
     - Simple order: E010 "I would like to order 1 pair of RSG8901 Retro Sunglasses"

3. **Product Inquiry Handling**
   - Respond to inquiries using product catalog information
   - Ensure solution scales to 100,000+ products
   - Output: inquiry-response sheet
   - **Test Examples**:
     - Specific product query: E005 "For the CSH1098, is the material good enough quality to use as a lap blanket?"
     - General inquiry: E016 "I'm looking for a dress for a summer wedding I have coming up"

### Implicit Requirements

1. **Language Handling**
   - Some emails may be in languages other than English
   - LLMs should be able to understand and respond appropriately
   - **Test Example**: 
     - E009: "Hola, tengo una pregunta sobre el DHN0987 Gorro de punto grueso. ¿De qué material está hecho? ¿Es lo suficientemente cálido para usar en invierno? Gracias de antemano."

2. **Tone Adaptation**
   - Match the formality and style of customer communications
   - Maintain professional tone while adapting to customer's language
   - **Test Examples**:
     - Formal: E005 "Good day, For the CSH1098 Cozy Shawl, the description mentions..."
     - Casual: E002 "Good morning, I'm looking to buy the VBT2345 Vibrant Tote bag. My name is Jessica and I love tote bags..."
     - Rambling: E012 "Hey, hope you're doing well. Last year for my birthday, my wife Emily got me..."

3. **Mixed Intent Handling**
   - Some emails contain both inquiries and orders
   - Solution should identify and address both aspects
   - **Test Examples**:
     - E019: "I would like to buy Chelsea Boots [CBT 89 01]... I would like to order Retro sunglasses from you, but probably next time!"
     - E016: "I'm looking for a dress for a summer wedding... And bag, I think I need some travel bag."

## Data-Specific Challenges

### Email Format Variations

1. **Metadata Inconsistencies**
   - Some emails have missing subject lines
   - Others have minimal subjects
   - Solution should handle emails with incomplete metadata
   - **Test Examples**:
     - No subject: E006 (blank), E017 (blank), E021 (blank)
     - Minimal subject: E019 ("Hi")

2. **Product Reference Patterns**
   - **Direct References**: Specific product IDs
     - Example: E010 "I would like to order 1 pair of RSG8901 Retro Sunglasses"
   - **Partial References**: Only product names
     - Example: E014 "Please send me 1 Sleek Wallet"
   - **Formatted Variations**: Products with spaces/brackets
     - Example: E019 "Chelsea Boots [CBT 89 01]"
   - **Vague References**: Generic descriptions
     - Example: E017 "I want to place an order for that popular item you sell. The one that's been selling like hotcakes lately"
     - Example: E008 "I'd want to order one of your Versatile Scarves, the one that can be worn as a scarf, shawl, or headwrap"
   - **Seasonal Inquiries**: Questions about seasonal suitability
     - Example: E020 "Hello I'd like to know how much does Saddle bag cost and if it is suitable for spring season?"

3. **Intent Complexity**
   - Future intentions mixed with current orders
     - Example: E019 "I would like to order Retro sunglasses from you, but probably next time!"
   - Tangential information in emails
     - Example: E012 "I could go for something slightly smaller than my previous one. Oh and we also need to make dinner reservations for our anniversary next month."
   - Personal anecdotes mixed with product inquiries
     - Example: E002 "Last summer I bought this really cute straw tote that I used at the beach. Oh, and a few years ago I got this nylon tote as a free gift with purchase that I still use for groceries."

### Product Catalog Nuances

1. **Special Promotions**
   - Products with ongoing promotions
   - Limited-time sales
   - Solutions should mention these in responses
   - **Test Examples**:
     - CBG9876 (Canvas Beach Bag): "Buy one, get one 50% off!"
     - QTP5432 (Quilted Tote): "Limited-time sale - get 25% off!"
     - TLR5432 (Tailored Suit): "Limited-time sale - get the full suit for the price of the blazer!"
     - BMX5432 (Bomber Jacket): "Buy now and get a free matching beanie!"
     - KMN3210 (Knit Mini Dress): "Limited-time sale - get two for the price of one!"

2. **Inventory Management Considerations**
   - Limited availability products
   - Products mentioned as "Limited stock" or "Almost sold out" in descriptions
   - Solutions should appropriately handle scarcity messaging
   - **Test Examples**:
     - RSG8901 (Retro Sunglasses): stock=1
     - LTG5432 (Leather Gloves): stock=1
     - BMX2345 (Bomber Jacket): stock=1, "Limited quantities available!"
     - PTD8901 (Patchwork Denim Jacket): stock=1, "Hurry, almost sold out!"
     - SKT4567 (Satin Skirt): stock=1, "Hurry, limited stock!"
     - SDE2345 (Saddle Bag): stock=1, "Limited stock available!"

3. **Product Relationships**
   - Related products mentioned in descriptions
   - Solutions should identify these relationships for alternatives/upselling
   - **Test Examples**:
     - PLV8765 (Plaid Flannel Vest): "Buy one, get a matching plaid shirt at 50% off!"
     - BMX5432 (Bomber Jacket): "Buy now and get a free matching beanie!"
     - Products in same category (e.g., "Bags") for alternatives

## Implementation Clues

### Key Signals in the Assignment

1. **LLM Tool Usage**
   - 💡 **Critical Clue**: "You may use additional libraries (e.g., langchain) to streamline the solution"
   - 💡 **Critical Clue**: "Use the most suitable AI techniques for each task. Note that solving tasks with traditional programming methods will not earn points"
   - This clearly indicates candidates should use modern LLM frameworks rather than traditional programming

2. **Vector Search Requirement**
   - 💡 **Critical Clue**: "Ensure your solution scales to handle a full catalog of over 100,000 products without exceeding token limits"
   - 💡 **Critical Clue**: "The system should use Retrieval-Augmented Generation (RAG) and vector store techniques"
   - Implies using proper vector databases, not simple cosine similarity with numpy

3. **Advanced AI Techniques**
   - Explicit mention of RAG and vector stores in evaluation criteria
   - Focus on how candidates leverage LLM capabilities

## Technical Approach Guidance

### Recommended Frameworks and Tools

1. **LLM Orchestration**
   - LangChain or similar framework for structuring LLM interactions
   - LangGraph for complex workflows with multiple steps (classification → processing → response)

2. **Vector Storage**
   - ChromaDB, Pinecone, or similar vector database
   - Not manual vector similarity calculations with numpy/sklearn

3. **Response Generation**
   - Contextual prompting with customer's original message
   - Temperature adjustments for tone adaptation

### Implementation Structure

Candidates should structure their solution with:

1. **Clear Component Separation**
   - Email classifier component
   - Order processing component
   - Inquiry handling component
   - Response generation component

2. **Appropriate Data Flow**
   - Pipeline architecture from classification → processing → response
   - Proper state management between steps

## Advanced Handling Requirements

### Product Reference Resolution

1. **Fuzzy Matching Capability**
   - Match product names with minor variations/misspellings
   - Resolve abbreviated or partially formatted product IDs
   - **Test Examples**:
     - E019: "[CBT 89 01]" should match to "CBT8901" (Chelsea Boots)
     - E008: "Versatile Scarf" should match to "VSC6789" (Versatile Scarf)
     - E014: "Sleek Wallet" should match to "SWL2345" (Sleek Wallet)

2. **Handling Vague References**
   - Identify products from context clues (category, usage, etc.)
   - **Test Examples**:
     - E017: "that popular item you sell" requires inferring the popular item
     - E016: "a dress for a summer wedding" requires finding appropriate dress products
     - E022: "those amazing bags I saw in your latest collection - you know, the ones with the geometric patterns" requires inferring the specific bag products

3. **Language-Agnostic Processing**
   - Handle product references in multiple languages
   - Match to appropriate products regardless of query language
   - **Test Example**:
     - E009: "DHN0987 Gorro de punto grueso" should match to "CHN0987" (Chunky Knit Beanie)

## Evaluation Focus Areas

### What TO Look For

1. **Use of Advanced LLM Tools**
   - ✅ LangChain/LangGraph for orchestration
   - ✅ Vector databases for product retrieval (e.g., ChromaDB, Pinecone, FAISS) and not manual numpy/sklearn similarity
   - ✅ Structured chains or agents for processing steps
   - ✅ Agents that demonstrate effective tool use (e.g., for database lookups, inventory checks, API calls) to perform actions or gather information dynamically, rather than relying solely on chained LLM prompts.

2. **Scalable Design**
   - ✅ Solution that doesn't load entire catalog into context
   - ✅ Proper RAG implementation with embedding-based retrieval
   - ✅ Efficient prompt design

3. **Comprehensive Handling**
   - ✅ Mixed intent detection
   - ✅ Multi-language support
   - ✅ Tone adaptation
   - ✅ Handling of promotions and special pricing
   - ✅ Fuzzy matching for product references

### What NOT To Accept

1. **Traditional Programming Approaches**
   - ❌ Heavy reliance on regex or keyword matching for core logic
   - ❌ Manual similarity calculations instead of vector databases
   - ❌ Direct API calls without appropriate framework usage (e.g., LangChain, LangGraph) for LLM interactions

2. **Prompt Engineering Only**
   - ❌ Relying solely on prompt engineering without proper RAG
   - ❌ Superficial 'agent' implementations that are merely sequential LLM calls without the ability to interact with external data or functions via tools.
   - ❌ Putting entire product catalog in context
   - ❌ Missing RAG implementation or attempting to load entire catalog into context

3. **Incomplete Solutions**
   - ❌ Missing multi-language support
   - ❌ Not adapting the response tone to customer communication style.
   - ❌ Inability to correctly identify and address emails with mixed intents (e.g., containing both an order and an inquiry).
   - ❌ Grossly inadequate product reference resolution, especially for vague mentions or variations.
   - ❌ Failing to incorporate critical product details like promotions or stock issues into responses where relevant.

## Common Pitfalls

1. **Token Limit Ignorance**
   - Not addressing the context window limitations with large catalogs
   - Attempting to include too much information in prompts

2. **Missed Evaluation Criteria**
   - Not implementing tone adaptation
   - Missing RAG implementation
   - Neglecting multi-language support

3. **Framework Avoidance**
   - Building everything from scratch instead of using appropriate frameworks
   - Using traditional programming approaches exclusively

4. **Email Complexity Handling**
   - Failing to extract information from emails with tangential content (E012)
   - Missing implicit intents in customer communications (E022)
   - Not recognizing future intentions vs. immediate orders (E006 vs. E001)

## Example Successful Patterns

1. **Email Classification**
   ```python
   # Using LangChain for structured classification
   from langchain.chains import create_structured_output_chain
   from langchain_core.pydantic_v1 import BaseModel, Field
   
   class EmailClassification(BaseModel):
       category: str = Field(description="Either 'product inquiry', 'order request', or 'mixed'")
       reasoning: str = Field(description="Explanation for the classification")
   
   # Classification chain with structured output
   classification_chain = create_structured_output_chain(...)
   ```

2. **Product Retrieval**
   ```python
   # Using a vector database for product retrieval
   from langchain_community.vectorstores import Chroma
   from langchain_openai import OpenAIEmbeddings
   
   # Create embeddings for products
   embeddings = OpenAIEmbeddings()
   product_db = Chroma.from_documents(product_documents, embeddings)
   
   # Retrieve relevant products for an inquiry
   relevant_products = product_db.similarity_search(query_text, k=3)
   ```

3. **Order Processing with LangGraph**
   ```python
   # Using LangGraph for order workflow
   from langgraph.graph import StateGraph
   
   # Define order processing workflow
   workflow = StateGraph(State)
   workflow.add_node("classify_email", classify_email)
   workflow.add_node("extract_order_details", extract_order_details)
   workflow.add_node("check_inventory", check_inventory)
   workflow.add_node("generate_response", generate_response)
   
   # Add conditional edges
   workflow.add_conditional_edges(...)
   ```

4. **Fuzzy Product Matching**
   ```python
   # Using LangChain for product reference extraction and matching
   from langchain.output_parsers import PydanticOutputParser
   
   class ProductReference(BaseModel):
       product_name: str = Field(description="The product name mentioned")
       product_id: Optional[str] = Field(description="The product ID if mentioned")
       quantity: int = Field(description="The quantity requested, default 1")
       
   # Extract structured product references from text
   parser = PydanticOutputParser(pydantic_object=ProductReference)
   references = extract_references_chain.invoke({"text": email_body})
   
   # Fuzzy match against product catalog using embeddings
   matched_products = []
   for ref in references:
       if ref.product_id:  # Try direct ID match first
           exact_match = find_product_by_id(ref.product_id)
           if exact_match:
               matched_products.append(exact_match)
               continue
       
       # Fall back to semantic search
       similar_products = product_db.similarity_search(
           ref.product_name, 
           filter={"category": infer_category(email_context)}
       )
       matched_products.append(similar_products[0])
   ```

5. **Promotion Handling in Responses**
   ```python
   # Example function to extract promotions from product descriptions
   def extract_promotion(product_description):
       """Extract any promotional details from product description"""
       promotion_keywords = ["sale", "off", "discount", "limited", "free", "buy one"]
       
       # Using LLM to extract structured promotion information
       promotion_chain = create_structured_output_chain(
           llm,
           PromotionInfo,
           prompt_template="Extract any promotional information from this product:\n{description}"
       )
       
       return promotion_chain.invoke({"description": product_description})
   
   # Including promotion in response generation
   def generate_response(customer_email, products, promotions):
       """Generate response including relevant promotional information"""
       context = f"Products to mention: {products}\nSpecial offers: {promotions}"
       response = response_chain.invoke({
           "customer_email": customer_email,
           "context": context
       })
       return response
   ```

This guide should help evaluate whether candidates have successfully demonstrated their knowledge of modern LLM tools and best practices, as specifically required by the assignment. 