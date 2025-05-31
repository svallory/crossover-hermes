import argparse
import asyncio
import os
import sys

from hermes.core import run_email_processing
from hermes.utils.logger import logger, get_agent_logger


def create_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="hermes",
        description="Hermes - AI-powered email processing system for customer service automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hermes run PRODUCTS_SRC EMAILS_SRC                                          # Process with default output directory
  hermes run PRODUCTS_SRC EMAILS_SRC --out-dir path/to/output                 # Specify output directory
  hermes run PRODUCTS_SRC EMAILS_SRC --output-gsheet-id YOUR_SHEET_ID         # Output to Google Sheets
  hermes run PRODUCTS_SRC EMAILS_SRC --limit 5                                # Process only 5 emails
  hermes run PRODUCTS_SRC EMAILS_SRC --email-id specific_email_id             # Process only a specific email ID
  hermes run PRODUCTS_SRC EMAILS_SRC --email-id id1,id2                       # Process a comma-separated list of email IDs
  hermes run PRODUCTS_SRC EMAILS_SRC --email-id id1 --email-id id2            # Process multiple specific email IDs
  hermes run PRODUCTS_SRC EMAILS_SRC --stop-on-error                          # Stop processing if an error occurs

  A source can be a Google Sheet (format: 'Gsheet_Id#SheetName') or a path to a local CSV.

Environment Variables:
  HERMES_PROCESSING_LIMIT Set to number to limit email processing
        """,
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create the 'run' subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Process emails from spreadsheet",
        description="""
    Process emails using the Hermes AI system

    A source can be a Google Sheet (format: 'Gsheet_Id#SheetName') or a path to a local CSV.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    run_parser.add_argument(
        "products_source", type=str, help="Source for products catalog."
    )

    run_parser.add_argument(
        "emails_source", type=str, help="Source for the customer emails."
    )

    run_parser.add_argument(
        "--output-gsheet-id",
        type=str,
        default=None,
        help="Google Spreadsheet ID for output results. If provided, results will be uploaded to this sheet.",
    )

    run_parser.add_argument(
        "--out-dir",
        type=str,
        default="./output",
        help="Directory to save output CSV files (default: ./output)",
    )

    run_parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Limit the number of emails to process (default: no limit, 0 means no limit)",
    )

    run_parser.add_argument(
        "--email-id",
        type=str,
        action="append",
        help="Process only specific email IDs. Can be used multiple times or as a comma-separated list (e.g., --email-id id1 --email-id id2,id3).",
    )

    run_parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop processing immediately if an error occurs with any email.",
    )

    return parser


def handle_run_command(args):
    """Handle the 'run' subcommand."""

    # Output directory
    output_dir = args.out_dir
    os.makedirs(output_dir, exist_ok=True)
    logger.info(
        get_agent_logger(
            "CLI",
            f"Output directory set to: [cyan underline]{output_dir}[/cyan underline]",
        )
    )

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
    if limit is not None and limit <= 0:
        limit = None
    if limit is not None:
        logger.info(
            get_agent_logger(
                "CLI", f"Processing limit set to: [yellow]{limit}[/yellow] emails"
            )
        )

    # Process email IDs if provided
    target_email_ids_list = []
    if args.email_id:
        for item in args.email_id:
            target_email_ids_list.extend(
                [eid.strip() for eid in item.split(",") if eid.strip()]
            )

        if target_email_ids_list:
            logger.info(
                get_agent_logger(
                    "CLI",
                    f"Targeting specific email IDs: [yellow]{target_email_ids_list}[/yellow]",
                )
            )
        else:
            # Handles cases like --email-id "" or --email-id ",,"
            logger.warning(
                get_agent_logger(
                    "CLI",
                    "--email-id flag used but no valid IDs were extracted. No emails will be processed.",
                )
            )
            logger.error(
                get_agent_logger(
                    "CLI", "Exiting: No valid email IDs provided with --email-id flag."
                )
            )
            sys.exit(1)
    # else:
    # target_email_ids = None # Process all if flag not used

    # Determine final target_email_ids to pass to run_email_processing
    final_target_email_ids = target_email_ids_list if args.email_id else None

    # Run the main function
    try:
        result = asyncio.run(
            run_email_processing(
                products_source=args.products_source,
                emails_source=args.emails_source,
                output_spreadsheet_id=args.output_gsheet_id,
                processing_limit=limit,
                target_email_ids=final_target_email_ids,  # Pass the processed list of email IDs
                output_dir=output_dir,  # Pass output_dir
                stop_on_error=args.stop_on_error,  # Pass the new flag
            )
        )
        logger.info(get_agent_logger("CLI", f"Final result: {result}"))
    except KeyboardInterrupt:
        logger.info(get_agent_logger("CLI", "\nOperation cancelled by user."))
        sys.exit(1)
    except Exception as e:
        logger.error(
            get_agent_logger("CLI", f"An unexpected error occurred: {e}"), exc_info=True
        )
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
