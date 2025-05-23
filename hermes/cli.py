import argparse
import asyncio
import os
import sys

from hermes.core import run_email_processing


def create_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="hermes",
        description="Hermes - AI-powered email processing system for customer service automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hermes run INPUT                                # Process with default output directory
  hermes run INPUT --out-dir path/to/output       # Specify output directory
  hermes run INPUT --output-gsheet-id YOUR_SHEET_ID # Output to Google Sheets
  hermes run INPUT --limit 5                        # Process only 5 emails

Environment Variables:
  HERMES_PROCESSING_LIMIT Set to number to limit email processing
        """
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create the 'run' subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Process emails from spreadsheet",
        description="Process emails using the Hermes AI system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    run_parser.add_argument(
        "products_source",
        type=str,
        help="Source for product data: Google Spreadsheet ID#SheetName (e.g., 'your_gsheet_id#products') or path to a local CSV/Excel file."
    )

    run_parser.add_argument(
        "emails_source",
        type=str,
        help="Source for email data: Google Spreadsheet ID#SheetName (e.g., 'your_gsheet_id#emails') or path to a local CSV/Excel file."
    )
    
    run_parser.add_argument(
        "--output-gsheet-id",
        type=str,
        default=None, 
        help="Google Spreadsheet ID for output results. If provided, results will be uploaded to this sheet."
    )

    run_parser.add_argument(
        "--out-dir",
        type=str,
        default="./output",
        help="Directory to save output CSV files (default: ./output)"
    )
    
    run_parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Limit the number of emails to process (0 = no limit)"
    )
    
    return parser


def handle_run_command(args):
    """Handle the 'run' subcommand."""
    
    # Output directory
    output_dir = args.out_dir
    os.makedirs(output_dir, exist_ok=True)
    global OUTPUT_DIR # Allow modification of global OUTPUT_DIR for other modules if needed
    OUTPUT_DIR = output_dir
    print(f"Output directory set to: {output_dir}")

    # Input data: determine if it's a file path or a sheet ID
    input_source = args.input_data
    is_file_input = os.path.exists(input_source) # Basic check if it's a path
    
    spreadsheet_id_to_load = None
    local_file_path_to_load = None

    if is_file_input:
        print(f"Input data identified as local file: {input_source}")
        local_file_path_to_load = input_source
    else:
        print(f"Input data identified as Google Sheet ID: {input_source}")
        spreadsheet_id_to_load = input_source

    # Handle processing limit - argument takes precedence over environment variable
    limit = args.limit
    if limit is None:
        # Try to get limit from environment variable if not set by command-line
        env_limit = os.getenv("HERMES_PROCESSING_LIMIT")
        if env_limit:
            try:
                limit = int(env_limit)
            except ValueError:
                limit = None
    
    # Convert limit=0 to None for the main function (0 means no limit)
    if limit == 0:
        limit = None
    
    # Run the main function
    try:
        result = asyncio.run(run_email_processing(
            spreadsheet_id=spreadsheet_id_to_load, # Will be None if local_file_path_to_load is set
            local_file_path=local_file_path_to_load, # Will be None if spreadsheet_id_to_load is set
            products_source=args.products_source,
            emails_source=args.emails_source,
            output_spreadsheet_id=args.output_gsheet_id,
            # use_csv_output is now implicitly True, csv files always generated to out_dir
            # The decision to upload to GSheet is based on output_spreadsheet_id presence
            processing_limit=limit,
            output_dir=output_dir # Pass output_dir
        ))
        print(f"Final result: {result}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point for the Hermes CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # If no command is provided, show help
    if args.command is None:
        parser.print_help()
        return
    
    # Handle the specific command
    if args.command == "run":
        handle_run_command(args)
    else:
        parser.print_help()
        sys.exit(1) 