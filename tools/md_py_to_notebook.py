#!/usr/bin/env python3
import argparse
import json
import re
import os
import sys
from typing import List, Dict, Any, Tuple, Optional


def parse_markdown_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a markdown file into Jupyter notebook cells.
    - Code blocks with ``` and {cell} attribute become code cells
    - Code blocks with ~~~ remain as part of markdown
    - Supports attributes like ```python {cell} for special handling
    """
    with open(file_path, 'r') as f:
        content = f.read()

    cells = []
    current_md_content = []
    
    # Split by code blocks with ``` - now supporting optional attributes with curly braces
    parts = re.split(r'```(\w*(?:\s+\{.*?\})?)\n(.*?)```', content, flags=re.DOTALL)
    
    for i in range(0, len(parts), 3):
        # Process markdown content
        md_part = parts[i]
        
        # Replace ~~~ code blocks with ``` in the markdown to preserve them
        md_part = re.sub(r'~~~(\w*(?:\s+\{.*?\})?)\n(.*?)~~~', r'```\1\n\2```', md_part, flags=re.DOTALL)
        
        if md_part.strip():
            current_md_content.append(md_part)
        
        # If we have a code block following
        if i + 2 < len(parts):
            # If we have accumulated markdown content, add it as a cell
            if current_md_content:
                cells.append({
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ''.join(current_md_content)
                })
                current_md_content = []
            
            lang_with_attr = parts[i + 1]
            code_content = parts[i + 2]
            
            # Parse language and attributes
            lang_match = re.match(r'(\w*)\s*(?:\{(.*?)\})?', lang_with_attr)
            language = lang_match.group(1) if lang_match else ""
            attributes_str = lang_match.group(2) if lang_match and lang_match.group(2) else ""
            
            # Process attributes to check for cell marker
            is_cell = False
            if attributes_str:
                # Check for variations like "cell", "cell=true", "cell='true'", etc.
                cell_pattern = r'cell(=|\s*:\s*|\s+)(true|"true"|\'true\')?|^cell$'
                is_cell = bool(re.search(cell_pattern, attributes_str, re.IGNORECASE))
            
            # Check if it's a code cell based on the cell attribute
            if is_cell:
                cells.append({
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": code_content
                })
            else:
                # For code without cell attribute, include as markdown
                cells.append({
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": f"```{language}\n{code_content}\n```"
                })
    
    # Add any remaining markdown content
    if current_md_content:
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": ''.join(current_md_content)
        })
    
    return cells


def parse_python_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a Python file into Jupyter notebook cells.
    - Regular Python code becomes code cells
    - Triple quotes with {cell} attribute become markdown cells
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all triple-quote blocks with {cell} attribute for markdown cells
    # First, mark them with special tags to preserve them during processing
    markdown_blocks = []
    
    def replace_markdown_block(match):
        block_content = match.group(2)
        attributes_str = match.group(1) if match.group(1) else ""
        
        # Process attributes to check for cell marker
        is_markdown_cell = False
        if attributes_str:
            # Check for variations like "cell", "cell=true", "cell='true'", etc.
            cell_pattern = r'cell(=|\s*:\s*|\s+)(true|"true"|\'true\')?|^cell$'
            is_markdown_cell = bool(re.search(cell_pattern, attributes_str, re.IGNORECASE))
        
        if is_markdown_cell:
            # This is a markdown cell
            marker = f"MARKDOWN_CELL_{len(markdown_blocks)}"
            markdown_blocks.append(block_content)
            return marker
        else:
            # Regular triple-quote docstring or multi-line string
            return match.group(0)
    
    # Find triple-quote blocks with {cell} attribute
    # The pattern matches """ {cell} or variations followed by content and closing """
    processed_content = re.sub(
        r'"""(?:\s*\{(.*?)\})?\n(.*?)"""', 
        replace_markdown_block, 
        content, 
        flags=re.DOTALL
    )
    
    # Now split the remaining content into code cells
    code_parts = processed_content.split("MARKDOWN_CELL_")
    
    cells = []
    
    # Process the first part (always code)
    if code_parts[0].strip():
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": code_parts[0]
        })
    
    # Process any remaining parts (alternating markdown and code)
    for i, part in enumerate(code_parts[1:], 1):
        # Extract the markdown block index
        match = re.match(r'(\d+)(.*)', part, re.DOTALL)
        if match:
            md_index = int(match.group(1))
            code_content = match.group(2)
            
            # Add the markdown cell
            cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": markdown_blocks[md_index]
            })
            
            # Add the code cell if there's any code content
            if code_content.strip():
                cells.append({
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": code_content
                })
    
    return cells


def create_notebook(cells: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a Jupyter notebook structure with the given cells and metadata.
    """
    if metadata is None:
        metadata = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        }
    
    notebook = {
        "cells": cells,
        "metadata": metadata,
        "nbformat": 4,
        "nbformat_minor": 0
    }
    
    return notebook


def convert_file_to_notebook(input_path: str, output_path: str):
    """
    Convert a markdown or Python file to a Jupyter notebook.
    """
    _, ext = os.path.splitext(input_path)
    
    if ext.lower() in ['.md', '.markdown']:
        cells = parse_markdown_file(input_path)
    elif ext.lower() == '.py':
        cells = parse_python_file(input_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
    
    notebook = create_notebook(cells)
    
    with open(output_path, 'w') as f:
        json.dump(notebook, f, indent=2)
    
    print(f"Converted {input_path} to {output_path}")


def find_md_py_files(directory: str) -> List[str]:
    """
    Recursively find all markdown and Python files in a directory.
    Returns a sorted list of file paths.
    """
    result = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.md', '.markdown', '.py')):
                result.append(os.path.join(root, file))
    
    return sorted(result)


def process_input(input_path: str, output_dir: str):
    """
    Process a single input path (file or directory) and convert to notebook.
    """
    if os.path.isdir(input_path):
        # Handle directory - find all relevant files and process them
        files = find_md_py_files(input_path)
        print(f"Found {len(files)} markdown/python files in {input_path}")
        
        if not files:
            print(f"No markdown or Python files found in {input_path}")
            return
        
        # Create a single notebook from all files in order
        all_cells = []
        for file in files:
            _, ext = os.path.splitext(file)
            
            # Add a cell with the filename as header
            filename = os.path.basename(file)
            all_cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": f"# File: {filename}\n\n"
            })
            
            # Add cells from the file
            if ext.lower() in ['.md', '.markdown']:
                all_cells.extend(parse_markdown_file(file))
            elif ext.lower() == '.py':
                all_cells.extend(parse_python_file(file))
        
        # Determine the output filename based on the input directory name
        dir_name = os.path.basename(os.path.normpath(input_path))
        output_path = os.path.join(output_dir, f"{dir_name}.ipynb")
        
        notebook = create_notebook(all_cells)
        
        with open(output_path, 'w') as f:
            json.dump(notebook, f, indent=2)
        
        print(f"Created notebook {output_path} from {len(files)} files in {input_path}")
    
    else:
        # Handle single file
        base_name = os.path.basename(input_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}.ipynb")
        
        try:
            convert_file_to_notebook(input_path, output_path)
        except Exception as e:
            print(f"Error converting {input_path}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Convert markdown or Python files to Jupyter notebooks")
    parser.add_argument('inputs', nargs='+', help='Input files or directories (markdown or Python)')
    parser.add_argument('-o', '--output-dir', default='.', help='Output directory')
    
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    for input_path in args.inputs:
        if not os.path.exists(input_path):
            print(f"Error: Path {input_path} does not exist", file=sys.stderr)
            continue
        
        process_input(input_path, args.output_dir)


if __name__ == "__main__":
    main() 