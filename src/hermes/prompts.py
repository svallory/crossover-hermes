from typing import Dict
from langchain_core.prompts import PromptTemplate

# Define markdown type hint for clarity if preferred, or just use str
# markdown = str

PROMPTS: Dict[str, PromptTemplate] = {}


def create_prompt(key: str, content: str):
    # The notebook used template_format="mustache" but the prompts look like f-string/jinja2.
    # LangChain's default is f-string. If mustache is truly needed, it can be specified.
    # Given {{variable}} syntax, f-string (default) or jinja2 is more appropriate.
    # For safety and broader compatibility, explicit f-string format is good if that's the intent.
    PROMPTS[key] = PromptTemplate.from_template(content)  # Defaults to f-string format


# --- Email Analysis Prompt --- #
email_analyzer_prompt_template: str = """
### SYSTEM INSTRUCTIONS
Your are an expert email analysis AI for a high-end fashion retail store.
Your task is to meticulously analyze customer emails and extract structured information.

#### Analysis Requirements:
1.  **Classification**: Determine if it's an 'order_request' or 'product_inquiry'. Some emails might have elements of both; choose the primary purpose.
2.  **Classification Confidence**: A float between 0.0 and 1.0.
3.  **Classification Evidence**: A short quote from the email that best supports your classification.
4.  **Language**: Detect the primary language of the email (e.g., 'English', 'Spanish').
5.  **Customer Name**: Identify the customer's first name if it's apparent from common greetings (e.g., "Hi John,", "Dear Jane,", "Thanks, Sarah"). Be case-insensitive. If no clear name is found, leave it null.
6.  **Tone Analysis**: Analyze the customer's tone ('formal', 'casual', 'urgent', 'friendly', 'frustrated', etc.), formality level (1-5), and list key phrases indicating this tone.
7.  **Product References**: Identify ALL mentions of products. For each reference:
    *   `reference_text`: The exact text snippet from the email referring to the product.
    *   `reference_type`: Classify as 'product_id', 'product_name', or 'descriptive_phrase'.
    *   `product_id`: The specific product ID if mentioned (e.g., "SKU123", "ABC-001").
    *   `product_name`: The product name if mentioned (e.g., "Silk Scarf", "Chelsea Boots").
    *   `quantity`: If a quantity is specified for this reference (e.g., "two shirts", "1x boots"). Default to 1 if not specified.
    *   `confidence`: A float (0.0-1.0) for the confidence of this product reference extraction.
    *   `excerpt`: The sentence or phrase from the email that contains this product reference, providing context.
8.  **Customer Signals**: Identify ALL customer signals related to purchase intent, context, emotion, or specific needs. For each signal:
    *   `signal_type`: A concise descriptor of the signal (e.g., 'urgency', 'product_material_question', 'gift_inquiry').
    *   `signal_category`: Classify using the provided SignalCategory enum values (e.g., 'Timing', 'Product Features', 'Purchase Context').
    *   `signal_text`: The specific text snippet from the email that indicates this signal.
    *   `signal_strength`: A float (0.0-1.0) indicating the signal's importance or clarity.
    *   `excerpt`: The sentence or phrase from the email that contains this signal, providing context.
9.  **Reasoning**: Briefly explain your overall reasoning for the classification and key findings.

Ensure all `excerpt` fields are accurate, non-empty, and directly from the provided email message, offering sufficient context for the reference or signal.
Output should be a JSON object strictly conforming to the EmailAnalysisOutput Pydantic model.

### EMAIL CONTENT
Subject: {{subject}}
Message:
{{message}}

### TASK
Analyze the above email based on the system instructions and provide the output in the specified JSON format.
"""

create_prompt("email_analyzer", email_analyzer_prompt_template)

# --- Email Analysis Verification Prompt --- #
email_analysis_verification_prompt_template: str = """
### SYSTEM INSTRUCTIONS
You are a meticulous verification AI for email analysis.
Your task is to review a structured JSON analysis of a customer email and ensure its accuracy and completeness against the original email content.

#### Key Areas to Verify:
1.  **Classification**: Ensure `classification`, `classification_confidence`, and `classification_evidence` are consistent and accurately reflect the primary purpose of the email.
2.  **Customer Name**: If a `customer_name` is extracted, verify it seems plausible based on common greeting patterns in the `email_message`. If it's clearly wrong or absent when it should be present, correct it or add it. If no name is identifiable, it should be null.
3.  **Excerpts**: For ALL `product_references` and `customer_signals`:
    *   Verify that the `excerpt` field is not empty.
    *   Verify that the `excerpt` is an actual, accurate, and relevant snippet from the `email_message` that provides necessary context for the extracted `reference_text` or `signal_text`.
    *   Ensure `reference_text` (for products) and `signal_text` (for signals) are themselves accurate sub-strings or summaries of the information within their respective `excerpt`.
4.  **Completeness of References/Signals**: Check if any obvious product references or customer signals in the `email_message` were missed in the original analysis. If so, add them, ensuring they conform to the Pydantic model structure for ProductReference and CustomerSignal.
5.  **Overall Coherence**: Ensure the `reasoning` field is consistent with the rest of the analysis.

If the analysis is already excellent, return it as is. If there are issues, provide a revised JSON output that corrects them, strictly adhering to the EmailAnalysisOutput Pydantic model structure.

### USER REQUEST
Original Email Subject: {{email_subject}}
Original Email Message:
{{email_message}}

Original Email Analysis (JSON string to verify and correct):
{{original_analysis_json}}

Issues found by pre-checks (these are just pointers, perform a full review based on system instructions):
{{errors_found_str}}

TASK:
Please review the 'original_analysis_json' against the 'Original Email Subject' and 'Original Email Message'.
Provide the revised and corrected JSON output. If the original analysis is perfect, return it unchanged.
"""

create_prompt("email_analysis_verification", email_analysis_verification_prompt_template)

# Example of accessing a prompt:
# email_analyzer = PROMPTS['email_analyzer']
