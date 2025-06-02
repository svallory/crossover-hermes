"""Tests for order_tools.py."""

import pytest
from unittest.mock import patch

from hermes.tools.order_tools import (
    check_stock,
    update_stock,
    StockStatus,
    StockUpdateStatus,
)
from hermes.model.errors import ProductNotFound

from tests.fixtures.mock_product_catalog import get_mock_products_df
from tests.fixtures.test_product_catalog import get_test_products_df


class TestOrderTools:
    """Tests for the order_tools module using mock data."""

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_in_stock(self, mock_load_df):
        """Test checking stock for an in-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="TST001", requested_quantity=5)

        # Verify result
        assert isinstance(result, StockStatus)
        assert result.current_stock == 10
        assert result.is_available

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_out_of_stock(self, mock_load_df):
        """Test checking stock for an out-of-stock product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="TST003", requested_quantity=1)

        # Verify result
        assert isinstance(result, StockStatus)
        assert result.current_stock == 0
        assert not result.is_available

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_insufficient_quantity(self, mock_load_df):
        """Test checking stock with insufficient quantity."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="TST002", requested_quantity=10)

        # Verify result
        assert isinstance(result, StockStatus)
        assert result.current_stock == 5
        assert not result.is_available

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_invalid_product(self, mock_load_df):
        """Test checking stock for an invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="NONEXISTENT", requested_quantity=1)

        # Verify result
        assert isinstance(result, ProductNotFound)
        assert "not found" in result.message

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_valid(self, mock_load_df):
        """Test updating stock with valid input."""
        # Setup mock
        df = get_mock_products_df()
        mock_load_df.return_value = df

        # Call function directly (not using .invoke())
        result = update_stock(product_id="TST001", quantity_to_decrement=2)

        # Verify result
        assert result == StockUpdateStatus.SUCCESS

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_insufficient(self, mock_load_df):
        """Test updating stock with insufficient quantity."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = update_stock(product_id="TST002", quantity_to_decrement=10)

        # Verify result
        assert result == StockUpdateStatus.INSUFFICIENT_STOCK

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_invalid_product(self, mock_load_df):
        """Test updating stock for an invalid product."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call function directly (not using .invoke())
        result = update_stock(product_id="NONEXISTENT", quantity_to_decrement=1)

        # Verify result
        assert result == StockUpdateStatus.PRODUCT_NOT_FOUND


class TestOrderToolsWithTestData:
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
            assert result.is_available
        else:
            pytest.fail("Expected StockStatus but got ProductNotFound")

    @patch("hermes.tools.order_tools.load_products_df")
    def test_check_stock_insufficient_with_test_data(self, mock_load_df):
        """Test checking stock with insufficient quantity using test data."""
        # Setup mock
        mock_load_df.return_value = get_test_products_df()

        # Call function directly (not using .invoke())
        result = check_stock(product_id="LTH0976", requested_quantity=100)

        # Verify result
        if isinstance(result, StockStatus):
            assert not result.is_available
        else:
            pytest.fail("Expected StockStatus but got ProductNotFound")

    @patch("hermes.tools.order_tools.load_products_df")
    def test_update_stock_valid_with_test_data(self, mock_load_df):
        """Test updating stock with valid input using test data."""
        # Setup mock
        df = get_test_products_df()
        mock_load_df.return_value = df

        # Call function directly (not using .invoke())
        result = update_stock(product_id="LTH0976", quantity_to_decrement=1)

        # Verify result
        assert result == StockUpdateStatus.SUCCESS
