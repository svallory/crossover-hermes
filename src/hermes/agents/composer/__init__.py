"""
Response Composer Agent package.

This agent creates the final customer response by combining outputs from the
Email Analyzer, Inquiry Responder, and Order Processor agents.
"""

from .compose_response import compose_response
from .models import (
    ResponseTone,
    ResponsePoint,
    ComposedResponse,
    ResponseComposerInput,
    ResponseComposerOutput,
)

__all__ = [
    "compose_response",
    "ResponseTone",
    "ResponsePoint",
    "ComposedResponse",
    "ResponseComposerInput",
    "ResponseComposerOutput",
]
