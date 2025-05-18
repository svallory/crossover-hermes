"""
Email Analyzer Agent package.

This agent analyzes customer emails to extract structured information about
intent, product references, and customer signals.
"""

from .analyze_email import analyze_email
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
    "analyze_email",
    "ProductCategory",
    "SegmentType",
    "ProductMention",
    "Segment",
    "EmailAnalysis",
    "EmailAnalyzerInput",
    "EmailAnalyzerOutput",
]
