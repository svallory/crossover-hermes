"""Hermes - AI-powered email processing system for customer service automation."""

from .config import *
from .model.enums import *
from .model.errors import *
from .core import run_email_processing, process_emails

__version__ = "0.1.0"

__all__ = [
    "run_email_processing",
    "process_emails",
]
