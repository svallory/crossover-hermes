#!/usr/bin/env python3
import unittest
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to sys.path to import the tool module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import md_py_to_notebook

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestMdPyToNotebook(unittest.TestCase):
    """Tests for the md_py_to_notebook.py tool."""

    def setUp(self):
        # Create a temporary directory for output files
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_markdown_with_cell_attributes(self):
        """Test conversion of markdown with {cell} attributes."""
        input_file = os.path.join(FIXTURES_DIR, 'markdown_with_cell_attr_input.md')
        output_file = os.path.join(self.temp_dir, 'output.ipynb')
        
        md_py_to_notebook.convert_file_to_notebook(input_file, output_file)
        
        # Verify the output file exists
        self.assertTrue(os.path.exists(output_file))
        
        # Load the generated notebook
        with open(output_file, 'r') as f:
            notebook = json.load(f)
        
        # Check the notebook structure
        self.assertEqual(notebook['nbformat'], 4)
        self.assertTrue('cells' in notebook)
        
        # Check that we have the expected number of cells
        # The markdown with cell attributes should have multiple cell types
        cells = notebook['cells']
        
        # Count code and markdown cells
        code_cells = [cell for cell in cells if cell['cell_type'] == 'code']
        markdown_cells = [cell for cell in cells if cell['cell_type'] == 'markdown']
        
        # Verify we have both code and markdown cells
        self.assertTrue(len(code_cells) > 0, "No code cells found")
        self.assertTrue(len(markdown_cells) > 0, "No markdown cells found")
        
        # Check that code blocks with {cell} attribute became code cells
        # This depends on the specific content of the test file
        # We know our test file has at least 3 code cells with {cell} attribute
        self.assertGreaterEqual(len(code_cells), 3)
    
    def test_python_with_cell_attributes(self):
        """Test conversion of Python with {cell} attributes in triple quotes."""
        input_file = os.path.join(FIXTURES_DIR, 'python_with_cell_attr_input.py')
        output_file = os.path.join(self.temp_dir, 'output.ipynb')
        
        md_py_to_notebook.convert_file_to_notebook(input_file, output_file)
        
        # Verify the output file exists
        self.assertTrue(os.path.exists(output_file))
        
        # Load the generated notebook
        with open(output_file, 'r') as f:
            notebook = json.load(f)
        
        # Check the notebook structure
        self.assertEqual(notebook['nbformat'], 4)
        self.assertTrue('cells' in notebook)
        
        # Check that we have the expected number of cells
        cells = notebook['cells']
        
        # Count code and markdown cells
        code_cells = [cell for cell in cells if cell['cell_type'] == 'code']
        markdown_cells = [cell for cell in cells if cell['cell_type'] == 'markdown']
        
        # Verify we have both code and markdown cells
        self.assertTrue(len(code_cells) > 0, "No code cells found")
        self.assertTrue(len(markdown_cells) > 0, "No markdown cells found")
        
        # Check that triple quote blocks with {cell} attribute became markdown cells
        # We know our test file has 2 markdown cells from triple quotes with {cell}
        self.assertGreaterEqual(len(markdown_cells), 2)
    
    def test_directory_processing(self):
        """Test processing of a directory with multiple markdown and Python files."""
        output_file = os.path.join(self.temp_dir, 'output.ipynb')
        
        # Define the list of files to process
        input_files = [
            os.path.join(FIXTURES_DIR, 'markdown_with_cell_attr_input.md'),
            os.path.join(FIXTURES_DIR, 'python_with_cell_attr_input.py')
        ]
        
        # Create a temporary directory with the test files
        test_dir = os.path.join(self.temp_dir, 'test_dir')
        os.makedirs(test_dir)
        for file in input_files:
            shutil.copy(file, test_dir)
        
        # Process the directory
        md_py_to_notebook.process_input(test_dir, self.temp_dir)
        
        # Check that the output notebook was created
        dir_name = os.path.basename(test_dir)
        expected_output = os.path.join(self.temp_dir, f"{dir_name}.ipynb")
        self.assertTrue(os.path.exists(expected_output))
        
        # Load the generated notebook
        with open(expected_output, 'r') as f:
            notebook = json.load(f)
        
        # The notebook should contain cells from both files plus headers
        cells = notebook['cells']
        self.assertGreater(len(cells), 0)
        
        # Verify that we have the header cells (one per file)
        headers = [cell for cell in cells if cell['cell_type'] == 'markdown' 
                  and 'source' in cell and '# File:' in cell['source']]
        self.assertEqual(len(headers), 2)


if __name__ == '__main__':
    unittest.main() 