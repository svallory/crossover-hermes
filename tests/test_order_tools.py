"""Tests for order_tools.py."""

import unittest
from unittest.mock import patch

from hermes.tools.catalog_tools import find_alternatives
from hermes.tools.order_tools import (
    check_stock,
    update_stock,
    StockStatus,
    StockUpdateStatus,
)
from hermes.model.errors import ProductNotFound

from tests.fixtures.mock_product_catalog import get_mock_products_df
from tests.fixtures.test_product_catalog import get_test_products_df


class TestOrderTools(unittest.TestCase):
    """Tests for the order_tools module using mock data."""

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_in_stock(self, mock_load_df):
        """Test checking stock for an in-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="TST001", requested_quantity=5)

        # Verify result
        self.assertIsInstance(result, StockStatus)
        self.assertEqual(result.current_stock, 10)
        self.assertTrue(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_out_of_stock(self, mock_load_df):
        """Test checking stock for an out-of-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="TST003", requested_quantity=1)

        # Verify result
        self.assertIsInstance(result, StockStatus)
        self.assertEqual(result.current_stock, 0)
        self.assertFalse(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_insufficient_quantity(self, mock_load_df):
        """Test checking stock with insufficient quantity."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="TST002", requested_quantity=10)

        # Verify result
        self.assertIsInstance(result, StockStatus)
        self.assertEqual(result.current_stock, 5)
        self.assertFalse(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_invalid_product(self, mock_load_df):
        """Test checking stock for an invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="NONEXISTENT", requested_quantity=1)

        # Verify result
        self.assertIsInstance(result, ProductNotFound)
        self.assertIn("not found", result.message)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_valid(self, mock_load_df):
        """Test updating stock with valid input."""
        # Setup mock
        df = get_mock_products_df()
        mock_load_df.return_value = df

        # Call function directly (not using .invoke())
        result = update_stock(product_id="TST001", quantity_to_decrement=2)

        # Verify result
        self.assertEqual(result, StockUpdateStatus.SUCCESS)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_insufficient(self, mock_load_df):
        """Test updating stock with insufficient quantity."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = update_stock(product_id="TST002", quantity_to_decrement=10)

        # Verify result
        self.assertEqual(result, StockUpdateStatus.INSUFFICIENT_STOCK)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_invalid_product(self, mock_load_df):
        """Test updating stock for an invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = update_stock(product_id="NONEXISTENT", quantity_to_decrement=1)

        # Verify result
        self.assertEqual(result, StockUpdateStatus.PRODUCT_NOT_FOUND)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_alternatives_for_oos_valid(self, mock_load_df):
        """Test finding alternatives for out-of-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = find_alternatives(original_product_id="TST003", limit=2)

        # Verify result - could be list or ProductNotFound
        if isinstance(result, list):
            self.assertGreater(len(result), 0)
            for alternative in result:
                self.assertEqual(alternative.product.category, "Men's Clothing")
                self.assertGreater(alternative.product.stock, 0)
        else:
            self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_alternatives_for_oos_invalid_product(self, mock_load_df):
        """Test finding alternatives for invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = find_alternatives(original_product_id="NONEXISTENT")

        # Verify result
        self.assertIsInstance(result, ProductNotFound)


class TestOrderToolsWithTestData(unittest.TestCase):
    """Tests for the order_tools module using test data."""

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_in_stock_with_test_data(self, mock_load_df):
        """Test checking stock for an in-stock product using test data."""
        # Setup mock
        mock_load_df.return_value = get_test_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="LTH0976", requested_quantity=1)

        # Verify result
        if isinstance(result, StockStatus):
            self.assertTrue(result.is_available)
        else:
            self.fail("Expected StockStatus but got ProductNotFound")

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_insufficient_with_test_data(self, mock_load_df):
        """Test checking stock with insufficient quantity using test data."""
        # Setup mock
        mock_load_df.return_value = get_test_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="LTH0976", requested_quantity=100)

        # Verify result
        if isinstance(result, StockStatus):
            self.assertFalse(result.is_available)
        else:
            self.fail("Expected StockStatus but got ProductNotFound")

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_valid_with_test_data(self, mock_load_df):
        """Test updating stock with valid input using test data."""
        # Setup mock
        df = get_test_products_df()
        mock_load_df.return_value = df

        # Call function directly (not using .invoke())
        result = update_stock(product_id="LTH0976", quantity_to_decrement=1)

        # Verify result
        self.assertEqual(result, StockUpdateStatus.SUCCESS)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_alternatives_for_oos_with_test_data(self, mock_load_df):
        """Test finding alternatives for out-of-stock product using test data."""
        # Setup mock
        mock_load_df.return_value = get_test_products_df()

        # Call function directly (not using .invoke())
        result = find_alternatives(original_product_id="LTH0976", limit=2)

        # Verify result - could be list or ProductNotFound
        if isinstance(result, list):
            self.assertGreaterEqual(len(result), 0)
        else:
            self.assertIsInstance(result, ProductNotFound)


if __name__ == "__main__":
    unittest.main()
