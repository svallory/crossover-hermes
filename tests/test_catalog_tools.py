"""Tests for catalog_tools.py."""

import json
import unittest
from unittest.mock import patch, MagicMock

from hermes.tools.catalog_tools import (
    find_product_by_id,
    find_product_by_name,
    search_products_by_description,
    find_related_products,
    resolve_product_reference,
    filtered_product_search,
)
from hermes.model.product import Product, ProductCategory, Season
from hermes.model.errors import ProductNotFound

from tests.fixtures.mock_product_catalog import get_mock_products_df, mock_vector_store_search
from tests.fixtures.test_product_catalog import (
    get_test_products_df,
    get_product_by_id,
    get_products_matching_description
)


class TestCatalogTools(unittest.TestCase):
    """Tests for the catalog_tools module using mock data."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_valid(self, mock_load_df):
        """Test finding a product by a valid ID."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = find_product_by_id.invoke('{"product_id": "TST001"}')
        
        # Verify result
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "TST001")
        self.assertEqual(result.name, "Test Shirt")
        self.assertEqual(result.category, ProductCategory.SHIRTS)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_invalid(self, mock_load_df):
        """Test finding a product with invalid ID."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = find_product_by_id.invoke('{"product_id": "NONEXISTENT"}')
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)
        self.assertIn("not found", result.message)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_invalid_input(self, mock_load_df):
        """Test finding a product with invalid JSON input."""
        # No mock needed for dataframe access since it should fail before that
        
        # Call function with invalid JSON
        result = find_product_by_id.invoke("not a json")
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)
        self.assertIn("Invalid input format", result.message)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_name_valid(self, mock_load_df):
        """Test finding a product by name with valid match."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function with exact match
        result = find_product_by_name.invoke("Test Shirt")
        
        # Verify result - should match both "Test Shirt" products in mock data
        self.assertIsInstance(result, list)
        # Both "Test Shirt" and "Test Shirt Blue" will match "Test Shirt" 
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0].matched_product.name, "Test Shirt")
        self.assertGreater(result[0].similarity_score, 0.9)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_name_no_match(self, mock_load_df):
        """Test finding a product by name with no match."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function with high threshold to force no matches
        result = find_product_by_name.invoke("Nonexistent Product", threshold=0.99)
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.VectorStore")
    def test_search_products_by_description_valid(self, mock_vector_store):
        """Test searching products by description with valid query."""
        # Setup mock
        mock_instance = mock_vector_store.return_value
        mock_instance.search_products_by_description.return_value = mock_vector_store_search("comfortable", 2)
        
        # Call function
        result = search_products_by_description.invoke('{"query": "comfortable", "top_k": 2}')
        
        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)  # Only one product has "comfortable" in description
        self.assertEqual(result[0].product_id, "TST001")

    @patch("hermes.tools.catalog_tools.VectorStore")
    def test_search_products_by_description_no_match(self, mock_vector_store):
        """Test searching products by description with no matches."""
        # Setup mock
        mock_instance = mock_vector_store.return_value
        mock_instance.search_products_by_description.return_value = []
        
        # Call function
        result = search_products_by_description.invoke('{"query": "nonexistent term"}')
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_related_products_valid(self, mock_load_df, mock_find_product):
        """Test finding related products with valid product ID."""
        # Setup mocks
        mock_load_df.return_value = get_mock_products_df()
        
        # Create a mock product to return
        mock_product = MagicMock(spec=Product)
        mock_product.category = ProductCategory.SHIRTS
        mock_product.price = 29.99
        mock_find_product.return_value = mock_product
        
        # Call function
        result = find_related_products.invoke('{"product_id": "TST001", "relationship_type": "alternative", "limit": 2}')
        
        # Verify result
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    def test_find_related_products_invalid_product(self, mock_find_product):
        """Test finding related products with invalid product ID."""
        # Setup mock
        mock_find_product.return_value = ProductNotFound(message="Product not found")
        
        # Call function
        result = find_related_products.invoke('{"product_id": "NONEXISTENT"}')
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.VectorStore")
    def test_resolve_product_reference_valid(self, mock_vector_store):
        """Test resolving product reference with valid query."""
        # Setup mock
        mock_instance = mock_vector_store.return_value
        mock_instance.search_products_by_description.return_value = [
            Product(
                product_id="TST001",
                name="Test Shirt",
                description="A comfortable cotton test shirt for any occasion.",
                category=ProductCategory.SHIRTS,
                stock=10,
                price=29.99,
                product_type="",
                seasons=[Season.SPRING, Season.SUMMER],
                metadata=None
            )
        ]
        
        # Call function
        result = resolve_product_reference.invoke('{"query": "comfortable shirt"}')
        
        # Verify result
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "TST001")

    @patch("hermes.tools.catalog_tools.VectorStore")
    def test_resolve_product_reference_no_match(self, mock_vector_store):
        """Test resolving product reference with no match."""
        # Setup mock
        mock_instance = mock_vector_store.return_value
        mock_instance.search_products_by_description.return_value = []
        
        # Call function
        result = resolve_product_reference.invoke('{"query": "nonexistent product"}')
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.VectorStore")
    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_filtered_product_search_description(self, mock_load_df, mock_vector_store):
        """Test filtered product search using description search."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        mock_instance = mock_vector_store.return_value
        mock_instance.search_products_by_description.return_value = mock_vector_store_search("comfortable", 2)
        
        # Call function
        result = filtered_product_search.invoke(input="comfortable", search_type="description", category="Shirts")
        
        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].product_id, "TST001")

    @patch("hermes.tools.catalog_tools.load_products_df")
    @patch("hermes.tools.catalog_tools.VectorStore")
    def test_filtered_product_search_name(self, mock_vector_store, mock_load_df):
        """Test filtered product search using name-based search."""
        # Setup mocks
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function - searching for "Test" should match multiple products in mock data
        result = filtered_product_search.invoke(input="Test", search_type="name", min_stock=1)
        
        # Verify result
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for product in result:
            self.assertGreaterEqual(product.stock, 1)
            self.assertIn("Test", product.name)  # All mock products have "Test" in the name


class TestCatalogToolsWithTestData(unittest.TestCase):
    """Tests for catalog_tools using test product data from CSV."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_with_test_data(self, mock_load_df):
        """Test finding a product by ID with test product data."""
        # Setup mock with test data
        mock_load_df.return_value = get_test_products_df()
        
        # Use a product ID from the test data
        test_product_id = "RSG8901"  # Retro Sunglasses
        
        # Call the tool function using invoke
        result = find_product_by_id.invoke(json.dumps({"product_id": test_product_id}))
        
        # Verify the result is a Product object (tool returns Product directly)
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, test_product_id)
        self.assertEqual(result.name, "Retro Sunglasses")
        self.assertEqual(result.category, ProductCategory.ACCESSORIES)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_not_found_with_test_data(self, mock_load_df):
        """Test finding a product with invalid ID using test data."""
        # Setup mock with test data
        mock_load_df.return_value = get_test_products_df()
        
        # Call with non-existent ID
        result = find_product_by_id.invoke(json.dumps({"product_id": "NONEXISTENT"}))
        
        # Verify the result is a ProductNotFound object
        self.assertIsInstance(result, ProductNotFound)
        self.assertIn("not found", result.message.lower())

    @patch("hermes.tools.catalog_tools.VectorStore")
    def test_search_products_by_description_with_test_data(self, mock_vector_store):
        """Test searching products by description using test data."""
        # Create a mock for the vector store instance
        mock_instance = mock_vector_store.return_value
        
        # Setup mock to return results from our fixture
        mock_instance.search_products_by_description.return_value = get_products_matching_description("leather", 2)
        
        # Call the function using invoke
        result = search_products_by_description.invoke(json.dumps({"query": "leather", "top_k": 2}))
        
        # Verify the result is a list of Product objects
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Verify at least one product has "leather" in its description
        has_leather = any("leather" in p.description.lower() for p in result)
        self.assertTrue(has_leather)

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_related_products_with_test_data(self, mock_load_df, mock_find_product):
        """Test finding related products using test data."""
        # Setup mocks
        mock_load_df.return_value = get_test_products_df()
        
        # Get a test product to use as the reference
        test_product = get_product_by_id("LTH0976")  # Leather Bifold Wallet
        mock_find_product.return_value = test_product
        
        # Call function using invoke
        result = find_related_products.invoke(json.dumps({
            "product_id": "LTH0976", 
            "relationship_type": "complementary", 
            "limit": 2
        }))
        
        # Verify result is a list of products
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    @patch("hermes.tools.catalog_tools.VectorStore")
    def test_resolve_product_reference_with_test_data(self, mock_vector_store):
        """Test resolving a product reference using test data."""
        # Setup mock
        mock_instance = mock_vector_store.return_value
        
        # Get a test product to use
        test_product = get_product_by_id("LTH0976")  # Leather Bifold Wallet
        mock_instance.search_products_by_description.return_value = [test_product]
        
        # Call function using invoke
        result = resolve_product_reference.invoke(json.dumps({
            "query": "leather wallet"
        }))
        
        # Verify result is a Product object
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "LTH0976")


if __name__ == "__main__":
    unittest.main() 