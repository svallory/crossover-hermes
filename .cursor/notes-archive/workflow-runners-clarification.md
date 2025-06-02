# Workflow Runner Files Clarification

## Overview

There are three files related to running the Hermes workflow, each serving a different purpose:

## 1. `hermes/workflow/run.py` (Core Library)
- **Purpose**: Core workflow execution function
- **Type**: Library module
- **Function**: `run_workflow()` - the main workflow execution logic
- **Usage**: Imported by other files to run the workflow
- **Status**: ✅ MUST STAY - This is the core implementation

## 2. ~~`tools/run_workflow.py` (CLI Tool)~~ - DELETED
- **Purpose**: ~~Command-line interface for manual workflow execution~~
- **Type**: ~~CLI script~~
- **Status**: ❌ DELETED - Redundant with `hermes/cli.py`
- **Reason**: `hermes/cli.py` provides the same functionality with more features

## 3. `tools/evaluate/workflow_runner.py` (Evaluation Tool)
- **Purpose**: Runs workflow on LangSmith datasets for evaluation
- **Type**: Evaluation framework component
- **Features**:
  - Integrates with LangSmith datasets
  - Creates experiments and tracks runs
  - Returns structured results for evaluation
  - Used by the evaluation system
- **Usage**: Called by evaluation tools
- **Status**: ✅ KEEP - Part of evaluation framework

## Analysis: CLI Tools Comparison

### `hermes/cli.py` (Main CLI - KEEP)
- **Official CLI**: Uses `hermes.core.run_email_processing()`
- **More features**:
  - Supports both Google Sheets and CSV sources
  - Can output to Google Sheets
  - Supports products catalog loading
  - More robust argument parsing
  - Better error handling
- **Production ready**: Part of the main package
- **Usage**: `hermes run PRODUCTS_SRC EMAILS_SRC --email-id E001,E002`

### ~~`tools/run_workflow.py` (Development Tool - DELETED)~~
- **Development tool**: Used `hermes.workflow.run.run_workflow()` directly
- **Limited features**:
  - Only read from `data/emails.csv` (hardcoded)
  - Only output YAML files
  - No products catalog integration
  - Simpler, more direct workflow testing
- **Status**: ❌ DELETED - Redundant functionality

## Final Recommendation

**Keep two files** - they serve different, non-overlapping purposes:
1. `hermes/workflow/run.py` - Core library (required)
2. `tools/evaluate/workflow_runner.py` - Evaluation framework component

**Deleted**: `tools/run_workflow.py` - Redundant with the more complete `hermes/cli.py`