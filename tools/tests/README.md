# Tests for Notebook Tools

This directory contains tests for the Jupyter notebook conversion tools.

## Structure

- `fixtures/`: Test input and expected output files
- `test_md_py_to_notebook.py`: Tests for the Markdown/Python to Jupyter notebook converter
- `test_ipynb_to_markdown.py`: Tests for the Jupyter notebook to Markdown converter

## Running Tests

You can run the tests in several ways:

### Running All Tests

```bash
# From the project root
python -m unittest discover -s tools/tests

# Or with Poetry
poetry run python -m unittest discover -s tools/tests
```

### Running Specific Test Files

```bash
# Run tests for the md_py_to_notebook.py tool
python -m unittest tools/tests/test_md_py_to_notebook.py

# Run tests for the ipynb_to_markdown.py tool
python -m unittest tools/tests/test_ipynb_to_markdown.py
```

### Running Individual Test Methods

```bash
# Run a specific test method
python -m unittest tools.tests.test_md_py_to_notebook.TestMdPyToNotebook.test_markdown_with_cell_attributes
```

## Test Fixtures

The fixtures directory contains:

- `markdown_basic_input.md`: Basic markdown file for testing
- `markdown_with_cell_attr_input.md`: Markdown file with {cell} attributes
- `python_basic_input.py`: Basic Python file for testing
- `python_with_cell_attr_input.py`: Python file with {cell} attributes in triple quotes
- `notebook_from_cell_attr_expected.ipynb`: Expected notebook output from cell attribute files
- `notebook_to_markdown_output.md`: Output from converting a notebook to markdown
- `markdown_to_notebook_output.ipynb`: Output from converting markdown back to a notebook

## Adding New Tests

To add new tests:

1. Add test fixtures to the `fixtures/` directory
2. Create test methods in the appropriate test class
3. Run the tests to verify your changes

## Round-Trip Testing

The tests include "round-trip" testing, where a file is converted:
notebook → markdown → notebook

This ensures that the bidirectional conversion process works correctly and preserves
the essential structure and content of the files. 