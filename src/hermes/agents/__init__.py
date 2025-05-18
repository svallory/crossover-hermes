"""
Agents for the Hermes system.

This package contains agent implementations for various email processing tasks.
"""

# Legacy agent (will be removed)
from .email_analyzer import analyze_email, EmailAnalyzerInput, EmailAnalyzerOutput
from .inquiry_responder import (
    respond_to_inquiry,
    InquiryResponderInput,
    InquiryResponderOutput,
)
from .order_processor import (
    process_order,
    OrderProcessorInput,
    OrderProcessorOutput,
    OrderedItem,
    ProcessedOrder,
)
from .response_composer import (
    compose_response,
    ResponseComposerInput,
    ResponseComposerOutput,
)

__all__ = [
    # Email Analyzer
    "analyze_email",
    "EmailAnalyzerOutput",
    "EmailAnalyzerInput",
    # Inquiry Responder
    "respond_to_inquiry",
    "InquiryResponderInput",
    "InquiryResponderOutput",
    # Order Processor
    "process_order",
    "OrderProcessorInput",
    "OrderProcessorOutput",
    # Response Composer
    "compose_response",
    "ResponseComposerInput",
    "ResponseComposerOutput",
]
