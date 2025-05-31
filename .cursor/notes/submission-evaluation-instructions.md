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

**Order Request Classification** - Must be ready for immediate order processing:
- ✅ Direct order commands (e.g., "I want to order", "Please send me", "I'd like to buy")
- ✅ Specific quantity requests without conditions (e.g., "Send me 5 units")
- ✅ Immediate purchase intent without prerequisites
- ✅ Ready for stock verification and order creation

**Product Inquiry Classification** - Seeking information before ordering:
- ✅ Questions about products, features, availability, pricing
- ✅ Requests for recommendations or comparisons
- ✅ Purchase intent **conditional on information** (e.g., "confirm availability first, before we move forward")
- ✅ Availability checks before committing to purchase
- ✅ Product research and information gathering

**Critical Distinction**:
- **Order Request**: Ready for immediate processing (stock check → order creation → stock update)
- **Product Inquiry**: Requires information response first, order processing may follow later

**Mixed Intent Emails**: Classify by **actionable intent**:
- If email requires information before order processing → "product inquiry"
- If email is ready for immediate order processing → "order request"

**Examples**:
- ❌ WRONG: "I'm prepared to commit... Just need you to confirm availability first" = This is **product inquiry** (needs availability confirmation before order)
- ✅ CORRECT: "I want to order 5 units" = This is **order request** (ready for immediate processing)
- ✅ CORRECT: "What's the price of X?" = This is **product inquiry** (seeking information)

**Expected Output**: `email-classification.csv` with columns: email ID, category

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