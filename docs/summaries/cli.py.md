# Summary of src/hermes/cli.py

This file, `cli.py`, implements the command-line interface (CLI) for the Hermes email processing system. It uses the `argparse` module to define commands, options, and arguments, allowing users to interact with and control the Hermes application from the terminal. The primary functionality exposed is the `run` command, which orchestrates the email processing workflow.

Key components and responsibilities:
-   **`create_parser() -> argparse.ArgumentParser`**:
    -   **Purpose**: Creates and configures the main `ArgumentParser` for the Hermes CLI.
    -   **Description**: Sets up the program name (`hermes`), a general description, and an epilog with usage examples and notes on relevant environment variables (like `HERMES_PROCESSING_LIMIT`).
    -   **Subcommands**: Defines a subparser system to handle different commands. Currently, it sets up one primary subcommand:
        -   **`run` subcommand**: 
            -   **Help/Description**: "Process emails from spreadsheet", "Process emails using the Hermes AI system".
            -   **Arguments for `run`**:
                -   `products_source` (positional, str): Specifies the source for product data. Can be a Google Spreadsheet ID and sheet name (e.g., `your_gsheet_id#products`) or a path to a local CSV/Excel file.
                -   `emails_source` (positional, str): Specifies the source for email data, with a similar format to `products_source`.
                -   `--output-gsheet-id` (optional, str): Google Spreadsheet ID where output results should be uploaded. If not provided, results are typically saved locally as CSVs.
                -   `--out-dir` (optional, str, default: `./output`): Directory where output CSV files will be saved.
                -   `--limit` (optional, int, metavar: `N`): Limits the number of emails to process. A value of 0 or less means no limit.
                -   `--email-id` (optional, str, action: `append`): Allows specifying one or more specific email IDs to process. Can be used multiple times or with a comma-separated list (e.g., `--email-id id1 --email-id id2,id3`).

-   **`handle_run_command(args: argparse.Namespace) -> None`**:
    -   **Purpose**: Handles the logic when the `run` subcommand is invoked.
    -   **Mechanism**:
        1.  **Output Directory**: Ensures the specified `args.out_dir` exists, creating it if necessary. Updates a global `OUTPUT_DIR` variable (noted as potentially needing refinement for better encapsulation).
        2.  **Processing Limit**: Determines the processing limit. It prioritizes the `--limit` command-line argument. If not set, it attempts to read the `HERMES_PROCESSING_LIMIT` environment variable. A limit of 0 or less is treated as no limit (None).
        3.  **Target Email IDs**: If `--email-id` is used, it parses the provided ID(s), handling multiple uses of the flag and comma-separated values. It builds a `target_email_ids_list`. If the flag is used but no valid IDs are extracted, it prints a warning and exits.
        4.  **Core Processing Execution**: Calls `asyncio.run(run_email_processing(...))` from `hermes.core`. It passes all the parsed and processed arguments: `products_source`, `emails_source`, `output_spreadsheet_id`, the determined `limit`, the `final_target_email_ids`, and `output_dir`.
        5.  **Error/Interrupt Handling**: Catches `KeyboardInterrupt` for graceful exit on user cancellation and other `Exception`s, printing an error message and exiting.

-   **`main() -> None`**:
    -   **Purpose**: The main entry point for the Hermes CLI application.
    -   **Mechanism**:
        1.  Calls `create_parser()` to get the configured argument parser.
        2.  Parses the command-line arguments using `parser.parse_args()`.
        3.  If no command is provided (e.g., just `hermes` is run), it prints the help message.
        4.  If the command is `run`, it calls `handle_run_command(args)`.
        5.  If an unknown command is given, it prints help and exits.

Architecturally, `cli.py` provides a user-friendly command-line wrapper around the core email processing logic (`hermes.core.run_email_processing`). It effectively decouples the user interaction layer from the application's core functionality. By using `argparse`, it offers a standard and well-documented way for users to configure and initiate processing tasks, including specifying data sources, output destinations, and processing controls like limits and specific email targeting. The handling of environment variables for some options (like processing limit) provides an additional layer of configuration flexibility. This CLI makes the Hermes system accessible and runnable in various environments, from local development to automated scripts.

[Link to source file](../../../src/hermes/cli.py) 