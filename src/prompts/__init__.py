"""
Prompt templates for the Hermes AI agents.

This package contains prompt templates used by the system's agents to process customer emails,
orders, inquiries, and generate responses.
"""

from src.prompts.utils import read_prompt_md
from src.prompts.analyzer import (
    email_analyzer_md,
    email_analysis_verification_md
)
from src.prompts.inquiry_responder import (
    inquiry_responder_md,
    answer_question_md,
    inquiry_response_verification_md
)
from src.prompts.order_processor import (
    order_processor_md,
    order_processing_verification_md
)
from src.prompts.response_composer import (
    response_composer_md,
    response_quality_verification_md
)

__all__ = [
    "read_prompt_md",
    
    # Analyzer
    "email_analyzer_md",
    "email_analysis_verification_md",
    
    # Inquiry Responder
    "inquiry_responder_md",
    "answer_question_md",
    "inquiry_response_verification_md",
    
    # Order Processor
    "order_processor_md",
    "order_processing_verification_md",
    
    # Response Composer
    "response_composer_md",
    "response_quality_verification_md",
] 