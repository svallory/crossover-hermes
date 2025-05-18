"""
Hermes Evaluation Tools package.

This package provides tools for running and evaluating the Hermes agent workflow.
It uses a single master evaluator to efficiently evaluate all components in one pass.
"""

from .utils import read_prompt, load_results_from_directory, save_report
from .workflow_runner import run_with_dataset
from .evaluators import evaluate_master

__all__ = [
    "read_prompt",
    "load_results_from_directory",
    "save_report",
    "run_with_dataset",
    "evaluate_master",
]
