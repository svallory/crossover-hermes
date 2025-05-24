"""Unit tests for the vector store module."""

import pytest
from unittest.mock import patch, MagicMock

from hermes.config import HermesConfig
from hermes.data.vector_store import VectorStore, IN_MEMORY_SENTINEL
from hermes.model.vector import ProductSearchQuery, SimilarProductQuery, ProductSearchResult


@pytest.fixture
def mock_collection():
    """Create a mock ChromaDB collection."""
    mock = MagicMock()
    mock.count.return_value = 10

    # Mock query responses
    mock.query.return_value = {
        "ids": [["product1", "product2"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[
            {
                "product_id": "product1",
                "name": "Test Product 1",
                "description": "A test product description",
                "category": "Men's Clothing",
                "product_type": "Shirt",
                "stock": "10",
                "seasons": "Spring,Summer",
                "price": "29.99"
            },
            {
                "product_id": "product2",
                "name": "Test Product 2",
                "description": "Another test product",
                "category": "Women's Clothing",
                "product_type": "Dress",
                "stock": "5",
                "seasons": "Summer",
                "price": "49.99"
            }
        ]]
    }

    # Mock get response for similar product search
    mock.get.return_value = {
        "ids": ["product1"],
        "embeddings": [[0.1, 0.2, 0.3]],
        "metadatas": [{
            "product_id": "product1",
            "name": "Test Product 1",
            "description": "A test product description",
            "category": "Men's Clothing",
            "product_type": "Shirt",
            "stock": "10",
            "seasons": "Spring,Summer",
            "price": "29.99"
        }]
    }

    return mock


@pytest.fixture
def vector_store(mock_collection):
    """Create a VectorStore instance with a mock collection."""
    with patch.object(VectorStore, '_collection', mock_collection):
        vector_store = VectorStore(HermesConfig(vector_store_path=IN_MEMORY_SENTINEL))
        yield vector_store


def test_search_products_by_description(vector_store, mock_collection):
    """Test searching products by description."""
    # Create a search query
    query = ProductSearchQuery(
        query_text="blue shirt",
        n_results=5,
        filter_criteria={"category": "Men's Clothing"}
    )

    # Perform the search
    results = vector_store.search_products_by_description(query)

    # Verify mock was called correctly
    mock_collection.query.assert_called_once_with(
        query_texts=["blue shirt"],
        n_results=5,
        where={"category": "Men's Clothing"}
    )

    # Check results
    assert len(results) == 2
    assert results[0].product_id == "product1"
    assert results[0].name == "Test Product 1"
    assert results[1].product_id == "product2"
    assert results[1].name == "Test Product 2"


def test_find_similar_products(vector_store, mock_collection):
    """Test finding similar products."""
    # Create a similar product query
    query = SimilarProductQuery(
        product_id="product1",
        n_results=3,
        exclude_reference=True
    )

    # Perform the search
    results = vector_store.find_similar_products(query)

    # Verify mocks were called correctly
    mock_collection.get.assert_called_once_with(
        ids=["product1"],
        include=["embeddings", "metadatas"]
    )

    mock_collection.query.assert_called_with(
        query_embeddings=[[0.1, 0.2, 0.3]],
        n_results=4,  # n_results + 1 because exclude_reference=True
        where=None
    )

    # Only 1 product should be returned since we exclude the reference
    assert len(results) <= 3


def test_similarity_search_with_score(vector_store, mock_collection):
    """Test similarity search with score."""
    # Create a search query
    query = ProductSearchQuery(
        query_text="summer dress",
        n_results=5
    )

    # Perform the search
    results = vector_store.similarity_search_with_score(query)

    # Verify mock was called correctly
    mock_collection.query.assert_called_with(
        query_texts=["summer dress"],
        n_results=5,
        where=None
    )

    # Check results
    assert len(results) == 2
    assert isinstance(results[0], ProductSearchResult)
    assert results[0].product_id == "product1"
    assert results[0].product_name == "Test Product 1"
    assert results[0].similarity_score == 0.9  # 1.0 - 0.1
    assert results[1].product_id == "product2"
    assert results[1].product_name == "Test Product 2"
    assert results[1].similarity_score == 0.8  # 1.0 - 0.2

    # Results should be sorted by similarity score
    assert results[0].similarity_score > results[1].similarity_score