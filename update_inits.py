#!/usr/bin/env python

import os
import re


def get_module_files(directory):
    """Get all Python files in a directory excluding __init__.py"""
    py_files = []
    for file in os.listdir(directory):
        if file.endswith(".py") and file != "__init__.py":
            py_files.append(file[:-3])  # Remove .py extension
    return py_files


def process_init_file(init_path):
    """Process an __init__.py file to use wildcard imports"""
    directory = os.path.dirname(init_path)
    module_files = get_module_files(directory)

    # Read the original content
    with open(init_path, "r") as f:
        content = f.read()

    # Extract docstring if present
    docstring_match = re.match(r'(""".*?"""|\'\'\'.*?\'\'\')\s*', content, re.DOTALL)
    docstring = docstring_match.group(0) if docstring_match else ""

    # Create new content with wildcard imports
    new_content = docstring if docstring else ""
    if new_content and not new_content.endswith("\n\n"):
        new_content += "\n\n"

    # Add wildcard imports for each module
    for module in module_files:
        new_content += f"from .{module} import *\n"

    # Write the updated content
    with open(init_path, "w") as f:
        f.write(new_content)

    print(f"Updated {init_path}")


def main():
    """Find and update all __init__.py files in the src/hermes directory"""
    for root, _, files in os.walk("src/hermes"):
        if "__init__.py" in files:
            init_path = os.path.join(root, "__init__.py")
            process_init_file(init_path)


if __name__ == "__main__":
    main()
