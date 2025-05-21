"""
Product resolver package for resolving product mentions to catalog products.
"""

from src.hermes.agents.product_resolver.models import ResolvedProductsOutput
from src.hermes.agents.product_resolver.resolve_products import resolve_product_mentions

__all__ = [
    "ResolvedProductsOutput",
    "resolve_product_mentions",
] 