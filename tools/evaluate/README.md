# Hermes Evaluation Tools

The Hermes Evaluation Tools provide functionality for evaluating the performance of the Hermes agent flow. The evaluation is performed using a single comprehensive **Master Evaluator** that evaluates all components in a single pass.

## Key Features

- **Single-Pass Evaluation**: Evaluates all agent outputs in a single LLM call
- **Efficiency**: Reduces API calls by ~80% compared to individual evaluator approach
- **Comprehensive Analysis**: Provides detailed evaluation of each component and end-to-end performance
- **LangSmith Integration**: Automatically uploads results to LangSmith for tracking and analysis

## Components Evaluated

The master evaluator evaluates the following components:

1. **Email Analyzer** - Intent identification, entity extraction, and segmentation
2. **Order Processor** - Order identification, inventory handling, and response appropriateness (if applicable)
3. **Inquiry Responder** - Question identification, answer accuracy, and completeness (if applicable)
4. **Response Composer** - Tone, completeness, clarity, and call to action
5. **End-to-End Performance** - Overall system understanding, accuracy, helpfulness, and professionalism

## Usage

Run the evaluation tool using one of the following commands:

```bash
# Using a LangSmith dataset
python -m tools.evaluate.main --dataset-id <UUID> [--experiment-name <NAME>] [--dataset-name <NAME>]

# Using a directory of result files
python -m tools.evaluate.main --result-dir <DIR> [--experiment-name <NAME>] [--dataset-name <NAME>]
```

### Options

- `--experiment-name`: Custom name for the LangSmith experiment
- `--auto-upload`: Automatically upload results to LangSmith (default: enabled)
- `--no-upload`: Disable automatic upload of results to LangSmith
- `--dataset-name`: Custom name for the dataset when auto-uploading to LangSmith

## Implementation Details

The master evaluator takes the complete workflow state containing all agent outputs and evaluates them in a single call. This significantly reduces token usage and API calls while maintaining high-quality evaluation.

### Prompt Structure

The master evaluator prompt is structured into five distinct evaluation tasks, one for each component. It presents the original email along with the outputs from each component, then asks the LLM to evaluate each component based on specific criteria.

### Result Format

The evaluation results are formatted to maintain compatibility with the existing reporting structure:

```python
{
    "email_analyzer": {
        "intent_accuracy": 8,
        "information_extraction": 9,
        "segmentation_quality": 7,
        "reasoning": "..."
    },
    "order_processor": { ... },
    "inquiry_responder": { ... },
    "response_composer": { ... },
    "end_to_end": { ... }
}
```

## LangSmith Integration

The evaluation results are automatically uploaded to LangSmith with detailed feedback for each criterion. This enables tracking of performance over time and detailed analysis of system behavior.

## File Structure

- `main.py` - Main entry point and CLI interface
- `evaluators.py` - Contains the master evaluator implementation
- `workflow_runner.py` - Functionality for running the workflow on datasets
- `utils.py` - Utility functions for loading prompts and handling results
- `prompts/` - Directory containing evaluation prompts
  - `master_evaluator.md` - Main prompt for comprehensive evaluation 