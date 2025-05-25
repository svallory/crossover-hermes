"""Shared vector store logic for Hermes: always uses persistent ChromaDB in ./chroma_db with a fixed embedding model."""

import os
from typing import Optional

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from hermes.data.load_data import load_products_df

# Vector store config
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "products_catalog"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# Global cache
_vector_store: Optional[Chroma] = None


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
        metadata = {
            "product_id": str(row["product_id"]),
            "name": str(row["name"]),
            "category": str(row["category"]),
            "stock": int(row["stock"]),
            "price": float(row["price"]) if row["price"] else 0.0,
            "season": str(row.get("season", "Spring")),
            "type": str(row.get("type", "")),
            "description": str(row["description"]),
        }
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
