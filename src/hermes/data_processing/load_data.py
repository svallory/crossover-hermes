import pandas as pd  # type: ignore
from typing import Optional
from chromadb.api.models.Collection import Collection
from src.hermes.config import HermesConfig


# Use the default from config instead of duplicating it
INPUT_SPREADSHEET_ID_DEFAULT = HermesConfig().input_spreadsheet_id

# Module-level ("global") variables, initialized to None
_products_df: Optional[pd.DataFrame] = None
vector_store: Optional[Collection] = None
# emails_df can also be made global here if widely needed, or loaded specifically by main.py


def read_data_from_gsheet(document_id: str, sheet_name: str) -> pd.DataFrame:
    """Reads a sheet from a Google Spreadsheet into a pandas DataFrame."""
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(export_link)
    print(f"Successfully read {len(df)} rows from sheet: {sheet_name}")
    return df


def load_emails_df(spreadsheet_id: str = INPUT_SPREADSHEET_ID_DEFAULT) -> pd.DataFrame:
    """Loads the emails DataFrame from Google Sheets."""
    print(f"Loading emails from spreadsheet ID: {spreadsheet_id}, sheet: emails")
    return read_data_from_gsheet(spreadsheet_id, "emails")


def load_products_df(spreadsheet_id: str = INPUT_SPREADSHEET_ID_DEFAULT) -> pd.DataFrame:
    """
    Loads the products DataFrame from Google Sheets with memoization.

    Args:
        spreadsheet_id: The Google Spreadsheet ID

    Returns:
        DataFrame with product data
    """
    global _products_df

    if _products_df is None:
        print(f"Loading products from spreadsheet ID: {spreadsheet_id}")
        _products_df = read_data_from_gsheet(spreadsheet_id, "products")
        print(f"Loaded {len(_products_df)} products")

    return _products_df
