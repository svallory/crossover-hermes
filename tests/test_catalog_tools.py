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
    metadata_to_product,
)
from hermes.model.product import Product, ProductCategory, Season
from hermes.model.errors import ProductNotFound

from tests.fixtures.mock_product_catalog import (
    get_mock_products_df,
)
from tests.fixtures.test_product_catalog import (
    get_test_products_df,
    get_product_by_id,
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

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_valid(self, mock_get_vector_store):
        """Test searching products by description with valid query."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock similarity search results
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST001",
            "name": "Test Shirt",
            "category": "Shirts",
            "stock": 10,
            "price": 29.99,
            "season": "Spring",
            "type": "",
            "description": "A comfortable cotton test shirt for any occasion.",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call function
        result = search_products_by_description.invoke(
            '{"query": "comfortable", "top_k": 2}'
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].product_id, "TST001")

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_no_match(self, mock_get_vector_store):
        """Test searching products by description with no matches."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_vector_store.similarity_search.return_value = []

        # Call function
        result = search_products_by_description.invoke('{"query": "nonexistent term"}')

        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_related_products_valid(self, mock_get_vector_store):
        """Test finding related products with valid product ID."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST002",
            "name": "Another Shirt",
            "category": "Shirts",
            "stock": 5,
            "price": 25.99,
            "season": "Spring",
            "type": "",
            "description": "Another test shirt",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Create mock function that behaves like find_product_by_id
        original_find_product = find_product_by_id.func

        def mock_find_product_func(tool_input: str):
            # Parse the input to get the product ID
            import json

            try:
                input_data = json.loads(tool_input)
                product_id = input_data.get("product_id", "")
                if product_id == "TST001":
                    return Product(
                        product_id="TST001",
                        name="Test Shirt",
                        description="A comfortable test shirt",
                        category=ProductCategory.SHIRTS,
                        stock=10,
                        price=29.99,
                        product_type="",
                        seasons=[Season.SPRING],
                        metadata=None,
                    )
                else:
                    return ProductNotFound(message="Product not found")
            except:
                return ProductNotFound(message="Invalid input")

        # Patch the underlying function
        with patch.object(find_product_by_id, "func", mock_find_product_func):
            # Call function
            result = find_related_products.invoke(
                '{"product_id": "TST001", "relationship_type": "similar", "limit": 2}'
            )

            # Verify result
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)

    def test_find_related_products_invalid_product(self):
        """Test finding related products with invalid product ID."""

        # Create mock function that always returns ProductNotFound
        def mock_find_product_func(tool_input: str):
            return ProductNotFound(message="Product not found")

        # Patch the underlying function
        with patch.object(find_product_by_id, "func", mock_find_product_func):
            # Call function
            result = find_related_products.invoke('{"product_id": "NONEXISTENT"}')

            # Verify result
            self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_resolve_product_reference_valid(self, mock_get_vector_store):
        """Test resolving product reference with valid query."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST001",
            "name": "Test Shirt",
            "category": "Shirts",
            "stock": 10,
            "price": 29.99,
            "season": "Spring",
            "type": "",
            "description": "A comfortable cotton test shirt for any occasion.",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call function
        result = resolve_product_reference.invoke('{"query": "comfortable shirt"}')

        # Verify result
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "TST001")

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_resolve_product_reference_no_match(self, mock_get_vector_store):
        """Test resolving product reference with no match."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_vector_store.similarity_search.return_value = []

        # Call function
        result = resolve_product_reference.invoke('{"query": "nonexistent product"}')

        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_filtered_product_search_description(self, mock_get_vector_store):
        """Test filtered product search using description search."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST001",
            "name": "Test Shirt",
            "category": "Shirts",
            "stock": 10,
            "price": 29.99,
            "season": "Spring",
            "type": "",
            "description": "A comfortable cotton test shirt",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call function
        result = filtered_product_search.invoke(
            input="comfortable", search_type="description", category="Shirts"
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].product_id, "TST001")

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_filtered_product_search_name(self, mock_load_df):
        """Test filtered product search using name-based search."""
        # Setup mocks
        mock_load_df.return_value = get_mock_products_df()

        # Call function - searching for "Test" should match multiple products in mock data
        result = filtered_product_search.invoke(
            input="Test", search_type="name", min_stock=1
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for product in result:
            self.assertGreaterEqual(product.stock, 1)
            self.assertIn(
                "Test", product.name
            )  # All mock products have "Test" in the name


class TestCatalogToolsCriticalScenarios(unittest.TestCase):
    """Tests for critical real-world scenarios from email analysis."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_product_id_with_typo(self, mock_load_df):
        """Test E009 scenario: DHN0987 should resolve to CHN0987 (typo in product ID)."""
        # Setup mock with actual products data structure
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test the typo case: DHN0987 -> CHN0987
        result = find_product_by_id.invoke('{"product_id": "DHN0987"}')

        # Should find CHN0987 through fuzzy matching
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "CHN0987")
        self.assertEqual(result.name, "Chunky Knit Beanie")

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_product_id_with_spaces(self, mock_load_df):
        """Test E019 scenario: 'CBT 89 01' should resolve to CBT8901."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test spaces in product ID
        result = find_product_by_id.invoke('{"product_id": "CBT 89 01"}')

        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "CBT8901")
        self.assertEqual(result.name, "Chelsea Boots")

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_product_id_with_brackets(self, mock_load_df):
        """Test E019 scenario: '[CBT 89 01]' should resolve to CBT8901."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test brackets and spaces in product ID
        result = find_product_by_id.invoke('{"product_id": "[CBT 89 01]"}')

        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "CBT8901")
        self.assertEqual(result.name, "Chelsea Boots")

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_case_insensitive_product_id(self, mock_load_df):
        """Test case insensitive product ID matching."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test lowercase product ID
        result = find_product_by_id.invoke('{"product_id": "rsg8901"}')

        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "RSG8901")
        self.assertEqual(result.name, "Retro Sunglasses")

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_spanish_to_english_resolution(self, mock_get_vector_store):
        """Test E009: Spanish 'Gorro de punto grueso' should find chunky knit beanie."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock finding a beanie product
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "CHN0987",
            "name": "Chunky Knit Beanie",
            "category": "Accessories",
            "stock": 2,
            "price": 22.0,
            "season": "Fall, Winter",
            "type": "",
            "description": "Keep your head toasty with our chunky knit beanie",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Test Spanish query
        result = resolve_product_reference.invoke(
            '{"query": "DHN0987 Gorro de punto grueso"}'
        )

        # Should find the beanie through enhanced translation
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "CHN0987")
        self.assertIn("Beanie", result.name)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_vague_description_handling(self, mock_get_vector_store):
        """Test E017: Very vague query should return ProductNotFound."""
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_vector_store.similarity_search.return_value = []

        # Test very vague query
        result = resolve_product_reference.invoke(
            '{"query": "popular item selling like hotcakes"}'
        )

        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_functional_description_search(self, mock_get_vector_store):
        """Test E003: 'bag to carry laptop and documents' should find work bags."""
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock finding a work bag
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH1098",
            "name": "Leather Backpack",
            "category": "Bags",
            "stock": 7,
            "price": 43.99,
            "season": "All seasons",
            "type": "",
            "description": "Leather backpack with padded laptop sleeve and multiple compartments",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        result = search_products_by_description.invoke(
            '{"query": "bag to carry laptop and documents"}'
        )

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Should find bags suitable for work - backpack contains "pack" and is a type of bag
        self.assertTrue(
            "backpack" in result[0].name.lower()
            or "bag" in result[0].name.lower()
            or result[0].category == ProductCategory.BAGS
        )

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_category_and_season_filtering(self, mock_get_vector_store):
        """Test E013: 'slide sandals for men' with category filtering."""
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "SLD7654",
            "name": "Slide Sandals",
            "category": "Men's Shoes",
            "stock": 3,
            "price": 22.0,
            "season": "Spring, Summer",
            "type": "",
            "description": "Casual slide sandals for men",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        result = search_products_by_description.invoke(
            '{"query": "slide sandals for men", "category_filter": "Men\'s Shoes"}'
        )

        self.assertIsInstance(result, list)
        self.assertEqual(result[0].product_id, "SLD7654")

    def test_empty_query_handling(self):
        """Test edge case: empty query should return ProductNotFound."""
        result = resolve_product_reference.invoke('{"query": ""}')
        self.assertIsInstance(result, ProductNotFound)

    def test_malformed_json_handling(self):
        """Test edge case: malformed JSON should be handled gracefully."""
        result = find_product_by_id.invoke("not valid json")
        self.assertIsInstance(result, ProductNotFound)
        self.assertIn("Invalid input format", result.message)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_nonexistent_product_id(self, mock_load_df):
        """Test nonexistent product ID should return ProductNotFound."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        result = find_product_by_id.invoke('{"product_id": "XXX9999"}')
        self.assertIsInstance(result, ProductNotFound)


class TestMetadataConversion(unittest.TestCase):
    """Test the metadata_to_product conversion function."""

    def test_metadata_to_product_basic(self):
        """Test basic metadata to product conversion."""
        metadata = {
            "product_id": "TST001",
            "name": "Test Product",
            "category": "Accessories",
            "stock": 10,
            "price": 29.99,
            "season": "Spring",
            "type": "test",
            "description": "A test product",
        }

        product = metadata_to_product(metadata)

        self.assertIsInstance(product, Product)
        self.assertEqual(product.product_id, "TST001")
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.category, ProductCategory.ACCESSORIES)
        self.assertEqual(product.stock, 10)
        self.assertEqual(product.price, 29.99)

    def test_metadata_to_product_season_handling(self):
        """Test season handling in metadata conversion."""
        metadata = {
            "product_id": "TST001",
            "name": "Test Product",
            "category": "Accessories",
            "stock": 10,
            "price": 29.99,
            "season": "Fall, Winter",
            "type": "",
            "description": "A test product",
        }

        product = metadata_to_product(metadata)

        # Fall should be converted to Autumn
        self.assertIn(Season.AUTUMN, product.seasons)
        self.assertIn(Season.WINTER, product.seasons)


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
    def test_find_product_by_id_with_spanish_name_test_data(self, mock_load_df):
        """Test finding a product by ID when mention has a Spanish name, using test data."""
        # Setup mock with test data
        mock_load_df.return_value = get_test_products_df()

        # Product ID from the user's YAML example
        product_id_to_find = "CHN0987"
        expected_name = "Chunky Knit Beanie"  # Name in products.csv for CHN0987

        # Call the tool function using invoke
        # The tool should use the product_id for lookup, ignoring the Spanish name in a real scenario.
        # For this test, we are essentially checking if the ID lookup works correctly
        # even if the original mention had a different language name.
        result = find_product_by_id.invoke(
            json.dumps({"product_id": product_id_to_find})
        )

        # Verify the result is a Product object
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, product_id_to_find)
        self.assertEqual(
            result.name, expected_name
        )  # Check against the actual name in the CSV
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

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_with_test_data(self, mock_get_vector_store):
        """Test searching products by description using test data."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock finding leather products
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH0976",
            "name": "Leather Bifold Wallet",
            "category": "Accessories",
            "stock": 4,
            "price": 21.0,
            "season": "All seasons",
            "type": "",
            "description": "Premium leather bifold wallet with multiple card slots",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call the function using invoke
        result = search_products_by_description.invoke(
            json.dumps({"query": "leather", "top_k": 2})
        )

        # Verify the result is a list of Product objects
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        # Verify at least one product has "leather" in its description
        has_leather = any("leather" in p.description.lower() for p in result)
        self.assertTrue(has_leather)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_related_products_with_test_data(self, mock_get_vector_store):
        """Test finding related products using test data."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "SWL2345",
            "name": "Sleek Wallet",
            "category": "Accessories",
            "stock": 5,
            "price": 30.0,
            "season": "All seasons",
            "type": "",
            "description": "Sleek wallet with multiple slots",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Create mock function that returns the test product
        def mock_find_product_call(tool_input: str):
            import json

            try:
                input_data = json.loads(tool_input)
                product_id = input_data.get("product_id", "")
                if product_id == "LTH0976":
                    return get_product_by_id("LTH0976")  # Leather Bifold Wallet
                else:
                    return ProductNotFound(message="Product not found")
            except:
                return ProductNotFound(message="Invalid input")

        # Patch the __call__ method
        with patch.object(find_product_by_id, "__call__", mock_find_product_call):
            # Call function using invoke
            result = find_related_products.invoke(
                json.dumps(
                    {
                        "product_id": "LTH0976",
                        "relationship_type": "complementary",
                        "limit": 2,
                    }
                )
            )

            # Verify result is a list of products
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_resolve_product_reference_with_test_data(self, mock_get_vector_store):
        """Test resolving a product reference using test data."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH0976",
            "name": "Leather Bifold Wallet",
            "category": "Accessories",
            "stock": 4,
            "price": 21.0,
            "season": "All seasons",
            "type": "",
            "description": "Premium leather wallet",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call function using invoke
        result = resolve_product_reference.invoke(
            json.dumps({"query": "leather wallet"})
        )

        # Verify result is a Product object
        self.assertIsInstance(result, Product)
        self.assertEqual(result.product_id, "LTH0976")


if __name__ == "__main__":
    unittest.main()
