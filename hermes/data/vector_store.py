"""Shared vector store logic for Hermes: always uses persistent ChromaDB in ./chroma_db with a fixed embedding model."""

import os
from typing import Optional, Dict, Any

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from hermes.data.load_data import load_products_df
from hermes.model import ProductCategory, Season
from hermes.model.product import Product

# Vector store config
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "products_catalog"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

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
    season_str = metadata.get("season", "Spring")
    for s in str(season_str).split(","):
        s = s.strip()
        if s:
            if s == "Fall":
                seasons.append(Season.AUTUMN)
            else:
                try:
                    seasons.append(Season(s))
                except ValueError:
                    seasons.append(Season.SPRING)

    if not seasons:
        seasons = [Season.SPRING]

    return Product(
        product_id=str(metadata["product_id"]),
        name=str(metadata["name"]),
        category=ProductCategory(str(metadata["category"])),
        stock=int(metadata["stock"]),
        description=str(metadata["description"]),
        product_type=str(metadata.get("type", "")),
        price=float(metadata["price"]),
        seasons=seasons,
        metadata=None,
    )


def get_vector_store() -> Chroma:
    """Get or create the persistent Chroma vector store for the product catalog."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    # Ensure persistent directory exists
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)

    # Create embeddings
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
    )

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
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DB_DIR,
    )
    return _vector_store
