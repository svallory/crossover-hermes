""" {cell}
## Vector Store Implementation

This module implements the vector store functionality using ChromaDB and OpenAI embeddings.
It's a critical component for enabling Retrieval-Augmented Generation (RAG) capabilities
in our product inquiry handling flow. The vector store allows us to search through
large product catalogs (100,000+ items) using semantic similarity rather than
exact keyword matching.

Key functionalities include:
- Creating embeddings for product descriptions
- Storing product vectors in ChromaDB
- Performing similarity searches with filtering
- Optimizing for large catalog processing through batching
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Helper function to create document from product row
def _create_product_document(row):
    """
    Create a Document from a product catalog row.
    
    Args:
        row: A pandas Series representing a row in the product catalog
        
    Returns:
        A Document object with product content and metadata
    """
    # Construct a rich text representation of the product
    content = f"Product: {row['name']}\nID: {row['product ID']}\nCategory: {row['category']}\n"
    
    if 'description' in row and pd.notna(row['description']):
        content += f"Description: {row['description']}\n"
    
    if 'season' in row and pd.notna(row['season']):
        content += f"Season: {row['season']}\n"
    
    # Create metadata for filtering
    metadata = {
        "product_id": row['product ID'],
        "category": row['category'],
        "name": row['name'],
    }
    
    # Add optional metadata if available
    if 'season' in row and pd.notna(row['season']):
        metadata["season"] = row['season']
    
    if 'stock amount' in row and pd.notna(row['stock amount']):
        metadata["stock_available"] = int(row['stock amount']) > 0
    
    # Create the document
    return Document(
        page_content=content,
        metadata=metadata
    )

# Helper function to determine embedding dimensions based on model name
def _get_embedding_dimensions(model_name: str) -> int:
    """
    Determine the appropriate embedding dimensions based on the model name.
    
    Args:
        model_name: The name of the embedding model
        
    Returns:
        The appropriate dimension for the embeddings
    """
    # Map of known models to their dimensions
    dimension_map = {
        "text-embedding-ada-002": 1536,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
    }
    
    # Return the dimension if known, otherwise default to 1536
    return dimension_map.get(model_name, 1536)

def create_product_vectorstore(product_catalog_df: pd.DataFrame, 
                               embedding_model_name: str = "text-embedding-ada-002",
                               chroma_persist_directory: str = "./chroma_db",
                               collection_name: str = "hermes_product_catalog") -> Chroma:
    """
    Create a ChromaDB vector store from product catalog data.
    
    Args:
        product_catalog_df: DataFrame containing product catalog data
        embedding_model_name: Name of the OpenAI embedding model to use
        chroma_persist_directory: Directory for ChromaDB to persist data
        collection_name: Name for the ChromaDB collection
        
    Returns:
        A ChromaDB vector store instance
    """
    print(f"Creating vector store with {len(product_catalog_df)} products...")
    
    # Initialize the embedding function with dimensions based on model
    embedding_dimensions = _get_embedding_dimensions(embedding_model_name)
    embedding_function = OpenAIEmbeddings(
        model=embedding_model_name,
        dimensions=embedding_dimensions
    )
    
    # Create documents from product data
    documents = []
    
    for _, row in product_catalog_df.iterrows():
        documents.append(_create_product_document(row))
    
    # Create the vector store
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embedding_function,
        persist_directory=chroma_persist_directory,
        collection_name=collection_name
    )
    
    # Persist to disk
    vector_store.persist()
    
    print(f"Vector store created successfully with {len(documents)} documents")
    return vector_store

def create_product_vectorstore_batched(product_catalog_df: pd.DataFrame, 
                                      embedding_model_name: str = "text-embedding-ada-002",
                                      chroma_persist_directory: str = "./chroma_db",
                                      collection_name: str = "hermes_product_catalog",
                                      batch_size: int = 100) -> Chroma:
    """
    Create a ChromaDB vector store from product catalog data using batched processing.
    This is more efficient for large catalogs (100,000+ products).
    
    Args:
        product_catalog_df: DataFrame containing product catalog data
        embedding_model_name: Name of the OpenAI embedding model to use
        chroma_persist_directory: Directory for ChromaDB to persist data
        collection_name: Name for the ChromaDB collection
        batch_size: Number of products to process in each batch
        
    Returns:
        A ChromaDB vector store instance
    """
    print(f"Creating vector store with {len(product_catalog_df)} products in batches of {batch_size}...")
    
    # Initialize the embedding function with dimensions based on model
    embedding_dimensions = _get_embedding_dimensions(embedding_model_name)
    embedding_function = OpenAIEmbeddings(
        model=embedding_model_name,
        dimensions=embedding_dimensions
    )
    
    # Initialize vector store
    vector_store = Chroma(
        embedding_function=embedding_function,
        persist_directory=chroma_persist_directory,
        collection_name=collection_name
    )
    
    # Process in batches
    total_rows = len(product_catalog_df)
    num_batches = (total_rows + batch_size - 1) // batch_size  # Ceiling division
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_rows)
        
        batch_df = product_catalog_df.iloc[start_idx:end_idx]
        
        print(f"Processing batch {batch_num + 1}/{num_batches} (rows {start_idx} to {end_idx - 1})...")
        
        # Create documents from the batch
        documents = []
        
        for _, row in batch_df.iterrows():
            documents.append(_create_product_document(row))
        
        # Add batch to vector store
        vector_store.add_documents(documents)
        
        # Persist after each batch to avoid losing progress
        vector_store.persist()
    
    print(f"Vector store created successfully with {total_rows} documents")
    return vector_store

def query_product_vectorstore(query: str, 
                            vector_store: Chroma, 
                            top_k: int = 5,
                            category_filter: Optional[str] = None) -> List[Document]:
    """
    Query the product vector store with a natural language query.
    
    Args:
        query: The natural language query to search for
        vector_store: The ChromaDB vector store instance
        top_k: Number of top results to return
        category_filter: Optional category filter to narrow down results
        
    Returns:
        List of Document objects containing matching products
    """
    # Create metadata filter if category is specified
    filter_dict = None
    if category_filter:
        filter_dict = {"category": category_filter}
    
    # Perform similarity search
    results = vector_store.similarity_search(
        query=query,
        k=top_k,
        filter=filter_dict
    )
    
    return results

def similarity_search_with_relevance_scores(query: str,
                                          vector_store: Chroma,
                                          top_k: int = 5,
                                          category_filter: Optional[str] = None,
                                          similarity_threshold: float = 0.7) -> List[tuple]:
    """
    Query the product vector store and return documents with their relevance scores.
    
    Args:
        query: The natural language query to search for
        vector_store: The ChromaDB vector store instance
        top_k: Number of top results to return
        category_filter: Optional category filter to narrow down results
        similarity_threshold: Minimum similarity score threshold
        
    Returns:
        List of tuples containing (Document, score)
    """
    # Create metadata filter if category is specified
    filter_dict = None
    if category_filter:
        filter_dict = {"category": category_filter}
    
    # Perform similarity search with scores
    results = vector_store.similarity_search_with_score(
        query=query,
        k=top_k,
        filter=filter_dict
    )
    
    # Filter by similarity threshold
    filtered_results = [(doc, score) for doc, score in results if score >= similarity_threshold]
    
    return filtered_results

def load_product_vectorstore(chroma_persist_directory: str = "./chroma_db",
                           collection_name: str = "hermes_product_catalog",
                           embedding_model_name: str = "text-embedding-ada-002") -> Chroma:
    """
    Load an existing ChromaDB vector store from disk.
    
    Args:
        chroma_persist_directory: Directory where ChromaDB data is persisted
        collection_name: Name of the ChromaDB collection
        embedding_model_name: Name of the OpenAI embedding model to use
        
    Returns:
        A ChromaDB vector store instance
    """
    # Initialize the embedding function with dimensions based on model
    embedding_dimensions = _get_embedding_dimensions(embedding_model_name)
    embedding_function = OpenAIEmbeddings(
        model=embedding_model_name,
        dimensions=embedding_dimensions
    )
    
    # Load the vector store
    vector_store = Chroma(
        persist_directory=chroma_persist_directory,
        embedding_function=embedding_function,
        collection_name=collection_name
    )
    
    return vector_store
""" {cell}
### Vector Store Implementation Notes

The vector store implementation enables efficient semantic search over large product catalogs, a key requirement for handling product inquiries. Key design features include:

1. **Rich Document Representation**:
   - Each product is encoded as a structured document with its name, ID, category, and description
   - Including this rich context improves semantic matching quality
   - Metadata fields enable efficient filtering

2. **Performance Optimization**:
   - The `create_product_vectorstore_batched` function processes products in batches
   - This allows handling of very large catalogs (100,000+ products) without memory issues
   - Progress tracking and persistence after each batch prevents data loss

3. **Flexible Search Options**:
   - Category-based pre-filtering to narrow search space before semantic matching
   - Similarity threshold filtering to exclude low-relevance matches
   - Option to return relevance scores for confidence-based decision making

4. **Persistence and Reusability**:
   - Stores vectors on disk to avoid recomputing embeddings
   - Provides functions for loading existing vector stores
   - Configurable paths and collection names for different environments

This implementation gives us the RAG capabilities needed to scale product inquiries from small to enterprise-level catalogs while maintaining fast response times. The category pre-filtering is especially important as catalog size grows, as it dramatically reduces the vector search space.
""" 