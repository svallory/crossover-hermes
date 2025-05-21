# Email Analyzer Agent

The Email Analyzer Agent processes customer emails to extract structured information, outputting an `EmailAnalysisResult` object.

## Structure

The agent (`src/hermes/agents/email_analyzer/`) is organized as follows:

- `__init__.py`: Exports the main functions and models.
- `models.py`: Defines Pydantic models (`EmailAnalysisResult`, `Segment`, `ProductMention`, etc.).
- `prompts.py`: Contains LangChain prompt templates for analysis, with prompt strings embedded directly.
- `analyze_email.py`: Houses the main `analyze_email` function using the weak model.

## Agent Flow

1.  The `analyze_email` function is called with email data.
2.  It uses the `email_analyzer` prompt (from `prompts.py`) and a **weak** LLM to perform an initial analysis, attempting to structure the output according to the `EmailAnalysisResult` model (from `models.py`).
3.  The final `EmailAnalyzerOutput` object (containing the initial analysis and unique products) is returned.

## Configuration

This agent respects the following settings from `HermesConfig`:

- `llm_provider`: "OpenAI" or "Gemini".
- `llm_weak_model_name`: For initial analysis.

Refer to `docs/env-sample.md` for detailed environment variable configuration.

## Prompts

The agent uses one main prompt defined in `prompts.py`:

1.  `email_analyzer`: For the initial analysis step, designed to output the `EmailAnalysisResult` structure.

## Models

The primary Pydantic models used are defined in `models.py`:

- `EmailAnalysisResult`: The main output structure, including language, intent, PII, and segments.
- `Segment`: Represents a distinct part of the email, with type, sentences, and product mentions.
- `ProductMention`: Details about a product mentioned in a segment.
- `EmailAnalyzerInput`: Input model for the email analyzer.
- `EmailAnalyzerOutput`: The overall output model containing the initial analysis and unique products.

## Usage Example

~~~python
from hermes.config import HermesConfig
from hermes.agents.email_analyzer import analyze_email, EmailAnalysis, EmailAnalyzerOutput

# Initialize HermesConfig (ensure your .env or environment variables are set)
hermes_config = HermesConfig()

# Example state dictionary matching what the LangGraph workflow might provide
email_state = {
    "email_id": "test_001",
    "subject": "Question about my order and a new jacket",
    "message": "Hi, I placed an order #12345 for the Sunset Breeze t-shirt (SKU: TSH7890) yesterday. Can you confirm if it shipped? Also, I saw the new Urban Nomad jacket (JKT1234) online. What colors does it come in? Thanks, Jane Doe."
}

# Runnable config for the agent node
run_config = {
    "configurable": {
        "hermes_config": hermes_config
    }
}

async def main():
    output: EmailAnalyzerOutput = await analyze_email(email_state, runnable_config=run_config)
    
    analysis_result = output.email_analysis
    print("--- Initial Email Analysis ---")
    print(f"Language: {analysis_result.language}")
    print(f"Primary Intent: {analysis_result.primary_intent}")
    if analysis_result.customer_pii:
        print(f"Customer PII: {analysis_result.customer_pii}")
    
    for i, segment in enumerate(analysis_result.segments):
        print(f"\nSegment {i+1}: {segment.segment_type.value}")
        print(f"  Main Sentence: {segment.main_sentence}")
        if segment.product_mentions:
            print("  Product Mentions:")
            for mention in segment.product_mentions:
                print(f"    - Name: {mention.product_name}, ID: {mention.product_id}, Qty: {mention.quantity}")
    
    # Show unique products
    if output.unique_products:
        print("\n--- Unique Products ---")
        for product in output.unique_products:
            print(f"  - Name: {product.product_name}, ID: {product.product_id}, Qty: {product.quantity}")

# If running in a Jupyter notebook or a script that can run asyncio
# import asyncio
# asyncio.run(main()) 
~~~ 