# Hermes Tools

This directory contains various utility scripts for the Hermes project.

## Available Tools

### `evaluate_agent_flow.py`

Evaluates the Hermes agent flow using LangSmith's LLM-as-judge framework.

**Features:**
- Runs the Hermes agent flow using the test infrastructure
- Creates a LangSmith experiment to evaluate the results
- Uses LLM-as-judge to evaluate each agent's performance
- Generates a summary report of evaluation scores

**Usage:**
```bash
# Run with default settings (5 emails)
python -m tools.evaluate_agent_flow

# Process a specific number of emails
python -m tools.evaluate_agent_flow --limit 10 

# Specify a custom experiment name
python -m tools.evaluate_agent_flow --experiment-name "my_evaluation"
```

**Requirements:**
- LangSmith API key in your `.env` file (`LANGSMITH_API_KEY`)
- Properly configured Hermes environment

### `ipynb_to_markdown.py`

Converts a Jupyter notebook to a Markdown file. Useful for documentation.

**Usage:**
```bash
python -m tools.ipynb_to_markdown notebook.ipynb output.md
```

### `md_py_to_notebook.py`

Converts a Markdown/Python file to a Jupyter notebook.

**Usage:**
```bash
python -m tools.md_py_to_notebook some_file.md notebook.ipynb
``` 