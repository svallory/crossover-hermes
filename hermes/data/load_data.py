import pandas as pd  # type: ignore
import os
from chromadb.api.models.Collection import Collection  # type: ignore

from hermes.config import HermesConfig
from hermes.utils.gsheets import read_data_from_gsheet

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
    elif os.path.exists(
        source
    ):  # If it's a path to an existing file, assume it's a CSV
        return None, None, source
    else:
        # Default to assuming it's a GSheet ID using the default_sheet_name
        print(
            f"Warning: Source '{source}' not found as a local file and does not contain '#'. "
            f"Assuming it is a Google Sheet ID for the sheet '{default_sheet_name}'."
        )
        return source, default_sheet_name, None


def load_emails_df(
    source: str = f"{input_spreadsheet_id}#emails", default_sheet_name: str = "emails"
) -> pd.DataFrame:
    """Loads the emails DataFrame from a specified source (Google Sheet or local CSV file)."""
    gsheet_id, sheet_name, file_path = _parse_data_source(source, default_sheet_name)

    if file_path:
        print(f"Loading emails from local file: {file_path} (assuming CSV format)")
        return pd.read_csv(file_path)
    elif gsheet_id and sheet_name:
        print(f"Loading emails from spreadsheet ID: {gsheet_id}, sheet: {sheet_name}")
        return read_data_from_gsheet(gsheet_id, sheet_name)
    else:
        # This case should ideally not be reached if _parse_data_source is robust
        raise ValueError(f"Invalid email data source: {source}")


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
            print(
                f"Loading products from local file: {file_path} (assuming CSV format)"
            )
            _products_df = pd.read_csv(file_path)
        elif gsheet_id and sheet_name:
            print(
                f"Loading products from spreadsheet ID: {gsheet_id}, sheet: {sheet_name}"
            )
            _products_df = read_data_from_gsheet(gsheet_id, sheet_name)
        else:
            # This case should ideally not be reached
            raise ValueError(f"Invalid product data source: {source}")

        if _products_df is not None:
            print(f"Loaded {len(_products_df)} products")

    return _products_df
