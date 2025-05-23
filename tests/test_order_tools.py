"""Tests for order_tools.py."""

import json
import unittest
from unittest.mock import patch

from hermes.tools.order_tools import (
    check_stock,
    update_stock,
    find_alternatives_for_oos,
    calculate_discount_price,
)
from hermes.model.errors import ProductNotFound
from hermes.model.enums import ProductCategory

from tests.fixtures.mock_product_catalog import get_mock_products_df
from tests.fixtures.test_product_catalog import get_test_products_df


class TestOrderTools(unittest.TestCase):
    """Tests for the order_tools module using mock data."""

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_in_stock(self, mock_load_df):
        """Test checking stock for an in-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = check_stock.invoke('{"product_id": "TST001", "requested_quantity": 5}')
        
        # Verify result
        self.assertEqual(result.product_id, "TST001")
        self.assertEqual(result.product_name, "Test Shirt")
        self.assertEqual(result.current_stock, 10)
        self.assertEqual(result.requested_quantity, 5)
        self.assertTrue(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_out_of_stock(self, mock_load_df):
        """Test checking stock for an out-of-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = check_stock.invoke('{"product_id": "TST003", "requested_quantity": 1}')
        
        # Verify result
        self.assertEqual(result.product_id, "TST003")
        self.assertEqual(result.current_stock, 0)
        self.assertFalse(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_insufficient_quantity(self, mock_load_df):
        """Test checking stock with insufficient quantity."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = check_stock.invoke('{"product_id": "TST002", "requested_quantity": 10}')
        
        # Verify result
        self.assertEqual(result.product_id, "TST002")
        self.assertEqual(result.current_stock, 5)
        self.assertEqual(result.requested_quantity, 10)
        self.assertFalse(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_invalid_product(self, mock_load_df):
        """Test checking stock for an invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = check_stock.invoke('{"product_id": "NONEXISTENT", "requested_quantity": 1}')
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_valid(self, mock_load_df):
        """Test updating stock with valid input."""
        # Setup mock
        df = get_mock_products_df()
        mock_load_df.return_value = df
        
        # Call function
        result = update_stock.invoke('{"product_id": "TST001", "quantity_to_decrement": 2}')
        
        # Verify result
        self.assertEqual(result.product_id, "TST001")
        self.assertEqual(result.product_name, "Test Shirt")
        self.assertEqual(result.previous_stock, 10)
        self.assertEqual(result.new_stock, 8)
        self.assertEqual(result.quantity_changed, -2)
        self.assertEqual(result.status, "success")

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_insufficient(self, mock_load_df):
        """Test updating stock with insufficient quantity."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = update_stock.invoke('{"product_id": "TST002", "quantity_to_decrement": 10}')
        
        # Verify result
        self.assertEqual(result.status, "insufficient_stock")
        self.assertEqual(result.previous_stock, 5)
        self.assertEqual(result.new_stock, 5)  # Should not change
        self.assertEqual(result.quantity_changed, 0)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_invalid_product(self, mock_load_df):
        """Test updating stock for an invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = update_stock.invoke('{"product_id": "NONEXISTENT", "quantity_to_decrement": 1}')
        
        # Verify result
        self.assertEqual(result.status, "product_not_found")

    @patch("hermes.tools.order_tools.load_products_df")
    def test_find_alternatives_for_oos_valid(self, mock_load_df):
        """Test finding alternatives for out-of-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = find_alternatives_for_oos.invoke('{"original_product_id": "TST003", "limit": 2}')
        
        # Verify result
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for alternative in result:
            self.assertEqual(alternative.product.category, "Men's Clothing")
            self.assertGreater(alternative.product.stock, 0)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_find_alternatives_for_oos_invalid_product(self, mock_load_df):
        """Test finding alternatives for invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()
        
        # Call function
        result = find_alternatives_for_oos.invoke('{"original_product_id": "NONEXISTENT"}')
        
        # Verify result
        self.assertIsInstance(result, ProductNotFound)

    def test_calculate_discount_price_percentage(self):
        """Test calculating discount with percentage off."""
        # Call function
        result = calculate_discount_price.invoke('{"original_price": 100.0, "promotion_text": "Get 20% off", "quantity": 1}')
        
        # Verify result
        self.assertEqual(result.original_price, 100.0)
        self.assertEqual(result.discounted_price, 80.0)
        self.assertEqual(result.discount_amount, 20.0)
        self.assertEqual(result.discount_percentage, 20.0)
        self.assertTrue(result.discount_applied)
        self.assertEqual(result.discount_type, "percentage")

    def test_calculate_discount_price_bogo(self):
        """Test calculating discount with buy-one-get-one offer."""
        # Call function
        result = calculate_discount_price.invoke(
            '{"original_price": 50.0, "promotion_text": "Buy one, get one free", "quantity": 2}'
        )
        
        # Verify result
        self.assertEqual(result.original_price, 50.0)
        self.assertEqual(result.discounted_price, 25.0)
        self.assertEqual(result.discount_amount, 25.0)
        self.assertTrue(result.discount_applied)
        self.assertEqual(result.discount_type, "bogo_free")

    def test_calculate_discount_price_bogo_half(self):
        """Test calculating discount with buy-one-get-one-half-off offer."""
        # Call function
        result = calculate_discount_price.invoke(
            '{"original_price": 50.0, "promotion_text": "Buy one, get one 50% off", "quantity": 2}'
        )
        
        # Verify result
        self.assertEqual(result.original_price, 50.0)
        self.assertTrue(result.discount_applied)
        # The discount type should be "bogo_half" for BOGO 50% off
        self.assertEqual(result.discount_type, "bogo_half")

    def test_calculate_discount_price_no_promotion(self):
        """Test calculating discount with no promotion text."""
        # Call function
        result = calculate_discount_price.invoke('{"original_price": 100.0, "promotion_text": "", "quantity": 1}')
        
        # Verify result
        self.assertEqual(result.original_price, 100.0)
        self.assertEqual(result.discounted_price, 100.0)
        self.assertEqual(result.discount_amount, 0.0)
        self.assertFalse(result.discount_applied)
        self.assertEqual(result.discount_type, "none")


class TestOrderToolsWithTestData(unittest.TestCase):
    """Tests for order_tools using test product data from CSV."""

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_in_stock_with_test_data(self, mock_load_df):
        """Test checking stock for an in-stock product using test data."""
        # Setup mock
        mock_load_df.return_value = get_test_products_df()
        
        # Call function
        result = check_stock.invoke('{"product_id": "TST001", "requested_quantity": 5}')
        
        # Verify result
        self.assertEqual(result.product_id, "TST001")
        self.assertEqual(result.product_name, "Classic T-Shirt")
        self.assertEqual(result.current_stock, 10)
        self.assertEqual(result.requested_quantity, 5)
        self.assertTrue(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_insufficient_with_test_data(self, mock_load_df):
        """Test checking stock with insufficient quantity using test data."""
        # Setup mock
        mock_load_df.return_value = get_test_products_df()
        
        # Call function
        result = check_stock.invoke('{"product_id": "TST002", "requested_quantity": 10}')
        
        # Verify result
        self.assertEqual(result.product_id, "TST002")
        self.assertEqual(result.current_stock, 5)
        self.assertEqual(result.requested_quantity, 10)
        self.assertFalse(result.is_available)

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_valid_with_test_data(self, mock_load_df):
        """Test updating stock with valid input using test data."""
        # Setup mock
        df = get_test_products_df()
        mock_load_df.return_value = df
        
        # Call function
        result = update_stock.invoke('{"product_id": "TST001", "quantity_to_decrement": 2}')
        
        # Verify result
        self.assertEqual(result.product_id, "TST001")
        self.assertEqual(result.product_name, "Classic T-Shirt")
        self.assertEqual(result.previous_stock, 10)
        self.assertEqual(result.new_stock, 8)
        self.assertEqual(result.quantity_changed, -2)
        self.assertEqual(result.status, "success")

    @patch("hermes.tools.order_tools.load_products_df")
    def test_find_alternatives_for_oos_with_test_data(self, mock_load_df):
        """Test finding alternatives for out-of-stock product using test data."""
        # Setup mock
        mock_load_df.return_value = get_test_products_df()
        
        # Call function
        result = find_alternatives_for_oos.invoke('{"original_product_id": "TST003", "limit": 2}')
        
        # Verify result
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for alternative in result:
            self.assertEqual(alternative.product.category, ProductCategory.MENS_CLOTHING)
            self.assertGreater(alternative.product.stock, 0)

    def test_calculate_discount_price_percentage_with_test_data(self):
        """Test calculating discount with percentage off using test data."""
        # Call function
        result = calculate_discount_price.invoke('{"original_price": 100.0, "promotion_text": "Get 20% off", "quantity": 1}')
        
        # Verify result
        self.assertEqual(result.original_price, 100.0)
        self.assertEqual(result.discounted_price, 80.0)
        self.assertEqual(result.discount_amount, 20.0)
        self.assertEqual(result.discount_percentage, 20.0)
        self.assertTrue(result.discount_applied)
        self.assertEqual(result.discount_type, "percentage")

    def test_calculate_discount_price_with_promotion_from_test_data(self):
        """Test calculating discount with a promotion from the test data."""
        # Get original price
        price = 29.99
        
        # Call function for "Buy one, get one 50% off" discount with 2 items
        result = calculate_discount_price.invoke(
            '{"original_price": 29.99, "promotion_text": "Buy one, get one 50% off", "quantity": 2}'
        )
        
        # Verify result
        self.assertEqual(result.original_price, 29.99)
        self.assertTrue(result.discount_applied)
        self.assertEqual(result.discount_type, "bogo_half")
        
    def test_calculate_discount_price_bogo_with_test_data(self):
        """Test calculating discount with buy-one-get-one offer using test data."""
        # Setup original price from test data
        price = 29.99
        
        # Call function
        result = calculate_discount_price.invoke(
            '{"original_price": 29.99, "promotion_text": "Buy one, get one free", "quantity": 2}'
        )
        
        # Verify result
        self.assertEqual(result.original_price, 29.99)
        self.assertTrue(result.discount_applied)
        self.assertEqual(result.discount_type, "bogo_free")


if __name__ == "__main__":
    unittest.main() 