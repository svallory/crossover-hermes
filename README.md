# Hermes: Human-like Email Responses for Magically Empathic Sales

A project for intelligently processing email order requests and customer inquiries for a fashion store using advanced AI techniques.

## Project Structure

```
hermes/
├── docs/               # Documentation
├── sample-data/        # Sample data for testing
├── src/                # Source files to be assembled into notebooks
├── tools/              # Utility scripts for notebook conversion/assembly
│   ├── ipynb_to_markdown.py  # Tool to convert .ipynb to .md
│   ├── md_py_to_notebook.py  # Tool to convert .md and .py to .ipynb
│   └── tests/               # Test suite for the tools
│       ├── fixtures/        # Test input and output files
│       └── README.md        # Test documentation
├── pyproject.toml      # Project configuration and dependencies
└── README.md           # This file
```

## Setup

This project uses [Poetry](https://python-poetry.org/) for dependency management and [Poethepoet](https://github.com/nat-n/poethepoet) for task running.

### Prerequisites

- Python 3.9+
- [Poetry](https://python-poetry.org/docs/#installation)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/svallory/hermes.git
   cd hermes
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

## Available Tasks

This project uses Poetry with Poethepoet for running tasks. The following tasks are available:

### nb2md - Convert Jupyter Notebook to Markdown

Convert a Jupyter Notebook (.ipynb) file to a Markdown (.md) file.

```bash
# Basic usage (output will be {input_name}.md)
poetry run poe nb2md path/to/notebook.ipynb

# With custom output path
poetry run poe nb2md path/to/notebook.ipynb custom/output/path.md
```

### build-notebook - Convert Markdown/Python to Jupyter Notebook

Convert Markdown (.md) or Python (.py) files to a Jupyter Notebook (.ipynb). Can also process entire directories.

```bash
# Basic usage for single files
poetry run poe build-notebook path/to/document.md

# Process multiple files with output directory
poetry run poe build-notebook file1.md file2.py -o output_dir/

# Process an entire directory (all .md and .py files)
poetry run poe build-notebook src/ -o notebooks/
```

#### Markdown Syntax for Code Cells

The build-notebook tool uses special syntax to identify which code blocks should be executable cells:

- All code blocks (regardless of language) need the `{cell}` attribute to become executable cells:
  ```python {cell}
  # This becomes an executable code cell
  print("Hello world")
  ```

- Without the `{cell}` attribute, code blocks remain as part of the markdown:
  ```python
  # This stays as a markdown code block (not executable)
  print("Not executed")
  ```

- Code blocks with triple tildes (~~~) always remain as markdown code blocks:
  ~~~python
  print("This stays as markdown")
  ~~~

- You can use various attribute formats:
  ```javascript {cell}
  // Basic cell attribute
  ```
  ```javascript {cell=true}
  // Explicit true value
  ```
  ```javascript {cell="true"}
  // String value
  ```

#### Python Syntax for Markdown Cells

In Python files:

- Regular Python code becomes code cells
- Triple-quote blocks with `{cell}` attribute become markdown cells:

```python
# This is a regular code cell
x = 10
print(x)

""" {cell}
# This is a markdown cell
This content will be rendered as markdown in the notebook.
- It can include lists
- And other markdown formatting
"""

# Back to code
y = 20
print(x + y)
```

See the [tools/README.md](tools/README.md) file for more detailed documentation.

### test - Run Tests

Run the unit tests for the tools:

```bash
# Run all tests
poetry run poe test

# Run a specific test file
python -m unittest tools/tests/test_md_py_to_notebook.py

# Run a specific test method
python -m unittest tools.tests.test_md_py_to_notebook.TestMdPyToNotebook.test_markdown_with_cell_attributes
```

See the [tools/tests/README.md](tools/tests/README.md) file for more information about testing.

## Development Workflow

### Creating a New Notebook

1. Create your notebook components (markdown files, python scripts) in the `src/` directory.
2. Use the tools to assemble these components into a Jupyter Notebook:
   ```bash
   poetry run poe build-notebook src/your_components/ -o notebooks/
   ```

### Converting an Existing Notebook

1. Use the `nb2md` task to transform a Jupyter Notebook to Markdown:
   ```bash
   poetry run poe nb2md notebook.ipynb
   ```
2. This will create a new Markdown file with the same base name.

### Bidirectional Conversion

The tools support bidirectional conversion between notebooks and markdown/Python files:

1. Convert a notebook to markdown with `nb2md`
2. Edit the markdown file
3. Convert it back to a notebook with `build-notebook`

The cell structure and types are preserved in the round-trip conversion.

## License

[Add your chosen license information here]