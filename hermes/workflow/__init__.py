"""Hermes Workflow Module.

This module provides a LangGraph-based workflow for processing customer emails through
a sequence of agents:
1. Classifier agent classifies and extracts information from emails
2. Fulfiller agent handles order-related tasks
3. Advisor agent addresses customer inquiries
4. Composer agent creates the final response

The module exposes the main workflow and supporting functions for execution.
"""

from .states import *
from .run import *
