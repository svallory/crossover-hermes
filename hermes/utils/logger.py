import logging
from rich.logging import RichHandler
from rich.console import Console

# Global console for non-logging rich prints if needed
console = Console()


def setup_logging(
    level: str = "INFO", with_time: bool = False, with_path: bool = False
) -> logging.Logger:
    """Configures logging with RichHandler for beautiful and informative output.

    Args:
        level: The logging level (e.g., "INFO", "DEBUG").
        with_time: Whether to show time in logs. Defaults to False.
        with_path: Whether to show the path of the logger. Defaults to False.

    Returns:
        A configured logger instance.
    """
    # Configure the root logger first - this helps if any library initializes its logger before this setup
    logging.basicConfig(
        level=logging.WARNING,  # Set root to WARNING to catch unexpected logs from libs
        handlers=[
            RichHandler(
                show_level=False, show_path=False, show_time=False, rich_tracebacks=True
            )
        ],
    )

    # Get our application's logger
    app_logger = logging.getLogger("hermes")  # Or your main app name
    app_logger.handlers.clear()  # Remove any default handlers it might have inherited
    app_logger.propagate = False  # Prevent passing logs to the root logger

    rich_handler = RichHandler(
        level=level.upper(),
        console=console,  # Use our shared console
        show_time=with_time,
        show_path=with_path,
        show_level=False,  # <--- Key change: Remove INFO prefix
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        markup=True,  # Allow rich markup in log messages
    )
    app_logger.addHandler(rich_handler)
    app_logger.setLevel(level.upper())

    # Silence overly verbose external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.WARNING)

    return app_logger


# Global logger instance for the application
logger = setup_logging()

# Agent-specific logger styling
AGENT_STYLE_MAP = {
    "Default": "[bold magenta]",
    "Workflow": "[bold cyan]",
    "CLI": "[bold green]",
    "Core": "[bold blue]",
    "Data": "[bold yellow]",
    "Utils": "[bold bright_black]",
    "Classifier": "[bold green_yellow]",
    "Stockkeeper": "[bold dark_orange3]",
    "Fulfiller": "[bold dodger_blue1]",
    "Advisor": "[bold hot_pink3]",
    "Composer": "[bold medium_purple1]",
}


def get_agent_logger(agent_name: str, message: str) -> str:
    """Formats a log message with agent-specific styling for the tag only."""
    style = AGENT_STYLE_MAP.get(agent_name, AGENT_STYLE_MAP["Default"])
    # Apply style only to the tag, then reset style for the message itself
    return f"{style}[{agent_name}][/] {message}"
