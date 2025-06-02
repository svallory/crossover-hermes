# Submission Evaluation Instructions

## Overview
This document outlines the evaluation criteria and methodology for assessing the email order processing system submission. The system should intelligently process email order requests and customer inquiries for a fashion store.

## File Structure Requirements
The submission should contain:
- `results/[email_id].yml` files (results/E001.yml, results/E002.yml, etc.) - Processing details
- `email-classification.csv` - Classification results
- `inquiry-response.csv` - Inquiry responses
- `order-response.csv` - Order responses
- `order-status.csv` - Order status tracking

## Evaluation Categories

### 1. Email Classification Accuracy
**Requirement**: Classify each email as either "product inquiry" or "order request"

**Evaluation Rules**:

**Core Principle for Classification**:
The classification of an email as an "order request" or "product inquiry" hinges on whether the customer's stated intent can be *immediately actioned* as a purchase by the system, or if it first requires informational prerequisites (e.g., answers to questions, confirmation of details) to be met.

**Rule for "Order Request" Classification**:
An email can ONLY be classified as an "order request" if it meets ALL of the following criteria:
1.  It expresses a clear, unconditional, and unambiguous intent from the customer to purchase specific items.
2.  The intent to purchase is *immediately actionable* by the system. This means the system can proceed directly to stock verification, order line creation, and stock updates based solely on the information provided in (or firmly established by prior context referenced in) the email.
3.  The email does NOT contain any conditions that must be satisfied, or any questions that must be answered by the store, *before* the customer's commitment to purchase is considered final and the order can be processed.
    *   *Example of an immediately actionable order*: "I want to order 5 units of Product X and 2 units of Product Y."
    *   *Example*: "Please send me those three items we discussed." (This is an order request if "those three items" are unambiguously defined from prior interaction and no new conditions are introduced).

**Rule for "Product Inquiry" Classification**:
An email MUST be classified as a "product inquiry" if ANY of the following criteria are met:
1.  It explicitly asks questions about products (e.g., features, availability, sizing, materials), services, store policies (e.g., returns, shipping), or pricing.
    *   *Example*: "What is the price of X?", "Do you have Y in blue?", "What is your return policy?"
2.  It expresses a purchase intent that is *explicitly or implicitly conditional* upon receiving further information or a specific prerequisite being met. The customer is indicating they are not ready for the order to be processed until their condition/question is addressed.
    *   *Example*: "I'm prepared to commit to Product Z, but I just need you to confirm its availability first." (The commitment is conditional on the availability check).
    *   *Example*: "I'd like to buy the LTH1234 bag if it comes in black." (The purchase is conditional on color confirmation).
    *   *Example*: "I want to buy Product A. Is it blue or green?" (The purchase intent for A is gated by the need for color information).
3.  The email's primary purpose is to seek recommendations, advice, or comparisons before a purchase decision is made.

**Handling Mixed Intent Emails**:
If an email contains elements of both a potential order and an inquiry, its primary classification MUST be "product inquiry" if any expressed or implied purchase intent is contingent upon fulfilling an informational prerequisite stated in the same email.
- **Primacy of Conditions/Questions**: The presence of any condition or question that blocks the immediate, unconditional processing of a stated purchase intent makes the *entire email's primary actionable classification* a "product inquiry". The order component cannot be actioned until the inquiry component (the condition/question) is resolved.
    *   *Example*: "I want to order 5 units of Product A. Before you process that, can you tell me if Product B is compatible with it?" (The order for Product A is held back by the question about Product B, making the email a "product inquiry").
    *   *Example*: "Please send me 3 of SKU123. Also, what other colors does SKU456 come in?" If understanding the colors of SKU456 is a prerequisite or could influence the decision on SKU123, or if the customer is clearly in an information-gathering phase for part of their request, the email leans towards "product inquiry". If the request for SKU123 is demonstrably independent and unconditional, the email presents a scenario of separable tasks (one order, one inquiry). However, for a single classification label for the email, any unresolved prerequisite for any part of a potential purchase makes it a "product inquiry".

**Expected Output**: \`email-classification.csv\` with columns: email ID, category

### 2. Order Processing Requirements
**Stock Management Rules**:
- ✅ Verify product availability in actual catalog stock
- ✅ If sufficient stock: create order with status "created"
- ✅ If insufficient stock: create order with status "out of stock"
- ✅ Update stock levels after processing each order
- ✅ Record actual requested quantity for out-of-stock items
- ❌ Creating orders for products not in catalog
- ❌ Incorrect stock calculations
- ❌ Wrong status assignments

**Product Resolution Rules**:
- ✅ Correctly identify products by ID when provided
- ✅ Use semantic search for products mentioned by name/description
- ✅ Handle variations in product naming
- ❌ Fail to resolve valid products
- ❌ Resolve to wrong products
- ❌ Create fictional products

**Expected Output**: `order-status.csv` with columns: email ID, product ID, quantity, status

### 3. Response Generation Quality
**Order Responses**:
- ✅ Inform customer of order status (created/out of stock)
- ✅ Provide actual product details from catalog
- ✅ For out-of-stock: explain situation and suggest alternatives
- ✅ Professional, production-ready tone
- ❌ Use fictional product information not in catalog
- ❌ Incorrect pricing or product details
- ❌ Unprofessional tone

**Inquiry Responses**:
- ✅ Answer questions using actual product catalog information
- ✅ Provide relevant product recommendations
- ✅ Use RAG/vector store techniques for scalability
- ✅ Professional and informative tone
- ❌ Provide information not in the catalog
- ❌ Fail to answer direct product questions
- ❌ Suggest non-existent products

**Expected Outputs**:
- `order-response.csv` with columns: email ID, response
- `inquiry-response.csv` with columns: email ID, response

### 4. Technical Implementation Requirements
**Advanced AI Techniques**:
- ✅ Use of RAG (Retrieval-Augmented Generation)
- ✅ Vector store implementation for product search
- ✅ Semantic product matching
- ✅ Scalable approach for large catalogs (100,000+ products)
- ❌ Hardcoded product lists in prompts
- ❌ Token limit violations
- ❌ Non-scalable approaches

**Data Consistency**:
- ✅ All referenced products exist in the provided catalog
- ✅ Stock numbers are accurately tracked and updated
- ✅ Pricing matches catalog exactly
- ✅ Product descriptions match catalog
- ❌ Fictional products or pricing
- ❌ Inconsistent stock tracking
- ❌ Wrong product categories

### 5. Output Format Compliance
**CSV Format Requirements**:
- ✅ Exact column headers as specified
- ✅ No extra columns or sheets
- ✅ Proper data types and formatting
- ✅ Complete data for all emails
- ❌ Missing or incorrect headers
- ❌ Additional unauthorized columns
- ❌ Incomplete data

**Status Value Requirements**:
- ✅ Use exact status values: "created", "out of stock"
- ✅ Use exact category values: "product inquiry", "order request"
- ❌ Variations like "out_of_stock" or "inquiry"
- ❌ Custom status values

## Critical Failure Modes
These issues represent major system failures:

1. **Response Fabrication**: Generating responses with products/prices not in the provided catalog
2. **Stock Inconsistency**: Incorrect stock calculations or allocations
3. **Intent Misclassification**: Clear orders classified as inquiries or vice versa
4. **Product Resolution Failure**: Unable to find products that exist in catalog
5. **Format Non-compliance**: Output files don't match required structure

## Evaluation Process

### Step 1: Structural Validation
- Verify all required files are present
- Check CSV headers and format compliance
- Validate data completeness

### Step 2: Classification Accuracy
- Review each email's classification against actual intent
- Check for consistency in mixed-intent emails

### Step 3: Product Resolution Validation
- Verify all mentioned products are correctly identified
- Check product IDs, names, categories match catalog
- Validate stock numbers are accurate

### Step 4: Order Processing Logic
- Trace order processing workflow for each order
- Verify stock calculations and updates
- Check status assignments are correct

### Step 5: Response Quality Assessment
- Verify responses use only catalog information
- Check tone and professionalism
- Validate alternatives and recommendations exist in catalog

### Step 6: Technical Implementation Review
- Assess use of RAG and vector store techniques
- Evaluate scalability of approach
- Check for hardcoded limitations

## Scoring Framework
- **Excellent (90-100%)**: All requirements met, minimal issues
- **Good (75-89%)**: Most requirements met, minor issues
- **Satisfactory (60-74%)**: Core functionality works, some major issues
- **Needs Improvement (40-59%)**: Significant issues affecting functionality
- **Unsatisfactory (0-39%)**: Major system failures, unusable

## Common Issues to Watch For
1. Fictional luxury brand responses (e.g., Kelly bags, Birkin bags not in catalog)
2. Incorrect price citations (luxury pricing vs. actual catalog prices)
3. Customer name fabrication when not provided in emails
4. Stock calculation errors
5. Format inconsistencies in status values
6. Missing processing details for some emails