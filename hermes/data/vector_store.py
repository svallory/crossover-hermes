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
        "price": float(product_row["price"]) if product_row["price"] else 0.0,
        "season": str(product_row.get("seasons"))
        if product_row.get("seasons") is not None
        else None,
        "type": str(product_row.get("type", "")),
        "description": str(product_row["description"]),
    }


def metadata_to_product(metadata: Dict[str, Any]) -> Product:
    """Convert vector store metadata back to Product model, ensuring live stock data.

    Args:
        metadata: Dictionary containing product metadata from vector store.

    Returns:
        Product object with all fields properly typed and validated, including live stock.
    """
    from hermes.tools.catalog_tools import find_product_by_id

    product_id_from_meta = str(metadata["product_id"])
    live_product_data = find_product_by_id.invoke({"product_id": product_id_from_meta})

    # Check by class name to avoid issues with type identity in test environments
    if live_product_data.__class__.__name__ == "ProductNotFound":
        logger.warning(
            get_agent_logger(
                "VectorStore",
                f"Product ID '{product_id_from_meta}' from vector store metadata not found in live catalog via find_product_by_id. Using metadata values with stock 0.",
            )
        )
        seasons_fallback = []
        season_data_fallback = metadata.get("season")
        if isinstance(season_data_fallback, str) and season_data_fallback.strip():
            season_values_fallback = season_data_fallback.split(",")
            for s_val_raw in season_values_fallback:
                s_val = s_val_raw.strip()
                if not s_val:
                    continue
                try:
                    seasons_fallback.append(Season(s_val))
                except ValueError:
                    logger.error(
                        f"Invalid season value '{s_val}' in fallback metadata for '{product_id_from_meta}'."
                    )

        category_val_fallback = ProductCategory.ACCESSORIES
        category_str_fallback = metadata.get("category")
        if category_str_fallback:
            try:
                category_val_fallback = ProductCategory(str(category_str_fallback))
            except ValueError:
                logger.error(
                    f"Invalid category '{category_str_fallback}' in fallback metadata for '{product_id_from_meta}'. Defaulting to ACCESSORIES."
                )

        return Product(
            product_id=product_id_from_meta,
            name=str(metadata.get("name", "Unknown Name")),
            category=category_val_fallback,
            stock=0,
            description=str(metadata.get("description", "No description available.")),
            product_type=str(metadata.get("type", "")),
            price=float(metadata.get("price", 0.0)),
            seasons=seasons_fallback,
            metadata=f"Fallback: Original product ID '{product_id_from_meta}' not found in live catalog.",
        )

    # If we reach here, live_product_data must be a Product.
    # Add an assertion to make this explicit for the type checker.
    assert isinstance(live_product_data, Product)

    # live_product_data is a Product object

    final_name = str(metadata.get("name", live_product_data.name))

    final_category = live_product_data.category
    category_from_meta_str = metadata.get("category")
    if category_from_meta_str:
        try:
            final_category = ProductCategory(str(category_from_meta_str))
        except ValueError:
            logger.error(
                f"Invalid category value '{category_from_meta_str}' in metadata for '{product_id_from_meta}'. Using live product category '{live_product_data.category.value}'."
            )

    final_description = str(metadata.get("description", live_product_data.description))
    final_product_type = str(metadata.get("type", live_product_data.product_type))

    final_seasons = live_product_data.seasons
    season_data_meta = metadata.get("season")
    if isinstance(season_data_meta, str) and season_data_meta.strip():
        temp_seasons_from_meta = []
        parsed_meta_seasons_successfully = True
        season_values_meta = season_data_meta.split(",")
        for s_val_raw in season_values_meta:
            s_val = s_val_raw.strip()
            if not s_val:
                continue
            try:
                temp_seasons_from_meta.append(Season(s_val))
            except ValueError:
                logger.error(
                    f"Invalid season value '{s_val}' in metadata for '{product_id_from_meta}'. Using live product seasons."
                )
                parsed_meta_seasons_successfully = False
                break
        if (
            parsed_meta_seasons_successfully and temp_seasons_from_meta
        ):  # Ensure list is not empty if parsed
            final_seasons = temp_seasons_from_meta
        elif (
            parsed_meta_seasons_successfully
            and not temp_seasons_from_meta
            and season_data_meta
        ):  # Metadata had season string but it parsed to empty (e.g. ",,")
            final_seasons = []  # Explicitly empty if metadata intended that

    return Product(
        product_id=live_product_data.product_id,
        name=final_name,
        category=final_category,
        stock=live_product_data.stock,
        description=final_description,
        product_type=final_product_type,
        price=live_product_data.price,
        seasons=final_seasons,
        promotion=live_product_data.promotion,
        promotion_text=live_product_data.promotion_text,
        metadata=live_product_data.metadata,
    )


def get_vector_store(config: HermesConfig = HermesConfig()) -> Chroma:
    """Get or create the persistent Chroma vector store for the product catalog."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    logger.info(get_agent_logger("Data", "Initializing vector store..."))

    # Ensure persistent directory exists
    os.makedirs(config.chroma_db_path, exist_ok=True)

    embedding_kwargs = {
        "model": config.embedding_model_name,
        "dimensions": config.chroma_embedding_dim,
        "api_key": config.llm_api_key,
        "base_url": config.llm_provider_url
        if config.llm_provider == "OpenAI"
        else None,
    }
    embeddings = OpenAIEmbeddings(**embedding_kwargs)

    # Load or create the Chroma vector store instance
    # This will load if exists, or create a new empty one if it doesn't.
    vector_store_instance = Chroma(
        collection_name=config.chroma_collection_name,
        embedding_function=embeddings,
        persist_directory=config.chroma_db_path,
    )

    doc_count = vector_store_instance._collection.count()

    if doc_count > 0:
        logger.info(
            get_agent_logger(
                "Data",
                f"Loaded existing vector store. Collection '[yellow]{config.chroma_collection_name}[/yellow]' in '[cyan underline]{config.chroma_db_path}[/cyan underline]' already contains [yellow]{doc_count}[/yellow] documents. Skipping re-population.",
            )
        )
    else:
        logger.info(
            get_agent_logger(
                "Data",
                f"Vector store collection '[yellow]{config.chroma_collection_name}[/yellow]' in '[cyan underline]{config.chroma_db_path}[/cyan underline]' is new or empty. Populating with product data...",
            )
        )
        products_df = load_products_df()
        if products_df is None:
            error_msg = "Product DataFrame is None, cannot build vector store."
            logger.error(get_agent_logger("Data", error_msg))
            raise ValueError(error_msg)

        documents = []
        doc_ids = []
        for _, row in products_df.iterrows():
            # Ensure page content is a string, handling potential NaNs from DataFrame
            name_str = str(row.get("name", ""))
            description_str = str(row.get("description", ""))
            content = f"{name_str} {description_str}".strip()

            metadata_for_doc = product_to_metadata(row)
            documents.append(
                Document(
                    page_content=content
                    if content
                    else "No content available",  # Ensure non-empty content
                    metadata=metadata_for_doc,
                )
            )
            doc_ids.append(str(row["product_id"]))

        vector_store_instance.add_documents(documents=documents, ids=doc_ids)
        logger.info(
            get_agent_logger(
                "Data",
                f"Successfully populated vector store. Collection '[yellow]{config.chroma_collection_name}[/yellow]' now contains [yellow]{vector_store_instance._collection.count()}[/yellow] documents.",
            )
        )

    _vector_store = vector_store_instance
    return _vector_store
