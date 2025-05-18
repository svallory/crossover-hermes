"""
Main function for analyzing customer emails.
"""

from typing import Optional, cast
from langsmith import traceable
from langchain_core.runnables import RunnableConfig

from .models import (
    EmailAnalysis,
    EmailAnalyzerInput,
    EmailAnalyzerOutput,
)
from .prompts import get_prompt
from ...config import HermesConfig
from ...utils.llm_client import get_llm_client
from ...data_processing.product_deduplication import get_product_mention_stats


@traceable(
    name="Email Analyzer Agent",
    description="Analyze an email to determine its intent, extract product references, and identify customer signals.",
)  # type: ignore
async def analyze_email(
    state: EmailAnalyzerInput, runnable_config: RunnableConfig
) -> EmailAnalyzerOutput:
    """
    Analyzes a customer email to extract structured information about intent, product references, and customer signals.

    Args:
        state (EmailAnalyzerInput): The input model containing email_id, subject, and message.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'], HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        EmailAnalyzerOutput: The output model containing the initial analysis and unique products.
    """
    hermes_config = HermesConfig.from_runnable_config(runnable_config)

    print(f"Analyzing email {state.email_id} - Subject: '{state.subject[:50] if state.subject else 'No subject'}...'")

    # Use a weak model for initial analysis since it's a relatively simple task
    llm = get_llm_client(config=hermes_config, model_strength="weak", temperature=0.0)

    analyzer_prompt = get_prompt("email_analyzer")
    analysis_chain = analyzer_prompt | llm.with_structured_output(EmailAnalysis)

    try:
        email_analysis = cast(
            EmailAnalysis, await analysis_chain.ainvoke(state.model_dump())
        )

        # Collect all product mentions from all segments
        all_products = []
        for segment in email_analysis.segments:
            all_products.extend(segment.product_mentions)

        # Get stats about product mentions
        product_stats = get_product_mention_stats(email_analysis)
        print(
            f"  Analysis for {state.email_id} complete. Found {product_stats['unique_products']} unique products across {product_stats['segments_with_products']} segments."
        )
        
        # Return without verification but with all products
        return EmailAnalyzerOutput(
            email_analysis=email_analysis, unique_products=all_products
        )

    except Exception as e:
        print(f"Error analyzing email {state.email_id}: {e}")
        fallback_analysis = EmailAnalysis(
            language="unknown",
            primary_intent="product inquiry",
            customer_pii={},
            segments=[],
        )

        # Return without verification in case of error
        return EmailAnalyzerOutput(email_analysis=fallback_analysis, unique_products=[])
