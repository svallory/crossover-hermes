""" {cell}
## Email Classifier Agent

This module implements the Email Analyzer Agent for the Hermes system.
This agent is the first active component in the processing pipeline. Its primary
responsibilities are:

1.  **Email Classification**: Determines the main intent of the email, categorizing it
    as either a "product_inquiry" or an "order_request". This is a mandatory
    binary classification as per the assignment requirements.
2.  **Language Detection**: Identifies the language used in the email.
3.  **Tone Analysis**: Assesses the tone and formality of the customer's writing style.
4.  **Product Reference Extraction**: Identifies all mentions of products, whether by ID,
    name, or descriptive phrases. It attempts to normalize these references.
5.  **Customer Signal Detection**: Extracts signals based on the sales intelligence
    framework (e.g., purchase intent, customer context, emotional cues).

The agent uses a Large Language Model (LLM) guided by a specialized prompt
(from `src.prompts.email_classifier`) to perform these tasks and to output the
results in a structured format, specifically the `EmailAnalysis` Pydantic model.

**Workflow within the agent function/node**:
- Receives the raw email subject and body from the input state.
- Prepares the input for the LLM using the `email_analyzer_prompt`.
- Invokes the LLM to get the structured analysis.
- (Optionally) Verifies the structured output. If verification fails (e.g., Pydantic
  validation error or logical inconsistency detected by a separate check), it might
  trigger a correction step (e.g., re-prompting the LLM with error feedback).
- Updates the graph state with the `EmailAnalysis` object.
"""

from typing import List, Optional, Dict, Any, Union
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableConfig # For config propagation
from langchain_openai import ChatOpenAI # Example LLM
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
import json

# Assuming HermesState and HermesConfig are defined in src.state and src.config respectively
# from ..state import HermesState # Placeholder for actual import
# from ..config import HermesConfig # Placeholder for actual import
# from ..prompts.email_classifier import email_analyzer_prompt_simple as email_analyzer_prompt # Using the simple one for now

# --- Pydantic Models for Structured Output (as per reference-agent-flow.md) ---

class ProductReference(BaseModel):
    """A single product reference extracted from an email."""
    reference_text: str = Field(description="Original text from email referencing the product")
    reference_type: str = Field(description="Type: 'product_id', 'product_name', 'description', or 'category'")
    product_id: Optional[str] = Field(default=None, description="Extracted or inferred product ID if available (e.g., normalized from [CBT 89 01] to CBT8901)")
    product_name: Optional[str] = Field(default=None, description="Extracted or inferred product name if available")
    quantity: int = Field(default=1, description="Requested quantity, defaults to 1 if not specified.")
    confidence: float = Field(description="Confidence in the extraction/match (0.0-1.0)")
    excerpt: str = Field(description="The exact text phrase from the email that contains this reference.")

class CustomerSignal(BaseModel):
    """A customer signal detected in the email, based on the sales intelligence framework."""
    signal_type: str = Field(description="Type of customer signal detected (e.g., 'Direct Intent', 'Seasonal Need', 'Enthusiasm').")
    signal_category: str = Field(description="Category from sales intelligence framework (e.g., 'Purchase Intent', 'Customer Context', 'Emotion and Tone').")
    signal_text: str = Field(description="The specific text in the email that indicates this signal.")
    signal_strength: float = Field(description="Perceived strength or confidence in this signal (0.0-1.0).")
    excerpt: str = Field(description="The exact text phrase from the email that triggered this signal detection.")

class ToneAnalysis(BaseModel):
    """Analysis of the customer's tone and writing style."""
    tone: str = Field(description="Overall detected tone: e.g., 'formal', 'casual', 'urgent', 'friendly', 'frustrated', 'polite'.")
    formality_level: int = Field(description="Formality level from 1 (very casual) to 5 (very formal).")
    key_phrases: List[str] = Field(description="Key phrases from the email that informed the tone analysis.")

class EmailAnalysis(BaseModel):
    """Comprehensive structured analysis of a customer email."""
    classification: str = Field(description="Primary classification: Must be either 'product_inquiry' or 'order_request'.")
    classification_confidence: float = Field(description="Confidence in the classification (0.0-1.0).")
    classification_evidence: str = Field(description="Key text (excerpt) from the email that most strongly supports the classification choice.")
    language: str = Field(description="Detected language of the email (e.g., 'English', 'Spanish', 'French').")
    tone_analysis: ToneAnalysis = Field(description="Detailed analysis of the customer's tone and writing style.")
    product_references: List[ProductReference] = Field(default_factory=list, description="List of all detected product references.")
    customer_signals: List[CustomerSignal] = Field(default_factory=list, description="List of all detected customer signals.")
    reasoning: str = Field(description="Brief overall reasoning for the classification and key findings, especially if the email intent is mixed or subtle.")

# --- Agent Node Function ---

def verify_email_analysis_output(analysis_data: Dict[str, Any]) -> Union[EmailAnalysis, str]:
    """
    Verifies the raw dictionary output from LLM against the EmailAnalysis Pydantic model.
    This is a crucial step for ensuring data integrity before it's used by other agents.
    Returns the parsed EmailAnalysis object if valid, or an error string if not.
    (Placeholder - In a real implementation, this might involve more complex validation logic
     or even asking the LLM to correct its output if minor issues are found.)
    """
    try:
        # Forgiving parsing: Pydantic will raise validation errors if data is incorrect
        parsed_analysis = EmailAnalysis(**analysis_data)
        
        # Additional custom checks can be added here, e.g.:
        if not parsed_analysis.classification_evidence and parsed_analysis.classification_confidence > 0.5:
            # This is just an example of a custom rule
            # print("Warning: High classification confidence but no evidence provided.")
            pass 
        
        if not parsed_analysis.product_references and "order" in parsed_analysis.classification.lower() :
            # If it's an order, we expect some product references. This is a soft check.
            # print("Warning: Classified as order but no product references found in analysis.")
            pass

        return parsed_analysis
    except Exception as e: # Catches Pydantic ValidationError and other potential errors
        error_message = f"Email Analysis Verification Failed: {str(e)}. Raw data: {analysis_data}"
        print(error_message)
        return error_message

async def analyze_email_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    LangGraph node function for the Email Analyzer Agent.
    Takes the raw email from state, invokes an LLM with the email_analyzer_prompt,
    parses the structured EmailAnalysis output, and updates the state.
    """
    print("--- Calling Email Analyzer Agent Node ---")
    # hermes_config = HermesConfig.from_runnable_config(config.get("configurable", {}) if config else {})
    # For placeholder, create a default config if none passed
    # current_hermes_config = hermes_config if hermes_config else HermesConfig()
    
    # Assuming email_analyzer_prompt is imported
    # from ..prompts.email_classifier import email_analyzer_prompt_simple as email_analyzer_prompt
    # This would be set up when building the graph
    # llm = ChatOpenAI(model=current_hermes_config.llm_model_name, temperature=current_hermes_config.llm_temperature,
    #                  api_key=current_hermes_config.llm_api_key, base_url=current_hermes_config.llm_base_url)
    
    # output_parser = PydanticOutputParser(pydantic_object=EmailAnalysis)
    # chain = email_analyzer_prompt | llm | output_parser

    email_subject = state.get("email_subject", "")
    email_body = state.get("email_body", "")
    
    print(f"Analyzing email ID: {state.get('email_id')}")
    print(f"Subject: {email_subject}")
    # print(f"Body: {email_body[:200]}...") # Print only a snippet of body

    # Placeholder for LLM call and parsing
    # try:
    #     # analysis_result: EmailAnalysis = await chain.ainvoke({
    #     #     "subject": email_subject,
    #     #     "body": email_body,
    #     #     # "format_instructions": output_parser.get_format_instructions() # If prompt expects it
    #     # }, config=config)
    #     # print("LLM call successful, parsing output.")
    # except Exception as e:
    #     print(f"Error during Email Analyzer LLM call or parsing: {e}")
    #     # Fallback or error state update
    #     # For now, creating a mock error/fallback analysis
    #     error_analysis = EmailAnalysis(
    #         classification="error_processing",
    #         classification_confidence=0.0,
    #         classification_evidence=str(e),
    #         language="unknown",
    #         tone_analysis=ToneAnalysis(tone="unknown", formality_level=0, key_phrases=[]),
    #         product_references=[],
    #         customer_signals=[],
    #         reasoning=f"Failed to analyze email due to error: {e}"
    #     )
    #     return {"email_analysis": error_analysis.model_dump()}

    # --- MOCK IMPLEMENTATION --- 
    # This mock implementation simulates an LLM call based on keywords in the email.
    # Replace with actual chain.ainvoke call above.
    mock_analysis_data = {
        "classification": "product_inquiry",
        "classification_confidence": 0.85,
        "classification_evidence": "What era are they inspired by exactly?",
        "language": "English",
        "tone_analysis": {"tone": "inquisitive", "formality_level": 3, "key_phrases": ["what era", "exactly"]},
        "product_references": [],
        "customer_signals": [],
        "reasoning": "Customer is asking a direct question about product inspiration."
    }
    if "order" in email_body.lower() or "buy" in email_body.lower() or (email_subject and "order" in email_subject.lower()):
        mock_analysis_data["classification"] = "order_request"
        mock_analysis_data["classification_evidence"] = "I want to order" # generic
        mock_analysis_data["reasoning"] = "Email contains keywords like 'order' or 'buy' suggesting an order intent."
        if "LTH0976" in email_body:
            mock_analysis_data["product_references"] = [
                ProductReference(reference_text="LTH0976", reference_type="product_id", product_id="LTH0976", product_name="Leather Bifold Wallet", quantity=1, confidence=0.99, excerpt="LTH0976").model_dump()
            ]
    elif "hola" in email_body.lower():
        mock_analysis_data["language"] = "Spanish"
        mock_analysis_data["reasoning"] = "Email contains Spanish greeting."

    analysis_result = EmailAnalysis(**mock_analysis_data)
    # --- END MOCK IMPLEMENTATION ---

    print(f"Email Classification: {analysis_result.classification}")
    # print(f"Full Analysis: {analysis_result.model_dump_json(indent=2)}")
    
    # Verification step (placeholder)
    # verified_analysis = verify_email_analysis_output(analysis_result, llm, config) 
    # The verify_email_analysis_output function might re-invoke an LLM if critical errors are found.
    # For now, we assume the initial output is used.
    
    return {"email_analysis": analysis_result.model_dump()} # Return as dict for state update

# Placeholder for verification function mentioned in reference-agent-flow.md
# async def verify_email_analysis_output(analysis: EmailAnalysis, llm: ChatOpenAI, config: RunnableConfig) -> EmailAnalysis:
#     errors = []
#     if analysis.classification not in ["product_inquiry", "order_request"]:
#         errors.append(f"Invalid classification: {analysis.classification}. Must be 'product_inquiry' or 'order_request'.")
#     # Add more validation rules here for other fields (e.g., confidence ranges, required excerpts)
#     if errors:
#         print(f"EmailAnalysis verification errors: {errors}")
#         # Potentially re-prompt LLM to fix: 
#         # fix_prompt = ... 
#         # fixed_analysis_json = await llm.ainvoke(fix_prompt, config=config)
#         # return EmailAnalysis.parse_raw(fixed_analysis_json.content) 
#         # For now, just return original if verification fails in this placeholder
#         return analysis 
#     return analysis

""" {cell}
### Agent Implementation Notes:

- **Pydantic Models**: The file starts by defining the Pydantic models (`ProductReference`, `CustomerSignal`, `ToneAnalysis`, `EmailAnalysis`) that represent the structured output this agent is expected to produce. These definitions should align with `reference-agent-flow.md`.
- **Agent Node Function (`analyze_email_node`)**:
    - This asynchronous function is designed to be a node in a LangGraph graph.
    - It takes the current `state` (a dictionary) and an optional `RunnableConfig`.
    - **LLM and Chain Initialization (Commented Out)**: The commented-out lines show how an `ChatOpenAI` LLM would be initialized using `HermesConfig` parameters and how it would be chained with the `email_analyzer_prompt` and a `PydanticOutputParser`.
    - **Input**: It retrieves `email_subject` and `email_body` from the state.
    - **LLM Invocation (Commented Out)**: The `chain.ainvoke(...)` call is where the actual LLM interaction would occur. Error handling (e.g., for LLM API errors or parsing failures) is important here.
    - **Mock Implementation**: Currently, a mock implementation simulates the LLM's output based on simple keyword checks. **This mock section must be replaced with the actual LLM chain invocation.**
    - **Output**: The function returns a dictionary `{"email_analysis": analysis_result.model_dump()}`. LangGraph uses this dictionary to update the corresponding fields in the `HermesState`.
- **Configuration (`HermesConfig`)**: The agent node would typically get its configuration (like LLM model name, API keys) via the `RunnableConfig` object passed by LangGraph. The `HermesConfig.from_runnable_config()` method (defined in `src/config.py`) would be used for this.
- **Verification (Placeholder)**: The `reference-agent-flow.md` mentions a verification step. A placeholder for `verify_email_analysis_output` is included. This step is crucial for ensuring the LLM output is reliable. It could involve Pydantic's built-in validation, custom validation rules, or even another LLM call to review and correct the output if necessary.
- **Imports**: Placeholder comments indicate where actual imports from other project modules (`state`, `config`, `prompts`) would go.

To make this agent functional, the mock implementation needs to be replaced by the actual LangChain expression language (LCEL) chain execution, and the dependencies (LLM, prompt, config) need to be correctly initialized and passed.
""" 