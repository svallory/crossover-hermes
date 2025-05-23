"""Tests for promotion_tools.py."""

import json
import unittest
from copy import deepcopy

from hermes.tools.promotion_tools import apply_promotion
from hermes.model.order import Order, OrderLine
from hermes.model.promotions import PromotionSpec, PromotionConditions, PromotionEffects, DiscountSpec

from tests.fixtures.test_product_catalog import get_test_products_df


class TestPromotionTools(unittest.TestCase):
    """Tests for the promotion_tools module using mock data."""

    def test_apply_promotion_percentage_discount(self):
        """Test applying a percentage discount promotion."""
        # Prepare test data
        input_data = {
            "email_id": "test@example.com",
            "ordered_items": [
                {
                    "product_id": "TST001",
                    "description": "Test Shirt",
                    "quantity": 2,
                    "base_price": 100.0
                }
            ],
            "promotion_specs": [
                {
                    "description": "20% off shirts",
                    "conditions": {
                        "min_quantity": 1
                    },
                    "effects": {
                        "apply_discount": {
                            "type": "percentage",
                            "amount": 20.0
                        }
                    }
                }
            ]
        }
        
        # Call function
        result = apply_promotion.invoke(json.dumps(input_data))
        
        # Verify result
        self.assertIsInstance(result, Order)
        self.assertEqual(result.email_id, "test@example.com")
        self.assertEqual(result.overall_status, "created")
        self.assertEqual(len(result.lines), 1)
        
        # Check line details
        line = result.lines[0]
        self.assertEqual(line.product_id, "TST001")
        self.assertEqual(line.description, "Test Shirt")
        self.assertEqual(line.quantity, 2)
        self.assertEqual(line.base_price, 100.0)
        self.assertEqual(line.unit_price, 80.0)  # 20% off
        self.assertEqual(line.total_price, 160.0)
        self.assertTrue(line.promotion_applied)
        
        # Check order totals
        self.assertEqual(result.total_discount, 40.0)
        self.assertEqual(result.total_price, 160.0)

    def test_apply_promotion_free_items(self):
        """Test applying a free items promotion."""
        # Prepare test data
        input_data = {
            "email_id": "test@example.com",
            "ordered_items": [
                {
                    "product_id": "TST001",
                    "description": "Test Shirt",
                    "quantity": 4,
                    "base_price": 50.0
                }
            ],
            "promotion_specs": [
                {
                    "description": "Buy 3, get 1 free",
                    "conditions": {
                        "min_quantity": 4
                    },
                    "effects": {
                        "free_items": 1
                    }
                }
            ]
        }
        
        # Call function
        result = apply_promotion.invoke(json.dumps(input_data))
        
        # Verify result
        self.assertIsInstance(result, Order)
        self.assertEqual(result.email_id, "test@example.com")
        self.assertEqual(result.overall_status, "created")
        self.assertEqual(len(result.lines), 1)
        
        # Check line details
        line = result.lines[0]
        self.assertEqual(line.product_id, "TST001")
        self.assertEqual(line.quantity, 4)
        self.assertEqual(line.base_price, 50.0)
        self.assertEqual(line.unit_price, 37.5)  # 4 items for price of 3
        self.assertEqual(line.total_price, 150.0)
        self.assertTrue(line.promotion_applied)
        
        # Check order totals
        self.assertEqual(result.total_discount, 50.0)
        self.assertEqual(result.total_price, 150.0)

    def test_apply_promotion_free_gift(self):
        """Test applying a free gift promotion."""
        # Prepare test data
        input_data = {
            "email_id": "test@example.com",
            "ordered_items": [
                {
                    "product_id": "TST005",
                    "description": "Test Dress",
                    "quantity": 1,
                    "base_price": 100.0
                }
            ],
            "promotion_specs": [
                {
                    "description": "Free gift with dress purchase",
                    "conditions": {
                        "min_quantity": 1
                    },
                    "effects": {
                        "free_gift": "Complementary scarf"
                    }
                }
            ]
        }
        
        # Call function
        result = apply_promotion.invoke(json.dumps(input_data))
        
        # Verify result
        self.assertIsInstance(result, Order)
        self.assertEqual(len(result.lines), 1)
        
        # Check line details
        line = result.lines[0]
        self.assertEqual(line.product_id, "TST005")
        self.assertEqual(line.description, "Test Dress")
        self.assertTrue(line.promotion_applied)
        self.assertIn("Free gift", line.promotion_description or "")

    def test_apply_promotion_multiple_items(self):
        """Test applying promotions to multiple items."""
        # Prepare test data
        input_data = {
            "email_id": "test@example.com",
            "ordered_items": [
                {
                    "product_id": "TST001",
                    "description": "Test Shirt",
                    "quantity": 2,
                    "base_price": 50.0
                },
                {
                    "product_id": "TST002",
                    "description": "Test Pants",
                    "quantity": 1,
                    "base_price": 100.0
                }
            ],
            "promotion_specs": [
                {
                    "description": "10% off shirts",
                    "conditions": {
                        "min_quantity": 1
                    },
                    "effects": {
                        "apply_discount": {
                            "type": "percentage",
                            "amount": 10.0,
                            "to_product_id": "TST001"
                        }
                    }
                }
            ]
        }
        
        # Call function
        result = apply_promotion.invoke(json.dumps(input_data))
        
        # Verify result
        self.assertIsInstance(result, Order)
        self.assertEqual(result.email_id, "test@example.com")
        self.assertEqual(result.overall_status, "created")
        self.assertEqual(len(result.lines), 2)
        
        # Check shirt line (should have promotion)
        shirt_line = next(line for line in result.lines if line.product_id == "TST001")
        self.assertEqual(shirt_line.base_price, 50.0)
        self.assertEqual(shirt_line.unit_price, 45.0)  # 10% off
        self.assertTrue(shirt_line.promotion_applied)
        
        # Check pants line (should not have promotion)
        pants_line = next(line for line in result.lines if line.product_id == "TST002")
        self.assertEqual(pants_line.base_price, 100.0)
        self.assertEqual(pants_line.unit_price, 100.0)  # No discount
        self.assertFalse(pants_line.promotion_applied)
        
        # Check order totals
        self.assertEqual(result.total_discount, 10.0)
        self.assertEqual(result.total_price, 190.0)

    def test_apply_promotion_invalid_input(self):
        """Test applying promotion with invalid input."""
        # Call function with invalid JSON
        result = apply_promotion.invoke("not a json")
        
        # Verify result still returns a valid Order object with error status
        self.assertIsInstance(result, Order)
        self.assertEqual(result.email_id, "error")
        self.assertEqual(result.overall_status, "no_valid_products")
        self.assertEqual(len(result.lines), 0)


class TestPromotionToolsWithTestData(unittest.TestCase):
    """Tests for promotion_tools using test data from CSV."""

    def create_order_items_from_test_products(self):
        """Create order items from test product data."""
        # Load products from test data
        products_df = get_test_products_df()
        
        # Extract a few products with known promotions mentioned in descriptions
        order_items = []
        
        # QTP5432 - Quilted Tote with "Limited-time sale - get 25% off!"
        tote_row = products_df[products_df["product_id"] == "QTP5432"].iloc[0]
        order_items.append({
            "product_id": "QTP5432",
            "description": tote_row["name"],
            "quantity": 1,
            "base_price": float(tote_row["price"])
        })
        
        # CBG9876 - Canvas Beach Bag with "Buy one, get one 50% off!"
        bag_row = products_df[products_df["product_id"] == "CBG9876"].iloc[0]
        order_items.append({
            "product_id": "CBG9876",
            "description": bag_row["name"],
            "quantity": 2,  # Order 2 to trigger BOGO
            "base_price": float(bag_row["price"])
        })
        
        # Regular product with no promotion
        regular_row = products_df[products_df["product_id"] == "RSG8901"].iloc[0]
        order_items.append({
            "product_id": "RSG8901",
            "description": regular_row["name"],
            "quantity": 1,
            "base_price": float(regular_row["price"])
        })
        
        return order_items

    def test_apply_percentage_promotion_with_test_data(self):
        """Test applying a percentage discount promotion with test product data."""
        # Get order items from test products
        ordered_items = self.create_order_items_from_test_products()
        
        # Use only the Quilted Tote with 25% off promotion
        tote_item = next(item for item in ordered_items if item["product_id"] == "QTP5432")
        
        input_data = {
            "email_id": "test@example.com",
            "ordered_items": [tote_item],
            "promotion_specs": [
                {
                    "description": "25% off Quilted Tote",
                    "conditions": {
                        "min_quantity": 1
                    },
                    "effects": {
                        "apply_discount": {
                            "type": "percentage",
                            "amount": 25.0,
                            "to_product_id": "QTP5432"
                        }
                    }
                }
            ]
        }
        
        # Call function using invoke
        result = apply_promotion.invoke(json.dumps(input_data))
        
        # The result should be an Order object since we're using invoke
        self.assertIsInstance(result, Order)
        self.assertEqual(result.email_id, "test@example.com")
        self.assertEqual(len(result.lines), 1)
        
        # Check line details
        line = result.lines[0]
        self.assertEqual(line.product_id, "QTP5432")
        base_price = tote_item["base_price"]
        self.assertEqual(line.base_price, base_price)
        
        # Expect 25% off
        expected_discounted_price = base_price * 0.75
        self.assertAlmostEqual(line.unit_price, expected_discounted_price, places=2)
        self.assertTrue(line.promotion_applied)

    def test_apply_bogo_promotion_with_test_data(self):
        """Test applying a BOGO promotion with test product data."""
        # Get order items from test products
        ordered_items = self.create_order_items_from_test_products()
        
        # Use only the Canvas Beach Bag with BOGO 50% off
        bag_item = next(item for item in ordered_items if item["product_id"] == "CBG9876")
        
        input_data = {
            "email_id": "test@example.com",
            "ordered_items": [bag_item],  # ordering 2 of these
            "promotion_specs": [
                {
                    "description": "Buy one get one 50% off beach bags",
                    "conditions": {
                        "min_quantity": 2
                    },
                    "effects": {
                        "apply_discount": {
                            "type": "percentage",
                            "amount": 25.0,  # 25% off each item = 50% off one of two items
                            "to_product_id": "CBG9876"
                        }
                    }
                }
            ]
        }
        
        # Call function using invoke
        result = apply_promotion.invoke(json.dumps(input_data))
        
        # The result should be an Order object since we're using invoke
        self.assertIsInstance(result, Order)
        self.assertEqual(len(result.lines), 1)
        
        # Check line details
        line = result.lines[0]
        self.assertEqual(line.product_id, "CBG9876")
        base_price = bag_item["base_price"]
        quantity = bag_item["quantity"]
        self.assertEqual(quantity, 2)
        
        # For BOGO 50% off with 2 items, we're applying 25% off each item
        expected_discount = base_price * 0.25 * quantity
        expected_total = base_price * quantity - expected_discount
        
        self.assertAlmostEqual(result.total_discount, expected_discount, places=2)
        self.assertAlmostEqual(result.total_price, expected_total, places=2)
        self.assertTrue(line.promotion_applied)

    def test_apply_multiple_promotions_with_test_data(self):
        """Test applying multiple promotions to different products."""
        # Get all order items 
        ordered_items = self.create_order_items_from_test_products()
        
        input_data = {
            "email_id": "test@example.com",
            "ordered_items": ordered_items,
            "promotion_specs": [
                {
                    "description": "25% off Quilted Tote",
                    "conditions": {
                        "min_quantity": 1
                    },
                    "effects": {
                        "apply_discount": {
                            "type": "percentage",
                            "amount": 25.0,
                            "to_product_id": "QTP5432"
                        }
                    }
                },
                {
                    "description": "Buy one get one 50% off beach bags",
                    "conditions": {
                        "min_quantity": 2
                    },
                    "effects": {
                        "apply_discount": {
                            "type": "percentage",
                            "amount": 25.0,
                            "to_product_id": "CBG9876"
                        }
                    }
                }
            ]
        }
        
        # Call function using invoke
        result = apply_promotion.invoke(json.dumps(input_data))
        
        # The result should be an Order object since we're using invoke
        self.assertIsInstance(result, Order)
        self.assertEqual(len(result.lines), 3)
        
        # Check which lines have promotions applied
        tote_line = next(line for line in result.lines if line.product_id == "QTP5432")
        bag_line = next(line for line in result.lines if line.product_id == "CBG9876")
        sunglasses_line = next(line for line in result.lines if line.product_id == "RSG8901")
        
        # Tote should have promotion
        self.assertTrue(tote_line.promotion_applied)
        
        # Bag should have promotion
        self.assertTrue(bag_line.promotion_applied)
        
        # Sunglasses should not have promotion
        self.assertFalse(sunglasses_line.promotion_applied)

    def test_invalid_input_handling_with_test_data(self):
        """Test handling of invalid input."""
        # Call with invalid JSON using invoke
        result = apply_promotion.invoke("not a valid json")
        
        # Should return a valid Order object with error status
        self.assertIsInstance(result, Order)
        self.assertEqual(result.email_id, "error")
        self.assertEqual(result.overall_status, "no_valid_products")
        self.assertEqual(len(result.lines), 0)


if __name__ == "__main__":
    unittest.main() 