"""
Inquiry Responder Agent package.

This agent handles customer inquiries about products, answering questions
and suggesting related products using RAG techniques.
"""

from .agent import respond_to_inquiry
from .models import (
    ExtractedQuestion,
    QuestionAnswer,
    ProductInformation,
    InquiryAnswers,
    InquiryResponderInput,
    InquiryResponderOutput,
)

__all__ = [
    "agent",
    "ExtractedQuestion",
    "QuestionAnswer",
    "ProductInformation",
    "InquiryAnswers",
    "InquiryResponderInput",
    "InquiryResponderOutput",
]
