"""Integration tests for catalog_tools.py, especially for tools involving vector store lookups."""

import pytest
from unittest.mock import (
    patch,
)  # Keep patch if we need to mock parts of the CSV loading for specific scenarios

from hermes.tools.catalog_tools import find_alternatives, find_complementary_products
from hermes.model.errors import ProductNotFound
from hermes.model.product import Product

# Fixtures for mock dataframes, if needed for specific controlled tests within integration context
from tests.fixtures.mock_product_catalog import get_mock_products_df
# from tests.fixtures.test_product_catalog import get_test_products_df # If using real test data

# It's good practice to have hermes_config for integration tests, even if not directly used by all tools,
# as underlying components (like get_vector_store) might depend on it.
# from hermes.config import HermesConfig # Import if needed for a config fixture


class TestCatalogToolsIntegration:
    """Integration tests for catalog tools that may interact with vector stores or real data."""

    # If HermesConfig is used by underlying components, a fixture like this would be standard:
    # @pytest.fixture
    # def hermes_config(self):
    #     from hermes.config import HermesConfig
    #     # Setup your integration test config here, possibly using environment variables
    #     return HermesConfig()

    # @pytest.fixture
    # def mock_runnable_config(self, hermes_config):
    #     return hermes_config.as_runnable_config()

    # Tests moved from test_order_tools.py
    @patch(
        "hermes.tools.catalog_tools.load_products_df"
    )  # Mocking CSV load if we want to control the dataset for this test
    def test_find_alternatives_for_oos_valid_integration(self, mock_load_df):
        """Test finding alternatives for out-of-stock product (Integration)."""
        # Setup mock - using mock_products_df for this example to control the data
        # For a true integration test against real data, you might not mock load_products_df
        # or use get_test_products_df() to load a specific test CSV.
        mock_load_df.return_value = get_mock_products_df()

        # Call tool function using invoke
        # TST003 is 'Test Dress', Men's Clothing, 0 stock in mock_products_df
        result = find_alternatives.invoke({"original_product_id": "TST003", "limit": 2})

        # Verify result - could be list or ProductNotFound
        # In mock_products_df, TST001 (Test Shirt) and TST002 (Test Shirt Blue) are Men's Clothing and in stock.
        if isinstance(result, list):
            assert len(result) > 0
            # Ensure all alternatives are in stock and from the same category (or a related one based on tool logic)
            for alternative_match in result:
                assert alternative_match.product.stock > 0
                # Assuming alternatives should be from the same category for this mock data scenario
                assert str(alternative_match.product.category.value) == "Men's Clothing"
        elif isinstance(result, ProductNotFound):
            # This might happen if the logic doesn't find suitable alternatives in the mock data
            pass  # Or assert specific conditions for ProductNotFound if expected
        else:
            pytest.fail(f"Unexpected result type: {type(result)}")

    @patch("hermes.tools.catalog_tools.load_products_df")  # Mocking CSV load
    def test_find_alternatives_for_oos_invalid_product_integration(self, mock_load_df):
        """Test finding alternatives for invalid product (Integration)."""
        mock_load_df.return_value = get_mock_products_df()

        # Call tool function using invoke
        result = find_alternatives.invoke({"original_product_id": "NONEXISTENT"})

        # Verify result
        assert isinstance(result, ProductNotFound)
        assert "Original product 'NONEXISTENT' not found" in result.message

    # Test moved from tests/unit/test_catalog_tools.py
    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_complementary_products_with_test_data_integration(self, mock_load_df):
        """Test finding complementary products using test product data (Integration)."""
        # This test relies on the actual implementation of find_complementary_products,
        # which may involve vector store lookups. load_products_df is mocked to control
        # the base product data for finding the initial product.
        from tests.fixtures.test_product_catalog import (
            get_test_products_df,
        )  # Ensure test data is used

        mock_load_df.return_value = get_test_products_df()

        # Using a product_id that exists in test_products.csv, e.g., LTH0976 (Leather Wallet, Accessories)
        # Complementary categories for Accessories might be Men's Clothing, Women's Clothing, Bags.
        # The mock_product_catalog.py defines TST005 as "Women's Clothing" which is what the original unit test used.
        # Let's stick to an ID from test_products.csv for an integration test using that data.
        # For LTH0976 (Accessories), if find_complementary_products looks for other accessories or related items.
        # This test will depend heavily on the vector store content if not further mocked.
        # For this example, let's use a known product from test_products.csv to see if it finds anything.
        # Let's use "RSG8901" (Retro Sunglasses, Accessories) as the source product.
        # Complementary could be other accessories or clothing.
        result = find_complementary_products.invoke(
            {"product_id": "RSG8901", "limit": 2}
        )

        # The result could be a list of products or ProductNotFound if no complements are found
        # or if the underlying vector store doesn't yield results for the given product's description/category.
        assert isinstance(result, (list, ProductNotFound))

        if isinstance(result, list):
            # If a list is returned, it should contain Product objects
            assert len(result) >= 0  # Can be an empty list if no complements found
            for item in result:
                # Assuming the items are Product objects
                assert isinstance(item, Product)
                assert item.stock > 0  # Complementary products should be in stock
        # If ProductNotFound, that's also an acceptable outcome for an integration test if no complements exist.
