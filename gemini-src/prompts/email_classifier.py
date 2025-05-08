""" {cell}
### Prompts for the Email Analyzer Agent

This module contains the LangChain `ChatPromptTemplate` designed for the `Email Analyzer Agent`. The primary goal of this agent is to comprehensively analyze an incoming customer email and extract structured information.

**The prompt guides the LLM to perform several tasks:**

1.  **Primary Classification**: Classify the email as either "product_inquiry" or "order_request" based on its dominant intent. This is a binary classification as per the assignment output requirements for the `email-classification` sheet.
2.  **Language Detection**: Identify the language of the email.
3.  **Tone Analysis**: Analyze the customer's tone and writing style (e.g., formal, casual, urgent) and formality level.
4.  **Product Reference Extraction**: Identify all mentions of products, whether by ID, name, or vague descriptions. For each reference, extract details like quantity and the original text excerpt.
5.  **Customer Signal Detection**: Identify various customer signals based on the detailed `customer-signal-processing.md` guide. This includes purchase intent, customer context, emotional signals, etc., along with supporting text excerpts.
6.  **Reasoning**: Provide a brief justification for the primary classification.
7.  **Structured Output**: The LLM is instructed to return its analysis in a JSON format that can be parsed into the `EmailAnalysis` Pydantic model (as defined in `reference-agent-flow.md` and later in `src/agents/email_classifier.py`).

Few-shot examples are embedded within the system prompt to guide the LLM, especially for handling nuanced cases like mixed intents (though the primary classification must remain binary), different languages, and varying product reference styles.
"""

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

# This system message is detailed and provides context, instructions, and few-shot examples.
EMAIL_ANALYZER_SYSTEM_MESSAGE_CONTENT = """
You are an expert email analysis system for "Hermes", a high-end fashion retail company. Your task is to meticulously analyze customer emails and extract structured information.

**Output Format:**
Provide your analysis as a JSON object that strictly adheres to the following Pydantic model structure:

```json
{{
  "classification": "(must be 'product_inquiry' or 'order_request')",
  "classification_confidence": {{float, 0.0-1.0}},
  "classification_evidence": "(key text snippet from email supporting the classification)",
  "language": "(detected language code, e.g., 'en', 'es')",
  "tone_analysis": {{
    "tone": "(e.g., 'formal', 'casual', 'urgent', 'enthusiastic', 'neutral')",
    "formality_level": {{int, 1-5 where 1 is very casual, 5 is very formal}},
    "key_phrases": ["(list of phrases indicative of tone)"]
  }},
  "product_references": [
    {{
      "reference_text": "(original text from email, e.g., 'LTH0976 Leather Bifold Wallet', 'that popular item')",
      "reference_type": "(must be 'product_id', 'product_name', 'description', or 'category')",
      "product_id": "(extracted or inferred product ID, if available, e.g., 'LTH0976', can be null)",
      "product_name": "(extracted or inferred product name, if available, e.g., 'Leather Bifold Wallet', can be null)",
      "quantity": {{int, default 1}},
      "confidence": {{float, 0.0-1.0, confidence in this specific product reference extraction/match}},
      "excerpt": "(the exact text snippet from the email containing this reference)"
    }}
  ],
  "customer_signals": [
    {{
      "signal_type": "(type of signal, e.g., 'Direct Intent', 'Browsing Intent', 'Gift Purchase', 'Enthusiasm')",
      "signal_category": "(category from sales intelligence framework, e.g., 'Purchase Intent', 'Customer Context', 'Emotion and Tone')",
      "signal_text": "(the text from the email that indicates this signal)",
      "signal_strength": {{float, 0.0-1.0}},
      "excerpt": "(the exact text snippet from the email that triggered this signal)"
    }}
  ],
  "reasoning": "(brief reasoning for the primary classification choice, especially if the email has mixed elements)"
}}
```

**Primary Classification Rules:**
- If the email primarily aims to ask questions about products, features, availability (without committing to a purchase), or general information, classify it as "product_inquiry".
- If the email primarily expresses an intent to purchase specific items, requests an order to be placed, or confirms items for an order, classify it as "order_request".
- Even if an email contains elements of both (e.g., an order request that also asks a question), you MUST choose ONE primary classification based on the dominant intent. Use the 'reasoning' field to explain if mixed elements are present.

**Product Reference Extraction:**
- Capture all mentions of products, including specific product IDs (e.g., "RSG8901", "LTH0976"), full or partial product names (e.g., "Sleek Wallet", "Infinity Scarf"), formatted variations (e.g., "CBT 89 01", "[RSG-8901]"), and vague descriptions (e.g., "a dress for a summer wedding", "that popular item you sell").
- For vague descriptions, set `reference_type` to 'description'. Try to infer `product_name` or `product_id` if context allows, otherwise they can be null.
- Default `quantity` to 1 if not specified.

**Customer Signal Detection:**
- Refer to the Hermes Sales Intelligence Framework for `signal_type` and `signal_category`.
- Examples of signals to detect include:
  - Purchase Intent: Direct Intent ("I want to order"), Browsing Intent ("thinking about"), Price Inquiry.
  - Customer Context: Business Use, Gift Purchase, Seasonal Need, Upcoming Event, Past Purchase.
  - Communication Style: Formal, Casual, Detailed, Concise.
  - Emotion and Tone: Enthusiasm, Uncertainty, Frustration, Urgency.
  - Upsell/Cross-sell Opportunities: Celebration Mention, Collection Building.
  - Objections: Price Concern, Quality Concern.
- For each signal, provide the `excerpt` from the email.

**Example Scenarios & Expected Behavior:**

1.  **Clear Order Email (English):**
    *   Subject: Order for Wallet
    *   Body: "Hello, I would like to order 1 LTH0976 Leather Bifold Wallet. My shipping address is 123 Main St. Thanks, John."
    *   Expected Classification: "order_request"
    *   Product Reference: one entry for "LTH0976 Leather Bifold Wallet", type 'product_id' (or 'product_name' if ID also extracted), quantity 1.
    *   Customer Signals: 'Direct Intent'.

2.  **Clear Inquiry Email (English):**
    *   Subject: Question about Cozy Shawl
    *   Body: "Hi, for the CSH1098 Cozy Shawl, is the material suitable for very cold weather? What colors does it come in?"
    *   Expected Classification: "product_inquiry"
    *   Product Reference: one entry for "CSH1098 Cozy Shawl", type 'product_id' (or 'product_name').
    *   Customer Signals: 'Specific Feature Question'.

3.  **Mixed Intent (Order Dominant):**
    *   Subject: Urgent Order + Quick Question
    *   Body: "Hi, please process an order for 2 Classic T-Shirts (P001) in size M. Also, do you have them in blue?"
    *   Expected Classification: "order_request"
    *   Reasoning: "Primary intent is to place an order for T-Shirts, with a secondary product inquiry about color availability."
    *   Product Reference: for "Classic T-Shirts (P001)", quantity 2.
    *   Customer Signals: 'Direct Intent', 'Urgency', 'Specific Feature Question'.

4.  **Vague Product Reference Inquiry (English):**
    *   Subject: Looking for a gift
    *   Body: "I need a nice gift for my mother. She likes scarves, something warm for winter. What do you suggest?"
    *   Expected Classification: "product_inquiry"
    *   Product Reference: one for "scarves", type 'category'; one for "something warm for winter", type 'description'.
    *   Customer Signals: 'Gift Purchase', 'Seasonal Need'.

5.  **Non-English Email (Spanish Inquiry):**
    *   Subject: Pregunta
    *   Body: "Hola, ¿el bolso VBT2345 está disponible en color rojo? Gracias."
    *   Expected Classification: "product_inquiry"
    *   Language: "es"
    *   Product Reference: for "bolso VBT2345", type 'product_name' (or 'product_id' if ID also extracted).

Analyze the email provided by the user thoroughly and generate the JSON output as specified.
Ensure all fields in the JSON output are populated correctly. `product_id` and `product_name` in `product_references` can be null if not directly extractable/inferable.
`classification_confidence` and `product_references[*].confidence`, `customer_signals[*].signal_strength` should be your estimated float values between 0.0 and 1.0.
"""

EMAIL_ANALYZER_HUMAN_MESSAGE_TEMPLATE_CONTENT = """
Analyze the following customer email and provide the output in the specified JSON format.

**Email Subject:**
```
{subject}
```

**Email Body:**
```
{body}
```

Ensure your entire response is ONLY the JSON object, without any preceding or succeeding text, comments, or explanations outside the JSON structure itself.
"""

email_analyzer_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(EMAIL_ANALYZER_SYSTEM_MESSAGE_CONTENT),
    HumanMessagePromptTemplate.from_template(EMAIL_ANALYZER_HUMAN_MESSAGE_TEMPLATE_CONTENT)
])

""" {cell}
### Using the Email Analyzer Prompt

This `email_analyzer_prompt` can be used with an LLM (e.g., via `llm.invoke()` or as part of a LangChain chain, potentially a `create_structured_output_chain` if the LLM supports function calling for the Pydantic model).

**Example Invocation (Conceptual):**

```python
# from langchain_openai import ChatOpenAI
# from src.config import HermesConfig # Assuming config is set up
# from src.prompts.email_classifier import email_analyzer_prompt

# # Load configuration
# config = HermesConfig()

# # Initialize LLM
# llm = ChatOpenAI(
#     model_name=config.llm.model_name,
#     temperature=config.llm.temperature,
#     openai_api_key=config.llm.api_key,
#     base_url=config.llm.base_url
# )

# # Example email data
# email_subject = "Order and a Question"
# email_body = "Hi, I'd like to order the LTH0976 wallet. Also, is it available in black? Thanks!"

# # Invoke the prompt with the LLM
# # For structured output, you'd ideally use a chain that parses to the Pydantic model.
# # For raw JSON string output from a model not fine-tuned for JSON mode:
# formatted_prompt = email_analyzer_prompt.format_prompt(
#     subject=email_subject,
#     body=email_body
# )
# response = llm.invoke(formatted_prompt)
# print(response.content) # This would be the JSON string

# # Ideally, parse this JSON string into the EmailAnalysis Pydantic model.
# # import json
# # from src.agents.email_classifier import EmailAnalysis # Assuming Pydantic model is defined
# # try:
# #     parsed_output = EmailAnalysis(**json.loads(response.content))
# #     print("Successfully parsed:", parsed_output.classification)
# # except Exception as e:
# #     print("Error parsing LLM output:", e)
```

The prompt is designed to be robust for various email types, guiding the LLM to provide a comprehensive and structured analysis critical for the subsequent agents in the Hermes pipeline.
""" 