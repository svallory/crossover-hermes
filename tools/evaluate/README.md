# Hermes Evaluation Tools

A clean, simple evaluation system for the Hermes workflow with LangSmith integration.

## Overview

This evaluation tool provides two types of evaluators:
1. **Simple Evaluators**: Fast, rule-based checks for basic functionality
2. **LLM-as-a-Judge Evaluators**: Sophisticated AI-powered evaluation for quality assessment

## Quick Start

### Prerequisites

1. Ensure your `.env` file has the required variables:
   ```bash
   LANGSMITH_API_KEY=your_langsmith_api_key
   LANGSMITH_PROJECT=your_project_name
   OPENAI_API_KEY=your_openai_api_key
   ```

2. Have a LangSmith dataset ready with email examples. The dataset should contain examples with:
   - `email_id` (optional, will be auto-generated)
   - `subject` or `email_subject`
   - `message` or `email_message`

### Running Evaluations

#### Basic Usage
```bash
# Run evaluation with simple evaluators
uv run python -m tools.evaluate.cli my_dataset_name

# Run with custom experiment name
uv run python -m tools.evaluate.cli my_dataset_name --experiment-name "my_test_run"

# Limit number of examples
uv run python -m tools.evaluate.cli my_dataset_name --max-examples 10
```

#### Advanced Usage
```bash
# Use LLM-as-a-judge evaluators for sophisticated evaluation
uv run python -m tools.evaluate.cli my_dataset_name --use-llm-evaluators

# Combine options
uv run python -m tools.evaluate.cli my_dataset_name \
  --experiment-name "llm_eval_test" \
  --max-examples 5 \
  --use-llm-evaluators
```

#### Create Sample Dataset
```bash
# Create a sample dataset for testing
uv run python tools/evaluate/create_dataset.py "my_test_dataset"
```

#### Test the System
```bash
# Test that everything is working
uv run python tools/evaluate/test_eval.py
```

## Evaluation Types

### Simple Evaluators

These evaluators provide basic functionality checks:

1. **Classification Accuracy**: Checks if email classification is reasonable
2. **Response Quality**: Validates that a response was generated
3. **Workflow Completion**: Ensures the workflow completed without errors

### LLM-as-a-Judge Evaluators

These use GPT-4 to evaluate quality more sophisticatedly:

1. **Classification Accuracy**: AI assessment of classification correctness
2. **Response Quality**: Multi-criteria evaluation including:
   - Helpfulness
   - Professionalism
   - Completeness

## Programmatic Usage

You can also use the evaluation tools programmatically:

```python
import asyncio
from tools.evaluate.evaluate import run_evaluation

async def main():
    result = await run_evaluation(
        dataset_name="my_dataset",
        experiment_name="my_experiment",
        max_examples=10
    )
    print(f"Results: {result['langsmith_url']}")

asyncio.run(main())
```

For LLM evaluators:

```python
import asyncio
from langsmith import evaluate
from tools.evaluate.evaluate import create_target_function
from tools.evaluate.llm_evaluators import create_llm_evaluator_functions

async def main():
    target = create_target_function()
    evaluators = create_llm_evaluator_functions()

    results = evaluate(
        target,
        data="my_dataset",
        evaluators=evaluators,
        experiment_prefix="my_experiment"
    )

asyncio.run(main())
```

## Dataset Format

Your LangSmith dataset should contain examples with the following structure:

```json
{
  "email_id": "email_001",
  "subject": "Question about product availability",
  "message": "Hi, I'm interested in purchasing the blue dress from your summer collection. Is it available in size M?"
}
```

Alternative field names are supported:
- `email_subject` instead of `subject`
- `email_message` instead of `message`

## Evaluation Results

Results are automatically uploaded to LangSmith where you can:
- View detailed evaluation scores
- Compare different experiments
- Analyze individual example results
- Track performance over time

Each evaluation creates a LangSmith experiment with:
- Individual run results for each email
- Evaluation scores and feedback
- Links to view in the LangSmith UI

## Evaluation Metrics

### Simple Evaluators
- `classification_accuracy`: 0-1 score for classification
- `response_quality`: 0-1 score for response generation
- `workflow_completion`: 0-1 score for workflow completion

### LLM Evaluators
- `llm_classification_accuracy`: AI-assessed classification accuracy (0-1)
- `llm_response_quality`: Multi-criteria response quality assessment (0-1)

## Example Workflow

1. **Create a dataset**:
   ```bash
   uv run python tools/evaluate/create_dataset.py "hermes_test_dataset"
   ```

2. **Run basic evaluation**:
   ```bash
   uv run python -m tools.evaluate.cli "hermes_test_dataset" --experiment-name "basic_test"
   ```

3. **Run advanced LLM evaluation**:
   ```bash
   uv run python -m tools.evaluate.cli "hermes_test_dataset" --use-llm-evaluators --experiment-name "llm_test"
   ```

4. **View results** in LangSmith at https://smith.langchain.com/

## Troubleshooting

### Common Issues

1. **"No dataset found"**: Ensure your dataset name is correct and exists in LangSmith
2. **Authentication errors**: Check your `LANGSMITH_API_KEY` is set correctly
3. **Workflow errors**: Ensure your Hermes configuration is complete (products data, vector store, etc.)

### Debug Mode

For debugging, you can run the test script:

```bash
uv run python tools/evaluate/test_eval.py
```

Or test individual components:

```python
# Test the target function directly
from tools.evaluate.evaluate import create_target_function

target = create_target_function()
result = await target({
    "subject": "Test email",
    "message": "This is a test message"
})
print(result)
```

## Architecture

- `evaluate.py`: Main evaluation logic with simple evaluators
- `llm_evaluators.py`: LLM-as-a-judge evaluators
- `cli.py`: Command-line interface
- `create_dataset.py`: Helper to create sample datasets
- `test_eval.py`: Test script to verify everything works
- `__init__.py`: Package initialization

The evaluation system:
1. Creates a target function that runs the Hermes workflow
2. Defines evaluators that assess workflow outputs
3. Uses LangSmith's `evaluate()` function to run the evaluation
4. Uploads results to LangSmith for analysis