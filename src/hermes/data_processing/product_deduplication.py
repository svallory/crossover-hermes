"""Product deduplication utilities to identify and merge duplicate product mentions."""

from collections import defaultdict
from typing import Any

async def deduplicate_product_mentions(product_mentions: list[Any]) -> list[Any]:
    """Deduplicates product mentions by merging mentions of the same product.

    DEPRECATED: This function will be moved to the Product Resolver agent as part of
    the responsibility for deduplicating and resolving product mentions.

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
    deduplicated_mentions = [mentions[0] for mentions in product_groups.values()]

    return deduplicated_mentions
