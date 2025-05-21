"""
Hermes Workflow Module

This module provides a LangGraph-based workflow for processing customer emails through
a sequence of agents:
1. Email Analyzer classifies and extracts information from emails
2. Order Processor handles order-related tasks
3. Inquiry Responder addresses customer inquiries
4. Response Composer creates the final response

The module exposes the main workflow and supporting functions for execution.
"""

from .graph import *
from .workflow import *
from .states import *
from .run_workflow import *
