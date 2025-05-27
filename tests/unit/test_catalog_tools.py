"""Tests for catalog_tools.py."""

from unittest.mock import patch, MagicMock

from hermes.tools.catalog_tools import (
    find_product_by_id,
    find_product_by_name,
    search_products_by_description,
    metadata_to_product,
    find_complementary_products,
    search_products_with_filters,
    find_products_for_occasion,
)
from hermes.model.product import Product, ProductCategory, Season
from hermes.model.errors import ProductNotFound

from tests.fixtures.mock_product_catalog import (
    get_mock_products_df,
)
from tests.fixtures.test_product_catalog import (
    get_test_products_df,
)


class TestCatalogTools:
    """Tests for the catalog_tools module using mock data."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_valid(self, mock_load_df):
        """Test finding a product by a valid ID."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke
        result = find_product_by_id.invoke({"product_id": "TST001"})

        # Verify result
        assert isinstance(result, Product)
        assert result.product_id == "TST001"
        assert result.name == "Test Shirt"
        assert result.category == ProductCategory.SHIRTS

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_invalid(self, mock_load_df):
        """Test finding a product with invalid ID."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke
        result = find_product_by_id.invoke({"product_id": "NONEXISTENT"})

        # Verify result
        assert isinstance(result, ProductNotFound)
        assert "not found" in result.message

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_invalid_input(self, mock_load_df):
        """Test finding a product with invalid input."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke with empty string
        result = find_product_by_id.invoke({"product_id": ""})

        # Verify result
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_name_valid(self, mock_load_df):
        """Test finding a product by name with valid match."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke
        result = find_product_by_name.invoke({"product_name": "Test Shirt"})

        # Verify result - should match both "Test Shirt" products in mock data
        assert isinstance(result, list)
        # Both "Test Shirt" and "Test Shirt Blue" will match "Test Shirt"
        assert len(result) >= 1
        assert result[0].matched_product.name == "Test Shirt"
        assert result[0].similarity_score > 0.9

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_name_no_match(self, mock_load_df):
        """Test finding a product by name with no match."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke with high threshold to force no matches
        result = find_product_by_name.invoke(
            {"product_name": "Nonexistent Product", "threshold": 0.99}
        )

        # Verify result
        assert isinstance(result, ProductNotFound)

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

        # Call function directly (not a @tool)
        result = search_products_by_description(query="comfortable", top_k=2)

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "TST001"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_no_match(self, mock_get_vector_store):
        """Test searching products by description with no matches."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_vector_store.similarity_search.return_value = []

        # Call function directly (not a @tool)
        result = search_products_by_description(query="nonexistent term")

        # Verify result
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_complementary_products_valid(self, mock_get_vector_store):
        """Test finding complementary products with valid product ID."""
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

        # Mock find_product_by_id tool to return a valid product
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = Product(
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

        with patch("hermes.tools.catalog_tools.find_product_by_id", mock_tool):
            # Call @tool function using invoke
            result = find_complementary_products.invoke(
                {"product_id": "TST001", "limit": 2}
            )

            # Verify result
            assert isinstance(result, list)
            assert len(result) > 0

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_complementary_products_invalid_product(self, mock_get_vector_store):
        """Test finding complementary products with invalid product ID."""
        # Mock find_product_by_id tool to return ProductNotFound
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = ProductNotFound(message="Product not found")

        with patch("hermes.tools.catalog_tools.find_product_by_id", mock_tool):
            # Call @tool function using invoke
            result = find_complementary_products.invoke({"product_id": "NONEXISTENT"})

            # Verify result
            assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_with_filters_valid(self, mock_get_vector_store):
        """Test searching products with filters."""
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

        # Call @tool function using invoke
        result = search_products_with_filters.invoke(
            {
                "query": "comfortable shirt",
                "category": "Shirts",
                "min_price": 20.0,
                "max_price": 50.0,
                "top_k": 3,
            }
        )

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "TST001"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_with_filters_no_match(self, mock_get_vector_store):
        """Test searching products with filters that don't match."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_vector_store.similarity_search.return_value = []

        # Call @tool function using invoke
        result = search_products_with_filters.invoke(
            {"query": "nonexistent product", "category": "Shirts"}
        )

        # Verify result
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_products_for_occasion_valid(self, mock_get_vector_store):
        """Test finding products for a specific occasion."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST001",
            "name": "Formal Shirt",
            "category": "Shirts",
            "stock": 10,
            "price": 49.99,
            "season": "Spring",
            "type": "",
            "description": "A formal dress shirt perfect for business meetings.",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call @tool function using invoke
        result = find_products_for_occasion.invoke(
            {"occasion": "business meeting", "limit": 3}
        )

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "TST001"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_products_for_occasion_no_match(self, mock_get_vector_store):
        """Test finding products for occasion with no matches."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_vector_store.similarity_search.return_value = []

        # Call @tool function using invoke
        result = find_products_for_occasion.invoke({"occasion": "space travel"})

        # Verify result
        assert isinstance(result, ProductNotFound)


class TestCatalogToolsCriticalScenarios:
    """Tests for critical real-world scenarios from email analysis."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_product_id_with_typo(self, mock_load_df):
        """Test E009 scenario: DHN0987 should resolve to CHN0987 (typo in product ID)."""
        # Setup mock with actual products data structure
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test the typo case: DHN0987 -> CHN0987
        result = find_product_by_id.invoke({"product_id": "DHN0987"})

        # Should find CHN0987 through fuzzy matching
        assert isinstance(result, Product)
        assert result.product_id == "CHN0987"
        assert result.name == "Chunky Knit Beanie"

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_product_id_with_spaces(self, mock_load_df):
        """Test E019 scenario: 'CBT 89 01' should resolve to CBT8901."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test spaces in product ID
        result = find_product_by_id.invoke({"product_id": "CBT 89 01"})

        assert isinstance(result, Product)
        assert result.product_id == "CBT8901"
        assert result.name == "Chelsea Boots"

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_product_id_with_brackets(self, mock_load_df):
        """Test E019 scenario: '[CBT 89 01]' should resolve to CBT8901."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test brackets and spaces in product ID
        result = find_product_by_id.invoke({"product_id": "[CBT 89 01]"})

        assert isinstance(result, Product)
        assert result.product_id == "CBT8901"
        assert result.name == "Chelsea Boots"

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_case_insensitive_product_id(self, mock_load_df):
        """Test case insensitive product ID matching."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test lowercase product ID
        result = find_product_by_id.invoke({"product_id": "rsg8901"})

        assert isinstance(result, Product)
        assert result.product_id == "RSG8901"
        assert result.name == "Retro Sunglasses"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_spanish_to_english_resolution(self, mock_get_vector_store):
        """Test resolving Spanish product references to English products."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock a beanie product that should match the Spanish query
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "CHN0987",
            "name": "Chunky Knit Beanie",
            "category": "Accessories",
            "stock": 15,
            "price": 24.99,
            "season": "Winter",
            "type": "",
            "description": "A warm chunky knit beanie for winter weather.",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Test Spanish query
        result = search_products_with_filters.invoke(
            {"query": "DHN0987 Gorro de punto grueso"}
        )

        # Should find the beanie through enhanced translation
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "CHN0987"
        assert "Beanie" in result[0].name

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_vague_description_handling(self, mock_get_vector_store):
        """Test handling of very vague product descriptions."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_vector_store.similarity_search.return_value = []

        # Test very vague query
        result = search_products_with_filters.invoke(
            {"query": "popular item selling like hotcakes"}
        )

        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_functional_description_search(self, mock_get_vector_store):
        """Test searching by functional description rather than product name."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock a laptop bag that should match functional description
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "BAG001",
            "name": "Professional Laptop Bag",
            "category": "Bags",
            "stock": 8,
            "price": 89.99,
            "season": "Spring",
            "type": "",
            "description": "A professional bag designed for laptops and documents.",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        result = search_products_with_filters.invoke(
            {"query": "bag to carry laptop and documents"}
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "BAG001"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_category_and_season_filtering(self, mock_get_vector_store):
        """Test filtering by category and season."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock sandals that should match the query
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "SND001",
            "name": "Men's Slide Sandals",
            "category": "Men's Shoes",
            "stock": 12,
            "price": 39.99,
            "season": "Summer",
            "type": "",
            "description": "Comfortable slide sandals for men.",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        result = search_products_with_filters.invoke(
            {"query": "slide sandals for men", "category": "Men's Shoes"}
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "SND001"

    def test_empty_query_handling(self):
        """Test edge case: empty query should return ProductNotFound."""
        result = search_products_with_filters.invoke({"query": ""})
        assert isinstance(result, ProductNotFound)

    def test_malformed_json_handling(self):
        """Test edge case: malformed input should be handled gracefully."""
        # This test is no longer relevant since we're using proper function parameters
        # instead of JSON strings, but we'll test empty occasion for find_products_for_occasion
        result = find_products_for_occasion.invoke({"occasion": ""})
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_nonexistent_product_id(self, mock_load_df):
        """Test nonexistent product ID should return ProductNotFound."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        result = find_product_by_id.invoke({"product_id": "XXX9999"})
        assert isinstance(result, ProductNotFound)


class TestMetadataConversion:
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

        assert isinstance(product, Product)
        assert product.product_id == "TST001"
        assert product.name == "Test Product"
        assert product.category == ProductCategory.ACCESSORIES
        assert product.stock == 10
        assert product.price == 29.99

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
        assert Season.AUTUMN in product.seasons
        assert Season.WINTER in product.seasons


class TestCatalogToolsWithTestData:
    """Tests for catalog_tools using test product data from CSV."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_with_test_data(self, mock_load_df):
        """Test finding a product by ID with test product data."""
        # Setup mock with test data
        mock_load_df.return_value = get_test_products_df()

        # Use a product ID from the test data
        test_product_id = "RSG8901"  # Retro Sunglasses

        # Call the tool function directly
        result = find_product_by_id.invoke({"product_id": test_product_id})

        # Verify the result is a Product object
        assert isinstance(result, Product)
        assert result.product_id == test_product_id
        assert result.name == "Retro Sunglasses"
        assert result.category == ProductCategory.ACCESSORIES

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_with_spanish_name_test_data(self, mock_load_df):
        """Test finding a product by ID when mention has a Spanish name, using test data."""
        # Setup mock with test data
        mock_load_df.return_value = get_test_products_df()

        # Product ID from the user's YAML example
        product_id_to_find = "CHN0987"
        expected_name = "Chunky Knit Beanie"  # Name in products.csv for CHN0987

        # Call the tool function directly
        result = find_product_by_id.invoke({"product_id": product_id_to_find})

        # Verify the result is a Product object
        assert isinstance(result, Product)
        assert result.product_id == product_id_to_find
        assert result.name == expected_name  # Check against the actual name in the CSV
        assert result.category == ProductCategory.ACCESSORIES

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_not_found_with_test_data(self, mock_load_df):
        """Test finding a product with invalid ID using test data."""
        # Setup mock with test data
        mock_load_df.return_value = get_test_products_df()

        # Call with non-existent ID
        result = find_product_by_id.invoke({"product_id": "NONEXISTENT"})

        # Verify the result is a ProductNotFound object
        assert isinstance(result, ProductNotFound)
        assert "not found" in result.message.lower()

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_with_test_data(self, mock_get_vector_store):
        """Test searching products by description using test data."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock document representing a leather wallet from test data
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH0976",
            "name": "Leather Wallet",
            "category": "Accessories",
            "stock": 25,
            "price": 45.0,
            "season": "All seasons",
            "type": "",
            "description": "Premium leather wallet with multiple card slots",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call the function directly
        result = search_products_with_filters.invoke({"query": "leather"})

        # Verify the result is a list of Product objects
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "LTH0976"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_complementary_products_with_test_data(self, mock_get_vector_store):
        """Test finding complementary products using test data."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock document representing a complementary product
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH0977",
            "name": "Leather Belt",
            "category": "Accessories",
            "stock": 15,
            "price": 35.0,
            "season": "All seasons",
            "type": "",
            "description": "Premium leather belt to match your wallet",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Mock find_product_by_id tool to return a valid product
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = Product(
            product_id="LTH0976",
            name="Leather Wallet",
            description="Premium leather wallet with multiple card slots",
            category=ProductCategory.ACCESSORIES,
            stock=25,
            price=45.0,
            product_type="",
            seasons=[Season.SPRING],
            metadata=None,
        )

        with patch("hermes.tools.catalog_tools.find_product_by_id", mock_tool):
            # Call function using invoke
            result = find_complementary_products.invoke(
                {"product_id": "LTH0976", "limit": 2}
            )

            # Verify result is a list of products
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].product_id == "LTH0977"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_with_filters_with_test_data(self, mock_get_vector_store):
        """Test searching products with filters using test data."""
        # Setup mock vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store

        # Mock document representing a leather wallet from test data
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH0976",
            "name": "Leather Wallet",
            "category": "Accessories",
            "stock": 25,
            "price": 45.0,
            "season": "All seasons",
            "type": "",
            "description": "Premium leather wallet with multiple card slots",
        }
        mock_vector_store.similarity_search.return_value = [mock_doc]

        # Call function directly
        result = search_products_with_filters.invoke(
            {"query": "leather wallet", "category": "Accessories"}
        )

        # Verify result is a Product object
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "LTH0976"
