# Hermes: Optimized 4-Agent Architecture

## Overview

This document outlines a streamlined 4-agent architecture for processing customer emails in the Hermes system. This design balances separation of concerns with efficient processing, ensuring comprehensive handling of complex email scenarios while maintaining a clear workflow.

## Core Agent Architecture

### 1. Email Analyzer Agent

**Purpose**: Analyze incoming emails to detect classification, language, tone, product references, and customer signals

**Input**:
- Email subject and body
- Product catalog metadata (for context)

**Output**:
- Primary classification: "product_inquiry" or "order_request" (binary as required by assignment)
- Language detection and tone analysis
- Extracted product references with confidence levels
- Customer signals based on the sales intelligence framework
- Structured analysis result

**Implementation**:
```python
from langchain.chains import create_structured_output_chain
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Optional

class ProductReference(BaseModel):
    reference_text: str = Field(description="Original text from email referencing the product")
    reference_type: str = Field(description="Type: 'product_id', 'product_name', 'description', 'category'")
    product_id: Optional[str] = Field(description="Extracted or inferred product ID if available")
    product_name: Optional[str] = Field(description="Extracted or inferred product name if available")
    quantity: int = Field(description="Requested quantity, default 1")
    confidence: float = Field(description="Confidence in the extraction/match (0-1)")
    excerpt: str = Field(description="The exact text from the email containing this reference")

class CustomerSignal(BaseModel):
    signal_type: str = Field(description="Type of customer signal detected")
    signal_category: str = Field(description="Category from sales intelligence framework")
    signal_text: str = Field(description="The text that indicates this signal")
    signal_strength: float = Field(description="Strength of the signal (0-1)")
    excerpt: str = Field(description="The exact text from the email that triggered this signal")
    
class ToneAnalysis(BaseModel):
    tone: str = Field(description="Detected tone: 'formal', 'casual', 'urgent', etc.")
    formality_level: int = Field(description="Formality level from 1 (very casual) to 5 (very formal)")
    key_phrases: List[str] = Field(description="Key phrases that informed the tone analysis")
    
class EmailAnalysis(BaseModel):
    """Pydantic model for structured email analysis result"""
    classification: str = Field(description="Either 'product_inquiry' or 'order_request'")
    classification_confidence: float = Field(description="Confidence in the classification (0-1)")
    classification_evidence: str = Field(description="Key text that determined the classification")
    language: str = Field(description="Detected language of the email")
    tone_analysis: ToneAnalysis = Field(description="Analysis of customer's tone and writing style")
    product_references: List[ProductReference] = Field(description="List of detected product references")
    customer_signals: List[CustomerSignal] = Field(description="Customer signals from sales intelligence guide")
    reasoning: str = Field(description="Reasoning behind the classification")

# Create email analyzer chain
classifier_chain = create_structured_output_chain(
    llm,
    EmailAnalysis,
    prompt_template="""
    Analyze the following email from a customer to a fashion store. 
    Classify it as either a 'product_inquiry' or an 'order_request' based on the primary intent.
    
    EMAIL SUBJECT: {subject}
    EMAIL BODY: {body}
    
    Even if the email contains both inquiries and order elements, you must classify it as ONE of the two categories based on the dominant intent.
    
    Also extract:
    1. All product references (direct IDs, names, descriptions)
    2. The email's language and tone
    3. Customer signals based on our sales intelligence framework
    
    PRODUCT REFERENCE FORMATS:
    - Direct product IDs (e.g., "RSG8901", "LTH0976")
    - Product names (e.g., "Sleek Wallet", "Infinity Scarf")
    - Product IDs with formatting variations (e.g., "CBT 89 01", "[RSG-8901]")
    - Vague descriptions (e.g., "a dress for summer wedding", "that popular item")
    
    CUSTOMER SIGNALS TO DETECT:
    - Purchase intent signals (direct intent, browsing, price inquiry)
    - Customer context (business use, gift purchase, seasonal need)
    - Communication style (formal/casual, detailed/concise)
    - Emotional signals (enthusiasm, uncertainty, frustration)
    - Objection signals (price concerns, quality concerns)
    
    For each detection, include the exact excerpt from the email that led to this conclusion.
    
    Provide a comprehensive analysis with confidence levels.
    """
)

# Add a verification step for structured output
def verify_email_analysis(analysis):
    """Verify the email analysis output and request fixes if needed"""
    verification_errors = []
    
    # Verify classification is one of the required values
    if analysis.classification not in ["product_inquiry", "order_request"]:
        verification_errors.append("Classification must be either 'product_inquiry' or 'order_request'")
    
    # Verify product references have sufficient information
    for i, ref in enumerate(analysis.product_references):
        if ref.reference_type not in ["product_id", "product_name", "description", "category"]:
            verification_errors.append(f"Product reference {i} has invalid reference_type: {ref.reference_type}")
        if ref.quantity < 1:
            verification_errors.append(f"Product reference {i} has invalid quantity: {ref.quantity}")
        if not ref.excerpt:
            verification_errors.append(f"Product reference {i} is missing the excerpt from the email")
    
    # Verify signals have required fields
    for i, signal in enumerate(analysis.customer_signals):
        if not signal.signal_type or not signal.signal_category:
            verification_errors.append(f"Customer signal {i} is missing required fields")
        if not signal.excerpt:
            verification_errors.append(f"Customer signal {i} is missing the excerpt from the email")
    
    if verification_errors:
        # Request fixes from the LLM
        fix_prompt = f"""
        The email analysis has the following errors that need to be fixed:
        
        {verification_errors}
        
        Please fix these issues in the analysis.
        
        Original analysis:
        {analysis}
        """
        
        # Call LLM to fix the analysis
        fixed_analysis = llm.invoke(fix_prompt)
        return fixed_analysis
    
    return analysis
```

### 2. Order Processor Agent

**Purpose**: Process order requests, check inventory, update stock levels

**Input**:
- Email analysis from Analyzer Agent
- Resolved product references
- Current inventory data

**Output**:
- Order status records (created/out of stock)
- Updated inventory
- Order summary for response generation

**Implementation**:
```python
class OrderItem(BaseModel):
    """Pydantic model for an individual order item"""
    product_id: str = Field(description="Product ID")
    product_name: str = Field(description="Product name")
    quantity: int = Field(description="Requested quantity")
    status: str = Field(description="'created' or 'out_of_stock'")
    unit_price: float = Field(description="Unit price")
    promotion: Optional[str] = Field(description="Applicable promotion if any")

class AlternativeProduct(BaseModel):
    """Pydantic model for a recommended alternative product"""
    product_id: str = Field(description="Product ID")
    product_name: str = Field(description="Product name")
    similarity_score: float = Field(description="Similarity score to the requested product")
    availability: int = Field(description="Current stock level")
    price: float = Field(description="Product price")
    reason: str = Field(description="Reason this product is recommended as an alternative")

class OrderProcessingResult(BaseModel):
    """Pydantic model for the complete order processing result"""
    email_id: str = Field(description="Email ID")
    order_items: List[OrderItem] = Field(description="Processed order items")
    fulfilled_items: int = Field(description="Number of fulfilled items")
    out_of_stock_items: int = Field(description="Number of out-of-stock items")
    total_price: float = Field(description="Total order price")
    recommended_alternatives: List[dict] = Field(description="Recommended alternatives for out-of-stock items")
    
async def process_order(email_analysis, product_db, inventory):
    """Process an order, checking inventory and updating stock"""
    
    # Step 1: Resolve product references to actual product IDs
    resolved_products = await resolve_product_references(email_analysis.product_references, product_db)
    
    # Step 2: Process each resolved product
    order_items = []
    fulfilled_items = 0
    out_of_stock_items = 0
    total_price = 0
    recommended_alternatives = []
    
    for product in resolved_products:
        product_id = product['product_id']
        quantity = product['quantity']
        
        # Get current product info from inventory
        product_info = inventory.get_product(product_id)
        
        if product_info.stock >= quantity:
            # Order can be fulfilled
            status = "created"
            fulfilled_items += 1
            
            # Update inventory
            inventory.update_stock(product_id, product_info.stock - quantity)
            
            # Add to order price
            item_price = product_info.price * quantity
            total_price += item_price
        else:
            # Out of stock
            status = "out_of_stock"
            out_of_stock_items += 1
            
            # Find alternative products
            alternatives = find_alternative_products(product_info, inventory, product_db)
            if alternatives:
                recommended_alternatives.append({
                    'original_product': product_info,
                    'alternatives': alternatives
                })
        
        # Extract any promotion from product description
        promotion = extract_promotion(product_info.description)
        
        # Add to order items
        order_items.append(OrderItem(
            product_id=product_id,
            product_name=product_info.name,
            quantity=quantity,
            status=status,
            unit_price=product_info.price,
            promotion=promotion
        ))
    
    # Create result
    result = OrderProcessingResult(
        email_id=email_analysis.email_id,
        order_items=order_items,
        fulfilled_items=fulfilled_items,
        out_of_stock_items=out_of_stock_items,
        total_price=total_price,
        recommended_alternatives=recommended_alternatives
    )
    
    # Verify result
    verified_result = verify_order_processing(result)
    
    return verified_result

def verify_order_processing(result):
    """Verify order processing result and fix if needed"""
    verification_errors = []
    
    # Check that all necessary fields are populated
    if not result.order_items:
        verification_errors.append("No order items found in the result")
    
    # Verify counts
    if result.fulfilled_items + result.out_of_stock_items != len(result.order_items):
        verification_errors.append("Item counts do not match the number of order items")
    
    # Verify total price
    calculated_price = sum(item.unit_price * item.quantity for item in result.order_items 
                           if item.status == "created")
    if abs(calculated_price - result.total_price) > 0.01:  # Allow small float difference
        verification_errors.append(f"Total price {result.total_price} doesn't match calculated price {calculated_price}")
    
    if verification_errors:
        # Request fixes
        fix_prompt = f"""
        The order processing result has the following errors:
        
        {verification_errors}
        
        Please fix these issues in the result.
        
        Original result:
        {result}
        """
        
        fixed_result = llm.invoke(fix_prompt)
        return fixed_result
    
    return result
```

### 3. Inquiry Responder Agent

**Purpose**: Generate detailed responses to product inquiries using RAG

**Input**:
- Email analysis from Analyzer Agent
- Product details from vector store

**Output**:
- Structured information addressing all inquiry elements
- Product specifications relevant to the inquiry
- Alternatives or complementary product information

**Implementation**:
```python
class ProductInformation(BaseModel):
    """Pydantic model for product information"""
    product_id: str = Field(description="Product ID")
    product_name: str = Field(description="Product name")
    details: dict = Field(description="Product details relevant to the inquiry")
    availability: str = Field(description="Availability status")
    price: float = Field(description="Product price")
    promotions: Optional[str] = Field(description="Any promotions for this product")

class QuestionAnswer(BaseModel):
    """Pydantic model for a question and its answer"""
    question: str = Field(description="Customer's question extracted or inferred from the email")
    question_excerpt: str = Field(description="The text from the email that contains this question")
    answer: str = Field(description="Answer to the question based on product information")
    confidence: float = Field(description="Confidence in the answer (0-1)")
    relevant_product_ids: List[str] = Field(description="Product IDs relevant to this answer")

class InquiryResponse(BaseModel):
    """Pydantic model for the complete inquiry response"""
    email_id: str = Field(description="Email ID")
    primary_products: List[ProductInformation] = Field(description="Main products the customer inquired about")
    answered_questions: List[QuestionAnswer] = Field(description="Questions answered with information")
    related_products: List[ProductInformation] = Field(description="Related or complementary products")
    response_points: List[str] = Field(description="Key points to include in response")
    
async def process_inquiry(email_analysis, product_db):
    """Generate structured response to product inquiries"""
    
    # Step 1: Resolve product references to actual product IDs
    product_references = email_analysis.product_references
    resolved_products = await resolve_product_references(product_references, product_db)
    
    # Step 2: Extract customer questions/needs based on signals
    customer_signals = email_analysis.customer_signals
    customer_questions = extract_questions_from_signals(customer_signals, email_analysis.classification_reasoning)
    
    # Step 3: Get detailed product information
    primary_products = []
    for product in resolved_products:
        product_info = product_db.get_product(product['product_id'])
        
        # Get details relevant to the customer's inquiry
        relevant_details = extract_relevant_details(product_info, customer_questions)
        
        # Check availability
        availability = "In stock" if product_info.stock > 0 else "Out of stock"
        
        # Extract promotions
        promotions = extract_promotion(product_info.description)
        
        primary_products.append(ProductInformation(
            product_id=product_info.id,
            product_name=product_info.name,
            details=relevant_details,
            availability=availability,
            price=product_info.price,
            promotions=promotions
        ))
    
    # Step 4: Answer customer questions
    answered_questions = []
    for question in customer_questions:
        # Find the email excerpt containing this question
        question_excerpt = find_question_excerpt(question, email_analysis)
        
        # Generate answer
        answer = generate_answer_to_question(question, primary_products, product_db)
        
        # Determine relevant product IDs for this question
        relevant_product_ids = identify_relevant_products_for_question(question, primary_products)
        
        answered_questions.append(QuestionAnswer(
            question=question,
            question_excerpt=question_excerpt,
            answer=answer,
            confidence=calculate_answer_confidence(question, answer, primary_products),
            relevant_product_ids=relevant_product_ids
        ))
    
    # Step 5: Find related or complementary products
    related_products = find_related_products(primary_products, customer_signals, product_db)
    
    # Step 6: Generate key response points
    response_points = generate_response_points(
        primary_products, 
        answered_questions, 
        related_products, 
        email_analysis
    )
    
    # Create result
    result = InquiryResponse(
        email_id=email_analysis.email_id,
        primary_products=primary_products,
        answered_questions=answered_questions,
        related_products=related_products,
        response_points=response_points
    )
    
    # Verify result
    verified_result = verify_inquiry_response(result)
    
    return verified_result

def verify_inquiry_response(result):
    """Verify inquiry response and fix if needed"""
    verification_errors = []
    
    # Check that primary products are populated or questions are answered
    if not result.primary_products and not result.answered_questions:
        verification_errors.append("No primary products or answered questions found")
    
    # Verify question answers have excerpts
    for i, qa in enumerate(result.answered_questions):
        if not qa.question_excerpt:
            verification_errors.append(f"Question {i} missing excerpt from email")
        if not qa.relevant_product_ids and result.primary_products:
            verification_errors.append(f"Question {i} not linked to any products")
    
    # Verify response points
    if not result.response_points:
        verification_errors.append("No response points generated")
    
    if verification_errors:
        # Request fixes
        fix_prompt = f"""
        The inquiry response has the following errors:
        
        {verification_errors}
        
        Please fix these issues in the response.
        
        Original response:
        {result}
        """
        
        fixed_result = llm.invoke(fix_prompt)
        return fixed_result
    
    return result
```

### 4. Response Composer Agent

**Purpose**: Generate final customer responses integrating all information and signals

**Input**:
- Email analysis from Analyzer Agent
- Order processing results (if applicable)
- Inquiry response (if applicable)
- Sales intelligence signals

**Output**:
- Final customer response with appropriate tone, structure and content
- All required information addressed in a cohesive manner

**Implementation**:
```python
class ResponseComposition(BaseModel):
    """Pydantic model for the composition plan"""
    greeting: str = Field(description="Appropriate greeting based on customer tone")
    sections: List[dict] = Field(description="Sections of the response with content plans")
    tone_matching: dict = Field(description="How to match customer's tone and style")
    closing: str = Field(description="Appropriate closing based on interaction type")

async def compose_response(email_analysis, order_result=None, inquiry_result=None):
    """Generate final customer response"""
    
    # Extract key information for response generation
    email_type = email_analysis.classification
    tone = email_analysis.tone_analysis.tone
    formality_level = email_analysis.tone_analysis.formality_level
    language = email_analysis.language
    signals = email_analysis.customer_signals
    
    # Format product information based on results
    product_info = ""
    if order_result:
        product_info += format_order_details(order_result)
    
    if inquiry_result:
        product_info += format_inquiry_details(inquiry_result)
    
    # Extract signals for response customization
    signal_actions = process_customer_signals(signals)
    
    # Determine the response structure based on signals and email type
    response_structure = determine_response_structure(email_type, signals, order_result, inquiry_result)
    
    # Generate appropriate greeting based on formality
    greeting = generate_greeting(email_analysis)
    
    # Determine emotional tone response
    emotional_response = generate_emotional_response(signals)
    
    # Create composition plan
    composition_plan = ResponseComposition(
        greeting=greeting,
        sections=[
            {"type": "emotional_acknowledgment", "content": emotional_response},
            {"type": "main_response", "content": response_structure},
            {"type": "additional_information", "content": signal_actions}
        ],
        tone_matching={
            "formality": formality_level,
            "style": tone,
            "language": language,
            "key_phrases": email_analysis.tone_analysis.key_phrases
        },
        closing=generate_closing(email_analysis, order_result)
    )
    
    # Create response prompt for the LLM
    prompt = f"""
    Generate a {tone}, level-{formality_level} formality response to this customer in {language}.
    
    CUSTOMER EMAIL ANALYSIS:
    - Type: {email_type}
    - Tone: {tone}
    - Formality: {formality_level}
    - Emotional signals: {[s for s in signals if s.signal_category == 'Emotion and Tone']}
    
    PRODUCT INFORMATION:
    {product_info}
    
    SIGNAL-BASED ACTIONS:
    {signal_actions}
    
    RESPONSE STRUCTURE:
    {response_structure}
    
    GREETING TO USE:
    {greeting}
    
    EMOTIONAL RESPONSE TO INCLUDE:
    {emotional_response}
    
    COMPOSITION PLAN:
    {composition_plan}
    
    Generate a natural, helpful response that sounds like a real person, not a template.
    Use appropriate contractions, sentence variety, and authentic enthusiasm.
    The response should be professional, warm, and address all customer needs while
    incorporating the signal-based actions where appropriate.
    
    DO NOT use phrases like "Based on your inquiry" or "I notice you're interested in".
    DO use natural language like "These boots are perfect for fall" or "You'll love how versatile this bag is".
    """
    
    # Generate the response
    response = llm.invoke(prompt)
    
    # Verify response quality
    verified_response = verify_response_quality(
        response, 
        email_analysis, 
        order_result, 
        inquiry_result
    )
    
    return verified_response

def process_customer_signals(signals):
    """Process customer signals into specific response actions"""
    actions = []
    
    # Process signals by category using the sales intelligence framework
    for signal in signals:
        category = signal.signal_category
        signal_type = signal.signal_type
        excerpt = signal.excerpt
        
        if category == "Purchase Intent":
            if signal_type == "Direct Intent":
                actions.append({
                    "action": "Confirm order details clearly and concisely", 
                    "based_on": excerpt
                })
            elif signal_type == "Browsing Intent":
                actions.append({
                    "action": "Provide detailed product information without pushing for immediate purchase", 
                    "based_on": excerpt
                })
                
        elif category == "Customer Context":
            if signal_type == "Business Use":
                actions.append({
                    "action": "Mention wholesale options and business-relevant features", 
                    "based_on": excerpt
                })
            elif signal_type == "Gift Purchase":
                actions.append({
                    "action": "Highlight gift-worthiness and suggest gift wrapping options", 
                    "based_on": excerpt
                })
                
        elif category == "Emotion and Tone":
            if signal_type == "Enthusiasm":
                actions.append({
                    "action": "Mirror enthusiasm and validate their excitement", 
                    "based_on": excerpt
                })
            elif signal_type == "Uncertainty":
                actions.append({
                    "action": "Provide clear, decisive information and recommendations", 
                    "based_on": excerpt
                })
        
        # Add more signal processing based on the sales intelligence guide
                
    return actions

def verify_response_quality(response, email_analysis, order_result, inquiry_result):
    """Verify the quality of the generated response and fix if needed"""
    verification_errors = []
    
    # Check if response addresses all products mentioned
    if email_analysis.product_references:
        for ref in email_analysis.product_references:
            if ref.product_name and ref.product_name.lower() not in response.lower():
                verification_errors.append(f"Response doesn't mention product: {ref.product_name}")
    
    # Check if order status is clearly communicated
    if order_result and order_result.out_of_stock_items > 0:
        if "out of stock" not in response.lower() and "unavailable" not in response.lower():
            verification_errors.append("Response doesn't clearly communicate out-of-stock items")
    
    # Check if inquiry questions are answered
    if inquiry_result and inquiry_result.answered_questions:
        # Check for presence of key answer terms
        for qa in inquiry_result.answered_questions:
            key_terms = extract_key_terms(qa.answer)
            if not any(term.lower() in response.lower() for term in key_terms):
                verification_errors.append(f"Response doesn't address question: {qa.question}")
    
    # Check for templated language
    templated_phrases = [
        "based on your inquiry",
        "as per your request",
        "in response to your email",
        "thank you for contacting us",
        "we would be happy to"
    ]
    
    for phrase in templated_phrases:
        if phrase in response.lower():
            verification_errors.append(f"Response contains templated phrase: '{phrase}'")
    
    if verification_errors:
        # Request fixes
        fix_prompt = f"""
        The customer response has the following issues:
        
        {verification_errors}
        
        Please revise the response to fix these issues while maintaining a natural, conversational tone.
        Make sure the response addresses all products, communicates stock status clearly, answers all questions,
        and avoids templated language.
        
        Original response:
        {response}
        """
        
        fixed_response = llm.invoke(fix_prompt)
        return fixed_response
    
    return response
```

## Tools and Utilities for Agents

The agents require specialized tools to access product information, manage inventory, and generate responses. Here's a breakdown of the required tools for each agent:

### 1. Product Catalog Tools

```python
# Tool: Find product by ID
def find_product_by_id(product_id: str) -> dict:
    """
    Retrieve product information by exact product ID
    
    Args:
        product_id: The product ID to look up
        
    Returns:
        Complete product information or None if not found
    """
    # Implementation that queries the product database
    pass

# Tool: Find product by name
def find_product_by_name(product_name: str, threshold: float = 0.8) -> List[dict]:
    """
    Find products matching a name using fuzzy matching
    
    Args:
        product_name: The product name to search for
        threshold: Minimum similarity score (0-1)
        
    Returns:
        List of matching products with similarity scores
    """
    # Implementation using fuzzy string matching
    pass

# Tool: Search products by description
def search_products_by_description(query: str, top_k: int = 5) -> List[dict]:
    """
    Search products using semantic similarity on descriptions
    
    Args:
        query: The search query
        top_k: Number of results to return
        
    Returns:
        List of relevant products with similarity scores
    """
    # Implementation using vector embeddings and similarity search
    pass

# Tool: Find related products
def find_related_products(product_id: str, relationship_type: str = "complementary", limit: int = 3) -> List[dict]:
    """
    Find products related to a given product
    
    Args:
        product_id: The reference product ID
        relationship_type: Type of relationship ("complementary", "alternative", "same_category")
        limit: Maximum number of results
        
    Returns:
        List of related products with relationship explanations
    """
    # Implementation based on product categories and relationships
    pass
```

### 2. Inventory Management Tools

```python
# Tool: Check product stock
def check_stock(product_id: str) -> dict:
    """
    Check current stock level for a product
    
    Args:
        product_id: The product ID to check
        
    Returns:
        Stock information including quantity and status
    """
    # Implementation that queries inventory
    pass

# Tool: Update product stock
def update_stock(product_id: str, quantity_change: int) -> dict:
    """
    Update stock level for a product
    
    Args:
        product_id: The product ID to update
        quantity_change: Amount to add (positive) or remove (negative)
        
    Returns:
        Updated stock information
    """
    # Implementation that modifies inventory
    pass

# Tool: Find alternative for out-of-stock product
def find_alternatives_for_oos(product_id: str, limit: int = 3) -> List[dict]:
    """
    Find in-stock alternatives for an out-of-stock product
    
    Args:
        product_id: The out-of-stock product ID
        limit: Maximum number of alternatives to return
        
    Returns:
        List of in-stock alternative products with similarity scores
    """
    # Implementation based on category, features, and stock levels
    pass
```

### 3. Order Processing Tools

```python
# Tool: Create order
def create_order(email_id: str, items: List[dict]) -> dict:
    """
    Create a new order with multiple items
    
    Args:
        email_id: The email ID the order is associated with
        items: List of items (product_id, quantity)
        
    Returns:
        Complete order information including status per item
    """
    # Implementation that processes the order
    pass

# Tool: Check order status
def check_order_status(email_id: str) -> dict:
    """
    Check status of orders associated with an email
    
    Args:
        email_id: The email ID to check
        
    Returns:
        Order status information for all items
    """
    # Implementation that retrieves order status
    pass

# Tool: Extract promotions from product description
def extract_promotion(description: str) -> Optional[str]:
    """
    Extract promotional information from product description
    
    Args:
        description: The product description text
        
    Returns:
        Extracted promotion or None if not found
    """
    # Implementation using regex or LLM-based extraction
    pass
```

### 4. Natural Language Processing Tools

```python
# Tool: Analyze tone
def analyze_tone(text: str) -> dict:
    """
    Analyze the tone, formality and style of text
    
    Args:
        text: The text to analyze
        
    Returns:
        Tone analysis with formality level and key phrases
    """
    # Implementation using LLM
    pass

# Tool: Extract questions
def extract_questions_from_text(text: str) -> List[dict]:
    """
    Extract explicit and implicit questions from text
    
    Args:
        text: The text to analyze
        
    Returns:
        List of extracted questions with confidence levels
    """
    # Implementation using LLM
    pass

# Tool: Generate natural language response
def generate_natural_response(composition_plan: dict) -> str:
    """
    Generate a natural-sounding response based on a composition plan
    
    Args:
        composition_plan: Structured plan for the response
        
    Returns:
        Generated natural language response
    """
    # Implementation using LLM
    pass
```

## Main Processing Flow

The main processing flow integrates all agents into a cohesive pipeline using LangGraph.

```python
from langgraph.graph import StateGraph
from typing_extensions import TypedDict

# Define the state schema
class HermesState(TypedDict):
    email_id: str
    email_subject: str
    email_body: str
    email_analysis: dict
    order_result: Optional[dict]
    inquiry_result: Optional[dict]
    final_response: str

# Create the graph
workflow = StateGraph(HermesState)

# Define the email analyzer function
async def analyze_email(state):
    email_id = state["email_id"]
    subject = state["email_subject"]
    body = state["email_body"]
    
    # Run email analysis
    analysis = await classifier_chain.ainvoke({"subject": subject, "body": body})
    
    # Verify and potentially fix the analysis
    verified_analysis = verify_email_analysis(analysis)
    
    return {"email_analysis": verified_analysis}

# Define conditional routing based on email classification
def route_by_classification(state):
    classification = state["email_analysis"]["classification"]
    
    if classification == "order_request":
        return "process_order"
    else:  # product_inquiry
        return "process_inquiry"

# Define the order processing function
async def handle_order(state):
    analysis = state["email_analysis"]
    
    # Process order
    order_result = await process_order(analysis, product_db, inventory)
    
    return {"order_result": order_result}

# Define the inquiry processing function
async def handle_inquiry(state):
    analysis = state["email_analysis"]
    
    # Process inquiry
    inquiry_result = await process_inquiry(analysis, product_db)
    
    return {"inquiry_result": inquiry_result}

# Define the response composition function
async def create_response(state):
    analysis = state["email_analysis"]
    order_result = state.get("order_result")
    inquiry_result = state.get("inquiry_result")
    
    # Generate final response
    final_response = await compose_response(analysis, order_result, inquiry_result)
    
    return {"final_response": final_response}

# Add nodes to the graph
workflow.add_node("analyze_email", analyze_email)
workflow.add_node("process_order", handle_order)
workflow.add_node("process_inquiry", handle_inquiry)
workflow.add_node("compose_response", create_response)

# Add edges
workflow.add_edge("analyze_email", route_by_classification)
workflow.add_conditional_edges(
    "analyze_email",
    route_by_classification,
    {
        "process_order": "process_order",
        "process_inquiry": "process_inquiry"
    }
)
workflow.add_edge("process_order", "compose_response")
workflow.add_edge("process_inquiry", "compose_response")

# Create the compiled workflow
hermes_workflow = workflow.compile()
```

## Processing Loop for All Emails

The main loop processes each email through the workflow:

```python
async def process_all_emails(emails_df, product_db):
    """Process all emails through the Hermes workflow"""
    
    results = {
        'email_classification': [],
        'order_status': [],
        'order_response': [],
        'inquiry_response': []
    }
    
    # Initialize vector store and inventory
    vector_store = setup_vector_store(product_db)
    inventory = initialize_inventory(product_db)
    
    # Process each email
    for _, email in emails_df.iterrows():
        email_id = email['email ID']
        subject = email['subject'] if not pd.isna(email['subject']) else ""
        body = email['body']
        
        print(f"Processing email {email_id}...")
        
        # Initialize state for this email
        initial_state = HermesState(
            email_id=email_id,
            email_subject=subject,
            email_body=body,
            email_analysis=None,
            order_result=None,
            inquiry_result=None,
            final_response=None
        )
        
        # Process the email through the workflow
        final_state = await hermes_workflow.ainvoke(initial_state)
        
        # Extract results
        analysis = final_state["email_analysis"]
        results['email_classification'].append({
            'email ID': email_id,
            'category': analysis["classification"]
        })
        
        # Add order status if applicable
        if final_state["order_result"]:
            order_result = final_state["order_result"]
            for item in order_result["order_items"]:
                results['order_status'].append({
                    'email ID': email_id,
                    'product ID': item["product_id"],
                    'quantity': item["quantity"],
                    'status': item["status"]
                })
            
            # Add order response
            if analysis["classification"] == "order_request":
                results['order_response'].append({
                    'email ID': email_id,
                    'response': final_state["final_response"]
                })
        
        # Add inquiry response if applicable
        if analysis["classification"] == "product_inquiry":
            results['inquiry_response'].append({
                'email ID': email_id,
                'response': final_state["final_response"]
            })
    
    # Convert results to DataFrames
    for key in results:
        results[key] = pd.DataFrame(results[key])
    
    return results
```

## Agent Collaboration and Verification

### Key Advantages of This 4-Agent Architecture

1. **Clear Separation of Concerns**:
   - Email Analyzer handles comprehensive analysis including classification, extracting product references, and detecting customer signals
   - Order Processor and Inquiry Responder focus exclusively on their specific business logic
   - Response Composer handles the final presentation layer, integrating all information

2. **Integrated Sales Intelligence Framework**:
   - Email Analyzer detects signals from the sales intelligence guide 
   - Signal processing in both business logic and response composition
   - Custom response elements based on detected signals

3. **Structured Verification System**:
   - Each agent includes verification steps to validate outputs
   - Automated correction requests when issues are detected
   - Multiple validation points throughout the workflow

4. **Binary Classification with Nuanced Processing**:
   - Binary classification as required (product_inquiry/order_request)
   - Still handles emails with mixed elements through signal detection and processing
   - Maintains adherence to assignment requirements

5. **Optimized Agent Boundary Decisions**:
   - Email Analyzer detects all signals to provide full context
   - Business logic agents focus on specific processing needs
   - Composer integrates signal handling with business results

6. **Pydantic Integration**:
   - Full Pydantic model usage for structured inputs and outputs
   - Leverages LangChain and LangGraph native Pydantic support
   - Enables robust validation and type checking

7. **Evidence-Based Analysis**:
   - Includes excerpts from the original email for each detection
   - Provides clear traceability between customer statements and system actions
   - Enhances verifiability and debugging

This architecture balances completeness with efficiency, ensuring all assignment requirements are met while maintaining a clear, maintainable system that can be enhanced and extended as needed. 