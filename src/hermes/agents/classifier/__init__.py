"""
Email Analyzer Agent package.

This agent analyzes customer emails to extract structured information about
intent, product references, and customer signals.
"""

from .agent import analyze_email
from .models import (
    ProductCategory,
    SegmentType,
    ProductMention,
    Segment,
    EmailAnalysis,
    EmailAnalyzerInput,
    EmailAnalyzerOutput,
)

__all__ = [
    "agent",
    "ProductCategory",
    "SegmentType",
    "ProductMention",
    "Segment",
    "EmailAnalysis",
    "EmailAnalyzerInput",
    "EmailAnalyzerOutput",
]
