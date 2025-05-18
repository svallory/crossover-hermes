from os import getenv
import os
import pandas as pd
from typing import Optional, Any
import chromadb
from .vector_store import create_vector_store, create_openai_embedding_function

# Since we're using OpenAI embeddings exclusively, we don't need to set this
# os.environ["TOKENIZERS_PARALLELISM"] = "false"

INPUT_SPREADSHEET_ID_DEFAULT = "14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U"

# Module-level ("global") variables, initialized to None
products_df: Optional[pd.DataFrame] = None
vector_store: Optional[chromadb.Collection] = None
# emails_df can also be made global here if widely needed, or loaded specifically by main.py


def read_data_from_gsheet(document_id: str, sheet_name: str) -> pd.DataFrame:
    """Reads a sheet from a Google Spreadsheet into a pandas DataFrame."""
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(export_link)
        print(f"Successfully read {len(df)} rows from sheet: {sheet_name}")
        return df
    except Exception as e:
        print(
            f"Error reading Google Sheet {sheet_name} from document {document_id}: {e}"
        )
        return None


def load_emails_df(spreadsheet_id: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Loads the emails DataFrame from Google Sheets. Can be called by main.py or notebook."""
    sid = spreadsheet_id or getenv("INPUT_SPREADSHEET_ID", INPUT_SPREADSHEET_ID_DEFAULT)
    if not sid:
        print(
            "Error: INPUT_SPREADSHEET_ID is not set in .env or passed as an argument for emails."
        )
        return None
    print(f"Loading emails from spreadsheet ID: {sid}, sheet: emails")
    df = read_data_from_gsheet(sid, "emails")
    if df is None:
        print(f"Failed to load emails_df from GSheet ID {sid}, sheet 'emails'.")
    return df


def initialize_data_and_vector_store(
    spreadsheet_id: Optional[str] = None,
    collection_name: Optional[str] = None,
    embedding_function: Optional[Any] = None,
    openai_api_key: str = None,
    openai_base_url: Optional[str] = None,
    openai_embedding_model: str = "text-embedding-3-small",
) -> bool:
    """
    Initializes the global products_df and vector_store.
    This function should be called once by the main script (e.g., main.py or a notebook cell).

    Args:
        spreadsheet_id: The Google Spreadsheet ID for input data.
        collection_name: Name for the ChromaDB collection.
        embedding_function: Optional custom embedding function for ChromaDB.
        openai_api_key: OpenAI API key for embeddings (required unless embedding_function is provided).
        openai_base_url: Optional base URL for OpenAI API (useful for assignment's custom endpoint).
        openai_embedding_model: The OpenAI embedding model to use (defaults to "text-embedding-3-small").

    Returns:
        True if initialization was successful, False otherwise.

    Raises:
        ValueError: If OpenAI API key is missing and no embedding function is provided.
    """
    global products_df, vector_store  # Declare intent to modify module-level globals

    print("Initializing global product data and vector store...")

    # Verify required OpenAI credentials
    if embedding_function is None and not openai_api_key:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OpenAI API key is required. Provide it as an argument or set OPENAI_API_KEY environment variable."
            )

    # Load products_df directly
    sid_products = spreadsheet_id or getenv(
        "INPUT_SPREADSHEET_ID", INPUT_SPREADSHEET_ID_DEFAULT
    )
    if not sid_products:
        print(
            "Error: INPUT_SPREADSHEET_ID is not set in .env or passed as an argument for products."
        )
        return False
    print(
        f"Loading products from spreadsheet ID: {sid_products}, sheet: products for global init"
    )
    loaded_products_df = read_data_from_gsheet(sid_products, "products")

    if loaded_products_df is None:
        print("Failed to load products_df. Global data initialization aborted.")
        return False
    products_df = loaded_products_df  # Assign to global
    print(f"Global products_df initialized with {len(products_df)} products.")

    # Create vector store
    effective_collection_name = collection_name or getenv(
        "CHROMA_COLLECTION_NAME", "hermes_product_catalog"
    )
    print(f"Creating vector store with collection name: {effective_collection_name}")

    try:
        if products_df is not None:
            # Create embedding function if none provided
            if embedding_function is None:
                print(
                    f"Creating OpenAI embedding function with model: {openai_embedding_model}"
                )
                embedding_function = create_openai_embedding_function(
                    model_name=openai_embedding_model,
                    api_key=openai_api_key,
                    base_url=openai_base_url,
                )
                print("Successfully created OpenAI embedding function")

            vs = create_vector_store(
                products_df=products_df,  # Use the global one
                collection_name=effective_collection_name,
                embedding_function=embedding_function,
            )
            if vs:
                vector_store = vs  # Assign to global
                print("Global vector_store initialized successfully.")
                return True
            else:
                print(
                    "Failed to create vector store (create_vector_store returned None)."
                )
                return False
        else:
            print(
                "products_df is None after attempting load, cannot create vector store."
            )
            return False

    except Exception as e:
        print(f"Error creating vector store: {e}")
        return False


# Example of how to potentially expose emails_df globally if desired:
# emails_df: Optional[pd.DataFrame] = None
# def initialize_emails_data(spreadsheet_id: Optional[str] = None) -> bool:
#     global emails_df
#     loaded_emails_df = load_emails_df(spreadsheet_id)
#     if loaded_emails_df is not None:
#         emails_df = loaded_emails_df
#         print(f"Global emails_df initialized with {len(emails_df)} emails.")
#         return True
#     return False
