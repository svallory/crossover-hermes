#!/usr/bin/env python
"""
Utility functions for Hermes evaluation tools.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Define paths
EVALUATE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = EVALUATE_DIR / "prompts"
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(EVALUATE_DIR)))


def read_prompt(prompt_name: str) -> str:
    """
    Read a prompt from a markdown file.

    Args:
        prompt_name: Name of the prompt file (without .md extension)

    Returns:
        The prompt text
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r") as f:
        # Skip the first line (title) and return the rest
        lines = f.readlines()
        return "".join(lines[2:]) if len(lines) > 2 else "".join(lines)


# YAML handling with custom tags
def custom_tag_constructor(loader, tag, node):
    """Handle custom YAML tags by returning appropriate Python structures."""
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


class SafeLoader(yaml.SafeLoader):
    """Custom YAML loader that handles custom Python object tags."""

    pass


# Register constructor for all Python object tags
yaml.add_multi_constructor("tag:yaml.org,2002:python/object", custom_tag_constructor, Loader=SafeLoader)
yaml.add_multi_constructor("tag:yaml.org,2002:python/object/apply", custom_tag_constructor, Loader=SafeLoader)
yaml.add_multi_constructor("tag:yaml.org,2002:python/object/new", custom_tag_constructor, Loader=SafeLoader)


def format_evaluation_scores(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format evaluation scores for LangSmith upload.

    Args:
        report: Evaluation report containing scores

    Returns:
        List of formatted scores for LangSmith
    """
    summary_scores = []

    # Extract scores from the report
    if "scores" not in report:
        return summary_scores

    scores = report.get("scores", {})

    # Format email analyzer scores
    if "email_analyzer" in scores and scores["email_analyzer"]:
        analyzer_scores = scores["email_analyzer"]
        avg_accuracy = (
            sum(s.get("accuracy", 0) for s in analyzer_scores) / len(analyzer_scores) if analyzer_scores else 0
        )
        summary_scores.append(
            {
                "key": "email_analyzer_accuracy",
                "score": round(avg_accuracy, 2),
                "comment": "Average accuracy score for email analysis",
            }
        )

    # Format order processor scores
    if "order_processor" in scores and scores["order_processor"]:
        processor_scores = scores["order_processor"]
        avg_accuracy = (
            sum(s.get("accuracy", 0) for s in processor_scores) / len(processor_scores) if processor_scores else 0
        )
        summary_scores.append(
            {
                "key": "order_processor_accuracy",
                "score": round(avg_accuracy, 2),
                "comment": "Average accuracy score for order processing",
            }
        )

    # Format inquiry responder scores
    if "inquiry_responder" in scores and scores["inquiry_responder"]:
        responder_scores = scores["inquiry_responder"]
        avg_accuracy = (
            sum(s.get("accuracy", 0) for s in responder_scores) / len(responder_scores) if responder_scores else 0
        )
        summary_scores.append(
            {
                "key": "inquiry_responder_accuracy",
                "score": round(avg_accuracy, 2),
                "comment": "Average accuracy score for inquiry responses",
            }
        )

    # Format response composer scores
    if "response_composer" in scores and scores["response_composer"]:
        composer_scores = scores["response_composer"]
        avg_quality = sum(s.get("quality", 0) for s in composer_scores) / len(composer_scores) if composer_scores else 0
        summary_scores.append(
            {
                "key": "response_composer_quality",
                "score": round(avg_quality, 2),
                "comment": "Average quality score for composed responses",
            }
        )

    # Format end-to-end scores
    if "end_to_end" in scores and scores["end_to_end"]:
        e2e_scores = scores["end_to_end"]
        avg_quality = sum(s.get("quality", 0) for s in e2e_scores) / len(e2e_scores) if e2e_scores else 0
        avg_correctness = sum(s.get("correctness", 0) for s in e2e_scores) / len(e2e_scores) if e2e_scores else 0

        summary_scores.append(
            {
                "key": "end_to_end_quality",
                "score": round(avg_quality, 2),
                "comment": "Average quality score for end-to-end email responses",
            }
        )

        summary_scores.append(
            {
                "key": "end_to_end_correctness",
                "score": round(avg_correctness, 2),
                "comment": "Average correctness score for end-to-end email responses",
            }
        )

    return summary_scores


def load_results_from_directory(directory: str) -> List[Dict[str, Any]]:
    """
    Load results from YAML files in the specified directory.

    Args:
        directory: Directory containing the YAML files

    Returns:
        List of result dictionaries
    """
    results = []
    output_dir = Path(directory)

    for yaml_file in output_dir.glob("*.yaml"):
        if yaml_file.name.endswith("_report.json"):
            continue

        with open(yaml_file, "r") as f:
            try:
                data = yaml.load(f, Loader=SafeLoader)
                results.append(data)
            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")

    return results


def save_report(report: Dict[str, Any], output_dir: str, experiment_name: str) -> str:
    """
    Save a report to a JSON file.

    Args:
        report: Report dictionary
        output_dir: Directory to save the report
        experiment_name: Name of the experiment

    Returns:
        Path to the saved report
    """
    report_path = os.path.join(output_dir, f"{experiment_name}_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report_path
