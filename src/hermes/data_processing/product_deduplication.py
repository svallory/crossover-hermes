"""
Product deduplication utilities to identify and merge duplicate product mentions.
"""

from typing import Dict, List, Any, Set
from collections import defaultdict

from src.hermes.agents.email_analyzer.models import EmailAnalysis


async def get_product_mention_stats(email_analysis: EmailAnalysis) -> Dict[str, int]:
    """
    Analyzes product mentions from email analysis results to provide statistics.

    Args:
        email_analysis: An EmailAnalysisResult object containing segments with product mentions.

    Returns:
        A dictionary with statistics about product mentions:
        - unique_products: Number of unique products mentioned
        - segments_with_products: Number of segments containing product mentions
        - total_mentions: Total count of all product mentions across all segments
    """
    unique_product_ids: Set[str] = set()
    segments_with_products = 0
    total_mentions = 0

    for segment in email_analysis.segments:
        if segment.product_mentions and len(segment.product_mentions) > 0:
            segments_with_products += 1
            for product in segment.product_mentions:
                if product.product_id:
                    unique_product_ids.add(product.product_id)
                total_mentions += 1

    return {
        "unique_products": len(unique_product_ids),
        "segments_with_products": segments_with_products,
        "total_mentions": total_mentions,
    }


async def deduplicate_product_mentions(product_mentions: List[Any]) -> List[Any]:
    """
    Deduplicates product mentions by merging mentions of the same product.

    Args:
        product_mentions: List of ProductMention objects

    Returns:
        A deduplicated list of ProductMention objects
    """
    # Group by product_id
    product_groups = defaultdict(list)

    for mention in product_mentions:
        product_id = mention.product_id if mention.product_id else mention.product_name
        product_groups[product_id].append(mention)

    # Return deduplicated list
    deduplicated_mentions = []
    for mentions in product_groups.values():
        deduplicated_mentions.append(mentions[0])

    return deduplicated_mentions
