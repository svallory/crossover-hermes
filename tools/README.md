# Markdown/Python to Jupyter Notebook Converter

This tool converts Markdown and Python files to Jupyter notebook format.

## Usage

```bash
python3 md_py_to_notebook.py [inputs...] [-o OUTPUT_DIR]
```

When using through Poetry:
```bash
poetry run poe build-notebook [inputs...] [-o OUTPUT_DIR]
```

### Arguments:

- `inputs`: One or more Markdown (.md), Python (.py) files, or directories
- `-o, --output-dir`: Directory to save the output notebooks (default: current directory)

## Conversion Rules

### Markdown Files

1. Regular markdown content is preserved as markdown cells
2. Code blocks with the `{cell}` attribute become code cells (regardless of language):
   ```python {cell}
   print("This becomes a code cell")
   ```
3. Code blocks without the `{cell}` attribute remain as markdown code blocks:
   ```python
   print("This stays as markdown")
   ```
4. Code blocks delimited with triple tildes (~~~) always remain as markdown code blocks:
   ~~~python
   print("This stays as markdown")
   ~~~
5. Supported `{cell}` attribute variations include:
   ```javascript {cell}
   // Basic cell attribute
   ```
   ```javascript {cell=true}
   // Explicit true value
   ```
   ```javascript {cell="true"}
   // String value
   ```

### Python Files

1. Regular Python code becomes code cells
2. Triple-quote blocks with the `{cell}` attribute become markdown cells:

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

3. Support for attribute variations in triple quotes:
   ```python
   """ {cell}
   # Basic cell attribute
   """
   
   """ {cell=true}
   # Explicit true value
   """
   
   """ {cell="true"}
   # String value
   """
   ```

## Directory Support

When a directory is provided as an input:

1. The script recursively searches for all .md, .markdown, and .py files in the directory
2. Files are sorted alphabetically
3. A single notebook is created containing all files in order
4. Each file is preceded by a markdown cell with the filename as a header

Example:
```bash
python3 md_py_to_notebook.py docs/ -o notebooks/
```

## Examples

Convert a single file:
```bash
python3 md_py_to_notebook.py document.md
```

Convert multiple files with a specific output directory:
```bash
python3 md_py_to_notebook.py file1.md file2.py -o notebooks/
```

Convert an entire directory:
```bash
python3 md_py_to_notebook.py src/ -o notebooks/
```

Convert mixed inputs:
```bash
python3 md_py_to_notebook.py file1.md directory1/ directory2/
```

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library modules) 