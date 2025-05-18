"""
Product deduplication utilities to identify and merge duplicate product mentions.
"""

from typing import Dict, List, Any, Set
from collections import defaultdict

from src.hermes.agents.email_analyzer.models import EmailAnalysis


def get_product_mention_stats(email_analysis: EmailAnalysis) -> Dict[str, int]:
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
    # Set to track unique product IDs
    unique_product_ids: Set[str] = set()

    # Count segments with products
    segments_with_products = 0
    total_mentions = 0

    # Process each segment
    for segment in email_analysis.segments:
        if segment.product_mentions and len(segment.product_mentions) > 0:
            segments_with_products += 1

            # Track product IDs from this segment
            for product in segment.product_mentions:
                if product.product_id:
                    unique_product_ids.add(product.product_id)
                total_mentions += 1

    return {
        "unique_products": len(unique_product_ids),
        "segments_with_products": segments_with_products,
        "total_mentions": total_mentions,
    }


def deduplicate_product_mentions(product_mentions: List[Any]) -> List[Any]:
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

    # Merge mentions for each product
    deduplicated_mentions = []
    for product_id, mentions in product_groups.items():
        if len(mentions) == 1:
            # If only one mention, keep it as is
            deduplicated_mentions.append(mentions[0])
        else:
            # TODO: Implement more sophisticated merging logic if needed
            # For now, just take the first mention as the representative
            deduplicated_mentions.append(mentions[0])

    return deduplicated_mentions
