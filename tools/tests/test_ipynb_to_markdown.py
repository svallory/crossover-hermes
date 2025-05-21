#!/usr/bin/env python3
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

# Add the parent directory to sys.path to import the tool module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ipynb_to_markdown

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestIpynbToMarkdown(unittest.TestCase):
    """Tests for the ipynb_to_markdown.py tool."""

    def setUp(self):
        # Create a temporary directory for output files
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_notebook_to_markdown_conversion(self):
        """Test conversion of a notebook to markdown."""
        # Use the notebook generated from our tests as input
        input_file = os.path.join(FIXTURES_DIR, "notebook_from_cell_attr_expected.ipynb")
        output_file = os.path.join(self.temp_dir, "output.md")

        # Convert the notebook to markdown
        ipynb_to_markdown.convert_notebook_to_markdown(input_file, output_file)

        # Verify the output file exists
        self.assertTrue(os.path.exists(output_file))

        # Read the content of the output markdown file
        with open(output_file) as f:
            markdown_content = f.read()

        # Check for code block markers and {cell} attribute
        code_blocks = re.findall(r"```(\w+)\s+\{cell\}", markdown_content)

        # Verify that we have code blocks with the {cell} attribute
        self.assertTrue(len(code_blocks) > 0, "No code blocks with {cell} attribute found")

        # Verify that Python is one of the languages
        self.assertIn("python", code_blocks)

    def test_round_trip_conversion(self):
        """Test a round-trip conversion (notebook -> markdown -> notebook)."""
        # First convert a notebook to markdown
        input_notebook = os.path.join(FIXTURES_DIR, "notebook_from_cell_attr_expected.ipynb")
        intermediate_markdown = os.path.join(self.temp_dir, "intermediate.md")

        ipynb_to_markdown.convert_notebook_to_markdown(input_notebook, intermediate_markdown)

        # Now convert the markdown back to a notebook
        output_notebook = os.path.join(self.temp_dir, "round_trip.ipynb")

        # Import the md_py_to_notebook module for the second conversion
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        import md_py_to_notebook

        md_py_to_notebook.convert_file_to_notebook(intermediate_markdown, output_notebook)

        # Verify the output notebook exists
        self.assertTrue(os.path.exists(output_notebook))

        # Load both the original and round-trip notebooks
        with open(input_notebook) as f:
            original_notebook = json.load(f)

        with open(output_notebook) as f:
            round_trip_notebook = json.load(f)

        # Check that both notebooks have the same format
        self.assertEqual(original_notebook["nbformat"], round_trip_notebook["nbformat"])

        # Compare the number of cells
        original_cells = original_notebook["cells"]
        round_trip_cells = round_trip_notebook["cells"]

        # Allow for slight variations in cell count due to markdown parsing
        self.assertAlmostEqual(len(original_cells), len(round_trip_cells), delta=3)

        # Count the cell types in both notebooks
        original_code_cells = [cell for cell in original_cells if cell["cell_type"] == "code"]
        original_markdown_cells = [cell for cell in original_cells if cell["cell_type"] == "markdown"]

        round_trip_code_cells = [cell for cell in round_trip_cells if cell["cell_type"] == "code"]
        round_trip_markdown_cells = [cell for cell in round_trip_cells if cell["cell_type"] == "markdown"]

        # Check that the cell type counts are preserved (with some tolerance)
        self.assertAlmostEqual(len(original_code_cells), len(round_trip_code_cells), delta=2)
        self.assertAlmostEqual(len(original_markdown_cells), len(round_trip_markdown_cells), delta=2)

    def test_code_blocks_with_cell_attribute(self):
        """Test that code blocks in output markdown have {cell} attribute."""
        input_file = os.path.join(FIXTURES_DIR, "notebook_from_cell_attr_expected.ipynb")
        output_file = os.path.join(self.temp_dir, "output.md")

        # Convert the notebook to markdown
        ipynb_to_markdown.convert_notebook_to_markdown(input_file, output_file)

        # Read the content of the output markdown file
        with open(output_file) as f:
            markdown_content = f.read()

        # Count the code block markers (```python {cell})
        code_blocks = re.findall(r"```\w+\s+\{cell\}", markdown_content)

        # Load the original notebook to count code cells
        with open(input_file) as f:
            notebook = json.load(f)

        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]

        # Check that the number of code blocks with {cell} matches the number of code cells
        self.assertEqual(len(code_blocks), len(code_cells))


if __name__ == "__main__":
    unittest.main()
