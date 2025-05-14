import os
from pathlib import Path

def read_prompt_md(filename: str, prompt_dir: Path) -> str:
    """Helper function to read a markdown prompt file.
    
    Args:
        filename: The name of the markdown file to read.
        prompt_dir: The directory containing the prompt file.
        
    Returns:
        The contents of the prompt file as a string.
    """
    file_path = prompt_dir / filename
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Prompt file '{filename}' not found in {prompt_dir}."
    except Exception as e:
        return f"Error reading prompt file '{filename}': {e}"
