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

from .states import OverallState, merge_errors
from .graph import workflow, graph_builder
from .run_workflow import run_workflow

__all__ = [
    "workflow",
    "graph_builder",
    "run_workflow",
    "OverallState",
    "merge_errors",
]
