# Hidden Evaluation Criteria: Edge Cases and Advanced Processing

This document outlines the "hidden" challenges and edge cases embedded in the sample data that candidates should discover and address independently. Interviewers should use this as a checklist to evaluate the robustness and sophistication of candidate solutions.

## Core Hidden Challenges

### 1. Multi-Language Support

**Challenge**: Some emails are written in languages other than English.

**Example**:
- E009: "Hola, tengo una pregunta sobre el DHN0987 Gorro de punto grueso. ¿De qué material está hecho? ¿Es lo suficientemente cálido para usar en invierno? Gracias de antemano."

**Expected Solution**:
- Language detection
- Ability to understand and respond in the detected language
- Correct product matching despite language differences

**Testing**: Check if the solution correctly identifies Spanish and provides a coherent response in Spanish.

### 2. Complex Product Reference Patterns

**Challenge**: Products are referenced in various formats beyond simple product IDs.

**Examples**:
- **Direct ID**: E010 "I would like to order 1 pair of RSG8901 Retro Sunglasses"
- **Name Only**: E014 "Please send me 1 Sleek Wallet"
- **Formatted Variations**: E019 "Chelsea Boots [CBT 89 01]"
- **Vague References**: E017 "I want to place an order for that popular item you sell. The one that's been selling like hotcakes lately"
- **Name + Use Case**: E008 "I'd want to order one of your Versatile Scarves, the one that can be worn as a scarf, shawl, or headwrap"

**Expected Solution**:
- Flexible product extraction logic
- Fuzzy matching for product names
- Contextual inference for vague references
- Resolution of formatting variations to canonical product IDs

**Testing**: Check how the solution handles each reference pattern type, particularly the more challenging vague references.

### 3. Mixed Intent/Future Purchase Handling

**Challenge**: Some emails contain both immediate orders and future considerations.

**Examples**:
- E019: "I would like to order Retro sunglasses from you, but probably next time!"
- E006: "I was thinking of ordering a pair of CBT8901 Chelsea Boots, but I'll wait until Fall to actually place the order"

**Expected Solution**:
- Ability to distinguish between immediate order intent and future considerations
- Not processing future interest as a current order
- Acknowledgment of future interest while focusing on actionable requests

**Testing**: Verify the solution correctly processes or declines to process these ambiguous cases.

### 4. Inventory Edge Cases

**Challenge**: Managing limited inventory products and providing alternatives.

**Examples**:
- RSG8901 (Retro Sunglasses): stock=1
- E010: "I would like to order 1 pair of RSG8901 Retro Sunglasses"
- E018: "I'd like to buy 2 pairs of the retro sun glasses (RSG8901)"

**Expected Solution**:
- Proper inventory tracking
- Out-of-stock handling when order quantity exceeds stock
- Suggesting alternative products when items are out of stock
- Partial order fulfillment logic

**Testing**: Check how the solution handles orders for the last item in stock and orders that exceed available stock.

### 5. Email Metadata Inconsistencies

**Challenge**: Some emails lack subject lines or have minimal metadata.

**Examples**:
- No subject: E006, E017, E021
- Minimal subject: E019 ("Hi")

**Expected Solution**:
- Resilience to missing metadata
- Focus on email body content for classification and processing
- Not failing when standard fields are missing

**Testing**: Verify the solution successfully processes emails with missing subjects.

### 6. Special Product Data Handling

**Challenge**: Products have special promotions, seasonal attributes, and relationships that should be reflected in responses.

**Examples**:
- CBG9876 (Canvas Beach Bag): "Buy one, get one 50% off!"
- TLR5432 (Tailored Suit): "Limited-time sale - get the full suit for the price of the blazer!"
- BMX5432 (Bomber Jacket): "Buy now and get a free matching beanie!"
- PLV8765 (Plaid Flannel Vest): "Buy one, get a matching plaid shirt at 50% off!"

**Expected Solution**:
- Extraction of promotion information from product descriptions
- Mention of relevant promotions in responses
- Seasonal appropriateness acknowledgment
- Identification of product relationships for alternatives/upselling

**Testing**: Check if responses mention relevant promotions and seasonal information.

### 7. Seasonal/Occasion-Specific Inquiries

**Challenge**: Emails asking about product suitability for specific seasons or occasions.

**Examples**:
- E020: "Hello I'd like to know how much does Saddle bag cost and if it is suitable for spring season?"
- E016: "I'm looking for a dress for a summer wedding I have coming up"

**Expected Solution**:
- Matching seasonal inquiries to product season metadata
- Providing relevant seasonal appropriateness information
- Recommending products suitable for specific occasions

**Testing**: Verify seasonal appropriateness is addressed in responses.

### 8. Tone/Style Adaptation

**Challenge**: Emails exhibit widely varying communication styles.

**Examples**:
- Formal: E005 "Good day, For the CSH1098 Cozy Shawl, the description mentions..."
- Casual: E002 "Good morning, I'm looking to buy the VBT2345 Vibrant Tote bag. My name is Jessica and I love tote bags..."
- Rambling: E012 "Hey, hope you're doing well. Last year for my birthday, my wife Emily got me..."

**Expected Solution**:
- Detection of communication style/tone
- Adaptation of response style to match the customer's tone
- Maintaining professionalism while reflecting the customer's style

**Testing**: Compare response tone across different email styles to verify adaptation.

### 9. Email Classification Complexity

**Challenge**: Some emails contain elements of both inquiry and order, requiring nuanced classification.

**Examples**:
- E019: Contains both order intent and future order consideration
- E016: Inquiry about dresses but also mentions needing a bag

**Expected Solution**:
- Clear binary classification as required by the assignment
- Appropriate handling of mixed elements within the chosen classification
- Evidence-based decision making when classifying

**Testing**: Verify consistent classification approach for complex cases.

### 10. Tangential Information Handling

**Challenge**: Emails contain personal anecdotes or tangential information.

**Examples**:
- E012: "Oh and we also need to make dinner reservations for our anniversary next month"
- E002: "Last summer I bought this really cute straw tote that I used at the beach. Oh, and a few years ago I got this nylon tote as a free gift with purchase that I still use for groceries"

**Expected Solution**:
- Focus on actionable fashion-related content
- Brief acknowledgment of personal details when appropriate
- Not getting distracted by unrelated information

**Testing**: Check if responses stay focused on relevant product information.

## Hidden Extra Credit: Customer Signal Processing

The reference solution implements an advanced customer signal processing framework as outlined in `customer-signal-processing.md`. This represents a sophisticated level of AI implementation that goes beyond the basic requirements but demonstrates mastery of LLM techniques.

### Key Signal Categories

1. **Product Identification Signals**
2. **Purchase Intent Signals**
3. **Customer Context Signals**
4. **Request Specificity Signals**
5. **Upsell/Cross-sell Opportunity Signals**
6. **Communication Style Signals**
7. **Language/Cultural Signals**
8. **Emotion and Tone Signals**
9. **Objection Signals**
10. **Irrelevant Information Signals**

### Testing Customer Signal Processing

While not explicitly required, superior solutions may show evidence of:

- Detection of customer signals beyond basic intent and product references
- Adaptation of responses based on detected signals
- Natural, non-templated language that adapts to customer communication style
- Personalization based on customer context clues
- Incorporation of emotional intelligence in responses

## Evaluation Guide

When reviewing candidate solutions, rate their handling of these hidden concerns on a scale:

1. **Not Addressed**: No evidence of considering this edge case
2. **Basic Handling**: Minimal handling of the edge case without sophistication
3. **Comprehensive Solution**: Robust handling with clear implementation patterns
4. **Advanced Implementation**: Sophisticated handling demonstrating mastery of LLM techniques

The reference solution in `reference-agent-flow.md` provides the benchmark for a comprehensive (level 3) to advanced (level 4) implementation.

### Minimum Acceptance Criteria

To be considered a valid solution, candidates should handle at least:
- Basic product reference extraction (direct IDs and names)
- Binary classification of emails
- Simple inventory management
- Order status tracking
- Basic response generation

### Superior Solution Indicators

Top-tier solutions will demonstrate:
- Handling of all edge cases listed in this document
- Structured, modular architecture following LangChain/LangGraph best practices
- Evidence of customer signal processing (possibly without explicitly naming it)
- Sophisticated RAG implementation for product inquiries
- Comprehensive testing for edge cases 