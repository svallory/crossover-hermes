import json
import os
import sys

def convert_notebook_to_markdown(ipynb_file_path: str, output_file_path: str | None = None) -> None:
    """Converts a Jupyter notebook (.ipynb file) to a Markdown file.
    If output_file_path is not provided, it defaults to the input filename with a .md extension.
    """
    try:
        with open(ipynb_file_path, encoding="utf-8") as f:
            notebook_content = f.read()

        notebook = json.loads(notebook_content)

        markdown_output_parts = []

        for cell in notebook.get("cells", []):
            source_content = "".join(cell.get("source", []))
            cell_type = cell.get("cell_type")

            if cell_type == "markdown":
                markdown_output_parts.append(source_content)
                markdown_output_parts.append("\n\n")
            elif cell_type == "code":
                cell.get("metadata", {})
                # Try to determine the language from metadata
                language = "python"  # Default to python
                if "language_info" in notebook.get("metadata", {}):
                    language = notebook["metadata"]["language_info"].get("name", "python")

                # Use triple backticks with {cell} attribute
                markdown_output_parts.append(f"```{language} {{cell}}\n")
                markdown_output_parts.append(source_content)
                if not source_content.endswith("\n"):
                    markdown_output_parts.append("\n")
                markdown_output_parts.append("```\n\n")

        final_markdown = "".join(markdown_output_parts)

        if output_file_path is None:
            base_name = os.path.splitext(ipynb_file_path)[0]
            output_file_path = base_name + ".md"
        else:
            # Ensure the parent directory for the output file exists
            output_dir = os.path.dirname(output_file_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(final_markdown)

        print(f"Successfully converted {ipynb_file_path} to {output_file_path}")

    except FileNotFoundError:
        print(f"Error: Input file not found: {ipynb_file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(
            f"Error: Could not decode JSON from file: {ipynb_file_path}",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if not 2 <= len(sys.argv) <= 3:
        print(
            f"Usage: python3 {sys.argv[0]} <path_to_ipynb_file> [output_markdown_file_path]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = sys.argv[1]
    custom_output_path = sys.argv[2] if len(sys.argv) == 3 else None

    convert_notebook_to_markdown(input_path, custom_output_path)
