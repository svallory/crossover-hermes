"""
Unit tests for the promotion_rulesets module.

These tests verify the functionality of the TypedDict-based promotion system
and ensure that various promotion types can be created correctly.
"""

import unittest
from src.hermes.agents.fulfiller.promotion_rulesets import (
    Condition,
    Effect,
    create_promotion,
    create_from_text,
)


class TestPromotionRulesets(unittest.TestCase):
    """Test cases for the promotion ruleset system."""

    def test_percentage_discount(self):
        """Test creating a percentage discount promotion."""
        promo = create_promotion(promotion_type="percentage_discount", discount_percentage=30)

        self.assertEqual(promo["name"], "Percentage Discount")
        self.assertEqual(promo["description"], "Get 30% off!")
        self.assertEqual(promo["conditions"][Condition.MIN_QUANTITY], 1)
        self.assertEqual(promo["effects"][Effect.DISCOUNT_PERCENTAGE], 30)

    def test_fixed_amount_discount(self):
        """Test creating a fixed amount discount promotion."""
        promo = create_promotion(promotion_type="fixed_amount_discount", discount_amount=15.0)

        self.assertEqual(promo["name"], "Fixed Amount Discount")
        self.assertEqual(promo["description"], "$15.0 off your order!")
        self.assertEqual(promo["conditions"][Condition.MIN_QUANTITY], 1)
        self.assertEqual(promo["effects"][Effect.DISCOUNT_AMOUNT], 15.0)

    def test_buy_x_get_y_free(self):
        """Test creating a buy X get Y free promotion."""
        promo = create_promotion(promotion_type="buy_x_get_y_free", buy_quantity=2, free_quantity=1)

        self.assertEqual(promo["name"], "Buy X Get Y Free")
        self.assertEqual(promo["description"], "Buy 2, get 1 free!")
        self.assertEqual(promo["conditions"][Condition.MIN_QUANTITY], 2)
        self.assertEqual(promo["conditions"][Condition.APPLIES_EVERY], 3)
        self.assertEqual(promo["effects"][Effect.FREE_ITEMS], 1)

    def test_buy_x_get_y_discount(self):
        """Test creating a buy X get Y at discount promotion."""
        promo = create_promotion(
            promotion_type="buy_x_get_y_discount", buy_quantity=2, discount_quantity=1, discount_percentage=25
        )

        self.assertEqual(promo["name"], "Buy X Get Y at Discount")
        self.assertEqual(promo["description"], "Buy 2, get 1 25% off!")
        self.assertEqual(promo["conditions"][Condition.MIN_QUANTITY], 2)
        self.assertEqual(promo["conditions"][Condition.APPLIES_EVERY], 3)
        self.assertEqual(promo["effects"][Effect.DISCOUNT_PERCENTAGE]["target"], "second_item")
        self.assertEqual(promo["effects"][Effect.DISCOUNT_PERCENTAGE]["value"], 25)

    def test_free_gift(self):
        """Test creating a free gift promotion."""
        promo = create_promotion(promotion_type="free_gift", gift_description="premium tote bag")

        self.assertEqual(promo["name"], "Free Gift")
        self.assertEqual(promo["description"], "Buy now and get a free premium tote bag!")
        self.assertEqual(promo["conditions"][Condition.MIN_QUANTITY], 1)
        self.assertEqual(promo["effects"][Effect.FREE_GIFT], "premium tote bag")

    def test_combo_deal(self):
        """Test creating a combo deal promotion."""
        promo = create_promotion(
            promotion_type="combo_deal",
            related_product_id="ACCS123",
            related_product_description="matching accessories set",
            discount_percentage=40,
        )

        self.assertEqual(promo["name"], "Combo Deal")
        self.assertEqual(promo["description"], "Buy one, get a matching accessories set at 40% off!")
        self.assertEqual(promo["conditions"][Condition.MIN_QUANTITY], 1)
        self.assertEqual(promo["effects"][Effect.ADD_PRODUCT]["product_id"], "ACCS123")
        self.assertEqual(promo["effects"][Effect.ADD_PRODUCT]["description"], "matching accessories set")
        self.assertEqual(promo["effects"][Effect.ADD_PRODUCT]["discount_percentage"], 40)

    def test_custom_promotion(self):
        """Test creating a custom promotion from scratch."""
        promo = create_promotion(
            name="Holiday Special",
            description="End of season clearance!",
            conditions={Condition.MIN_QUANTITY: 2, Condition.APPLIES_EVERY: 2},
            effects={Effect.DISCOUNT_PERCENTAGE: 35},
        )

        self.assertEqual(promo["name"], "Holiday Special")
        self.assertEqual(promo["description"], "End of season clearance!")
        self.assertEqual(promo["conditions"][Condition.MIN_QUANTITY], 2)
        self.assertEqual(promo["conditions"][Condition.APPLIES_EVERY], 2)
        self.assertEqual(promo["effects"][Effect.DISCOUNT_PERCENTAGE], 35)

    def test_create_from_text(self):
        """Test creating promotions from text descriptions."""
        # Test percentage discount
        promo = create_from_text("Get 25% off all products this weekend!")
        self.assertEqual(promo["name"], "Percentage Discount")
        self.assertEqual(promo["effects"][Effect.DISCOUNT_PERCENTAGE], 25)

        # Test Buy One Get One Free
        promo = create_from_text("BOGO sale on all footwear!")
        self.assertEqual(promo["name"], "Buy One Get One Free")
        self.assertEqual(promo["effects"][Effect.FREE_ITEMS], 1)

        # Test free gift
        promo = create_from_text("Purchase any jacket and receive a free matching beanie!")
        self.assertEqual(promo["name"], "Free Gift")
        self.assertEqual(promo["effects"][Effect.FREE_GIFT], "matching beanie")


if __name__ == "__main__":
    unittest.main()
