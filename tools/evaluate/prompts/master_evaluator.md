# Master Evaluator Prompt

You are evaluating the performance of a comprehensive email processing system for a high-end fashion retailer called "Luxe Fashions". You will evaluate all components of the system in a single pass.

## System Components to Evaluate:
1. Email Analyzer - Classifies and extracts information from customer emails
2. Order Processor - Handles order-related segments (if applicable)
3. Inquiry Responder - Addresses customer questions (if applicable)
4. Response Composer - Creates the final email response
5. End-to-End Performance - Overall system effectiveness

## Original Customer Email:
Subject: {email_subject}
Message: {email_message}

## Component 1: Email Analyzer Output
```json
{email_analysis}
```

## Component 2: Order Processor Output
Order processing applicable: {has_order_processing}
```json
{order_result}
```

## Component 3: Inquiry Responder Output
Inquiry response applicable: {has_inquiry_response}
```json
{inquiry_response}
```

## Component 4: Response Composer Output (Final Response)
Subject: {response_subject}
Body: {response_body}

## Evaluation Tasks

### Task 1: Evaluate Email Analyzer
- Email Analyzer Intent (0-10): Did the agent correctly identify the primary intent of the email?
- Email Analyzer Extraction (0-10): Did the agent extract all relevant entities and details?
- Email Analyzer Segmentation (0-10): Did the agent properly segment the email?
- Reasoning: [Explain your evaluation of the Email Analyzer]

### Task 2: Evaluate Order Processor (if applicable)
- Order Processor Identification (0-10): Did the agent correctly identify all ordered items?
- Order Processor Inventory (0-10): Did the agent correctly handle inventory checks?
- Order Processor Response (0-10): Did the agent provide appropriate order status info?
- Reasoning: [Explain your evaluation of the Order Processor]

### Task 3: Evaluate Inquiry Responder (if applicable)
- Inquiry Responder Questions (0-10): Did the agent correctly identify all customer questions?
- Inquiry Responder Accuracy (0-10): Are the answers factually correct based on available information?
- Inquiry Responder Completeness (0-10): Did the agent address all aspects of the questions?
- Reasoning: [Explain your evaluation of the Inquiry Responder]

### Task 4: Evaluate Response Composer
- Response Composer Tone (0-10): Is the tone suitable for the customer's situation?
- Response Composer Completeness (0-10): Does the response address all aspects of the customer's email?
- Response Composer Clarity (0-10): Is the response clear, well-structured, and professional?
- Response Composer CTA (0-10): Does it include appropriate next steps?
- Reasoning: [Explain your evaluation of the Response Composer]

### Task 5: Evaluate End-to-End Performance
- End-to-End Understanding (0-10): Did the system understand the customer's request and situation?
- End-to-End Accuracy (0-10): Is the response factually correct and appropriate?
- End-to-End Helpfulness (0-10): Does the response effectively help the customer?
- End-to-End Professionalism (0-10): Is the response professional with an appropriate tone?
- Reasoning: [Explain your evaluation of the overall system performance]

## Important Instructions:
1. Evaluate each component based solely on their specific responsibilities
2. For components marked as "not applicable", score them as NA
3. Provide detailed reasoning for each evaluation
4. Use the full 0-10 scale for nuanced scoring
5. Consider the context of a high-end fashion retailer when evaluating tone and content 