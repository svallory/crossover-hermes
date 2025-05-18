#!/usr/bin/env python
"""
Wrapper script for Hermes workflow evaluation.

This script is a simple wrapper around tools.evaluate.main to maintain
compatibility with existing code and provide a convenient entry point.

Usage:
  python -m tools.evaluate_workflow --dataset-id UUID [--experiment-name NAME]
"""

import sys
from tools.evaluate.main import main

if __name__ == "__main__":
    main()
