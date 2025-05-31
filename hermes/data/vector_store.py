"""Shared vector store logic for Hermes: always uses persistent ChromaDB in ./chroma_db with a fixed embedding model."""

import os
from typing import Optional, Dict, Any

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from hermes.data.load_data import load_products_df
from hermes.model import ProductCategory, Season
from hermes.model.product import Product
from hermes.utils.logger import logger, get_agent_logger
from hermes.config import HermesConfig


# Global cache
_vector_store: Optional[Chroma] = None


def product_to_metadata(product_row) -> Dict[str, Any]:
    """Convert DataFrame row to vector store metadata format.

    Args:
        product_row: A pandas DataFrame row containing product data.

    Returns:
        Dictionary with standardized metadata format for vector store.
    """
    return {
        "product_id": str(product_row["product_id"]),
        "name": str(product_row["name"]),
        "category": str(product_row["category"]),
        "stock": int(product_row["stock"]),
        "price": float(product_row["price"]) if product_row["price"] else 0.0,
        "season": str(product_row.get("season", "Spring")),
        "type": str(product_row.get("type", "")),
        "description": str(product_row["description"]),
    }


def metadata_to_product(metadata: Dict[str, Any]) -> Product:
    """Convert vector store metadata back to Product model.

    Args:
        metadata: Dictionary containing product metadata from vector store.

    Returns:
        Product object with all fields properly typed and validated.
    """
    # Handle seasons
    seasons = []
    season_data = metadata.get("season")  # No default like "Spring" if key is missing

    if (
        isinstance(season_data, str) and season_data.strip()
    ):  # Process only if it's a non-empty string
        season_values = season_data.split(",")
        for s_val_raw in season_values:
            s_val = s_val_raw.strip()
            if not s_val:  # Skip empty strings that might result from "Spring,,Summer"
                continue

            # Attempt direct conversion for other seasons like "Spring", "Summer", "Winter"
            # This assumes s_val matches the enum value string exactly (e.g. "Spring")
            try:
                seasons.append(Season(s_val))
            except ValueError:
                # If a season string is provided but is not valid and not handled above,
                # it's an error in the data.
                raise ValueError(
                    f"Invalid season value '{s_val}' found in metadata for product ID '{metadata.get('product_id', 'Unknown')}'. "
                    f"Expected one of: {', '.join([e.value for e in Season])} (case-sensitive for non-mapped values), "
                    f"or 'all seasons'/'fall'/'autumn' (case-insensitive)."
                )

    # The 'seasons' list will be empty if 'season_data' was None, an empty string,
    # or contained only empty strings after splitting. This is not a default.
    # If the Product model requires seasons to be non-empty, Pydantic validation will catch it.

    return Product(
        product_id=str(metadata["product_id"]),
        name=str(metadata["name"]),
        category=ProductCategory(str(metadata["category"])),
        stock=int(metadata["stock"]),
        description=str(metadata["description"]),
        product_type=str(metadata.get("type", "")),
        price=float(metadata["price"]),
        seasons=seasons,
        metadata=None,  # Simple string format, None by default
    )


def get_vector_store(config: HermesConfig = HermesConfig()) -> Chroma:
    """Get or create the persistent Chroma vector store for the product catalog."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    logger.info(get_agent_logger("Data", "Initializing vector store..."))

    # Ensure persistent directory exists
    os.makedirs(config.chroma_db_path, exist_ok=True)

    # Create embeddings - let OpenAIEmbeddings pick up API key from environment
    # Use default OpenAI API endpoint (no custom base_url)
    embedding_kwargs = {
        "model": config.embedding_model_name,
    }

    embeddings = OpenAIEmbeddings(**embedding_kwargs)

    # Load products
    products_df = load_products_df()
    if products_df is None:
        raise ValueError("Could not load products data")

    # Convert products to LangChain Documents
    documents = []
    for _, row in products_df.iterrows():
        content = f"{row['name']} {row['description']}"
        metadata = product_to_metadata(row)
        documents.append(
            Document(page_content=content, metadata=metadata, id=str(row["product_id"]))
        )

    # Create or load persistent Chroma vector store
    _vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=config.chroma_collection_name,
        persist_directory=config.chroma_db_path,
    )
    logger.info(
        get_agent_logger(
            "Data",
            f"Vector store initialized. Collection '[yellow]{config.chroma_collection_name}[/yellow]' in '[cyan underline]{config.chroma_db_path}[/cyan underline]'. Documents: [yellow]{_vector_store._collection.count()}[/yellow]",
        )
    )
    return _vector_store
