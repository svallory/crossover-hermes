from os import getenv
import os
import pandas as pd  # type: ignore
from typing import Optional, Any
import asyncio
import chromadb
from .vector_store import create_vector_store, create_openai_embedding_function

# Since we're using OpenAI embeddings exclusively, we don't need to set this
# os.environ["TOKENIZERS_PARALLELISM"] = "false"

INPUT_SPREADSHEET_ID_DEFAULT = "14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U"

# Module-level ("global") variables, initialized to None
products_df: Optional[pd.DataFrame] = None
vector_store: Optional[chromadb.Collection] = None
# emails_df can also be made global here if widely needed, or loaded specifically by main.py


async def read_data_from_gsheet(document_id: str, sheet_name: str) -> pd.DataFrame:
    """Reads a sheet from a Google Spreadsheet into a pandas DataFrame."""
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = await asyncio.to_thread(pd.read_csv, export_link)
    print(f"Successfully read {len(df)} rows from sheet: {sheet_name}")
    return df


async def load_emails_df(spreadsheet_id: str = INPUT_SPREADSHEET_ID_DEFAULT) -> pd.DataFrame:
    """Loads the emails DataFrame from Google Sheets."""
    print(f"Loading emails from spreadsheet ID: {spreadsheet_id}, sheet: emails")
    return await read_data_from_gsheet(spreadsheet_id, "emails")


async def initialize_data_and_vector_store(
    spreadsheet_id: str = INPUT_SPREADSHEET_ID_DEFAULT,
    collection_name: str = "hermes_product_catalog",
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    openai_embedding_model: str = "text-embedding-3-small",
) -> bool:
    """Initializes the global products_df and vector store."""
    global products_df, vector_store
    print("Initializing global product data and vector store...")

    # Determine OpenAI API key
    current_openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    
    # Try to load existing vector store
    chroma_db_path = "./chroma_db"
    if os.path.exists(chroma_db_path) and os.path.isdir(chroma_db_path):
        print(f"Found existing vector store directory. Attempting to load.")
        try:
            # Create embedding function for loading
            ef_for_loading = create_openai_embedding_function(
                model_name=openai_embedding_model,
                api_key=current_openai_api_key,
                base_url=openai_base_url,
            )

            # Load the vector store
            from .vector_store import load_vector_store
            loaded_vs = await load_vector_store(
                collection_name=collection_name,
                embedding_function=ef_for_loading,
                api_key=current_openai_api_key,
                base_url=openai_base_url,
                model_name=openai_embedding_model,
                storage_path=chroma_db_path,
            )

            if loaded_vs and loaded_vs.count() > 0:
                vector_store = loaded_vs
                print(f"Successfully loaded existing vector store with {vector_store.count()} items.")
                
                # Load products_df even if vector store was loaded
                print(f"Loading products_df from spreadsheet ID: {spreadsheet_id}")
                products_df = await read_data_from_gsheet(spreadsheet_id, "products")
                print(f"Global products_df initialized with {len(products_df)} products.")
                return True
        except Exception as e:
            print(f"Error loading existing vector store: {e}. Creating a new one.")

    # Load products_df and create a new vector store
    print(f"Loading products from spreadsheet ID: {spreadsheet_id}")
    products_df = await read_data_from_gsheet(spreadsheet_id, "products")
    print(f"Global products_df initialized with {len(products_df)} products.")

    # Create embedding function
    embedding_function = create_openai_embedding_function(
        model_name=openai_embedding_model,
        api_key=current_openai_api_key,
        base_url=openai_base_url,
    )

    # Create the vector store
    vector_store = await create_vector_store(
        products_df=products_df,
        collection_name=collection_name,
        embedding_function=embedding_function,
    )
    
    print("Global vector_store initialized successfully.")
    return True