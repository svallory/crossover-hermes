import pandas as pd  # type: ignore
import os
from chromadb.api.models.Collection import Collection  # type: ignore

from hermes.config import HermesConfig
from hermes.utils.gsheets import read_data_from_gsheet
from hermes.utils.logger import logger, get_agent_logger
from hermes.model.enums import ProductCategory

# Module-level ("global") variables, initialized to None
_products_df: pd.DataFrame | None = None
vector_store: Collection | None = None

input_spreadsheet_id = HermesConfig().input_spreadsheet_id


def _parse_data_source(
    source: str, default_sheet_name: str
) -> tuple[str | None, str | None, str | None]:
    """Parses a data source string.

    Args:
        source: The source string (e.g., "gsheet_id#sheet_name", "path/to/file.csv").
        default_sheet_name: The default sheet name to use if parsing a GSheet ID without a sheet name.

    Returns:
        A tuple (gsheet_id, sheet_name, file_path).
        - If GSheet: (gsheet_id, actual_sheet_name, None)
        - If file: (None, None, file_path) (file_path is assumed to be a CSV)
    """
    if "#" in source:
        gsheet_id, sheet_name = source.split("#", 1)
        return gsheet_id, sheet_name, None
    elif os.path.exists(source):
        return None, None, source
    else:
        # Default to assuming it's a GSheet ID using the default_sheet_name
        logger.warning(
            get_agent_logger(
                "Data",
                f"Source '[cyan underline]{source}[/cyan underline]' not found as a local file and does not contain '#'. "
                f"Assuming it is a Google Sheet ID for the sheet '[yellow]{default_sheet_name}[/yellow]'.",
            )
        )
        return source, default_sheet_name, None


def load_emails_df(
    source: str = f"{input_spreadsheet_id}#emails", default_sheet_name: str = "emails"
) -> pd.DataFrame:
    """Loads the emails DataFrame from a specified source (Google Sheet or local CSV file)."""
    gsheet_id, sheet_name, file_path = _parse_data_source(source, default_sheet_name)

    if file_path:
        logger.info(
            get_agent_logger(
                "Data",
                f"Loading emails from local file: [cyan underline]{file_path}[/cyan underline] (assuming CSV format)",
            )
        )
        return pd.read_csv(file_path)
    elif gsheet_id and sheet_name:
        logger.info(
            get_agent_logger(
                "Data",
                f"Loading emails from spreadsheet ID: [cyan underline]{gsheet_id}[/cyan underline], sheet: [yellow]{sheet_name}[/yellow]",
            )
        )
        return read_data_from_gsheet(gsheet_id, sheet_name)
    else:
        error_msg = f"Invalid email data source: {source}"
        logger.error(get_agent_logger("Data", error_msg))
        raise ValueError(error_msg)


def load_products_df(
    source: str = f"{input_spreadsheet_id}#products",
    default_sheet_name: str = "products",
) -> pd.DataFrame:
    """Loads the products DataFrame from a specified source (Google Sheet or local CSV file) with memoization.

    Args:
        source: The source string (e.g., "gsheet_id#sheet_name", "path/to/file.csv").
        default_sheet_name: The default sheet name if source is a GSheet ID without a sheet name.

    Returns:
        DataFrame with product data
    """
    global _products_df

    if _products_df is None:
        gsheet_id, sheet_name, file_path = _parse_data_source(
            source, default_sheet_name
        )

        if file_path:
            logger.info(
                get_agent_logger(
                    "Data",
                    f"Loading products from local file: [cyan underline]{file_path}[/cyan underline] (assuming CSV format)",
                )
            )
            _products_df = pd.read_csv(file_path)
        elif gsheet_id and sheet_name:
            logger.info(
                get_agent_logger(
                    "Data",
                    f"Loading products from spreadsheet ID: [cyan underline]{gsheet_id}[/cyan underline], sheet: [yellow]{sheet_name}[/yellow]",
                )
            )
            _products_df = read_data_from_gsheet(gsheet_id, sheet_name)
        else:
            # This case should ideally not be reached
            error_msg = f"Invalid product data source: {source}"
            logger.error(get_agent_logger("Data", error_msg))
            raise ValueError(error_msg)

        if _products_df is not None:
            # Normalize category names using regex for specific known issues
            if "category" in _products_df.columns:
                # quick fix for known issue with kids clothing category
                _products_df["category"] = (
                    _products_df["category"].astype(str).str.strip()
                )
                _products_df["category"] = _products_df["category"].str.replace(
                    r"(?i)Kid(s)?\s*['’]?\s*Clothing",
                    ProductCategory.KIDS_CLOTHING.value,
                    regex=True,
                )
            else:
                logger.warning(
                    get_agent_logger(
                        "Data",
                        "Column 'category' not found in products DataFrame. Skipping normalization.",
                    )
                )
            logger.info(
                get_agent_logger(
                    "Data",
                    f"Loaded and normalized [yellow]{len(_products_df)}[/yellow] products",
                )
            )

    return _products_df
