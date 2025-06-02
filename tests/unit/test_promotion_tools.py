"""Tests for promotion_tools.py."""

from hermes.tools.promotion_tools import apply_promotion
from hermes.model.order import Order, OrderLine


class TestPromotionTools:
    """Tests for the promotion_tools module using mock data."""

    def test_apply_promotion_percentage_discount(self):
        """Test applying a percentage discount promotion."""
        # Create an Order object
        order = Order(
            email_id="test@example.com",
            overall_status="created",
            lines=[
                OrderLine(
                    product_id="TST001",
                    name="Test Shirt",
                    description="Test Shirt",
                    quantity=2,
                    base_price=100.0,
                    unit_price=100.0,
                    total_price=200.0,
                )
            ],
            total_price=200.0,
        )

        promotion_specs = [
            {
                "description": "20% off shirts",
                "conditions": {"min_quantity": 1},
                "effects": {"apply_discount": {"type": "percentage", "amount": 20.0}},
            }
        ]

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # Verify result
        assert isinstance(result, Order)
        assert result.email_id == "test@example.com"
        assert result.overall_status == "created"
        assert len(result.lines) == 1

        # Check the order line
        line = result.lines[0]
        assert line.product_id == "TST001"
        assert line.quantity == 2
        assert line.base_price == 100.0
        assert line.unit_price == 80.0  # 20% discount applied
        assert line.total_price == 160.0  # 80 * 2
        assert line.promotion_applied

        # Check order totals
        assert result.total_discount == 40.0
        assert result.total_price == 160.0

    def test_apply_promotion_free_items(self):
        """Test applying a free items promotion."""
        # Create an Order object
        order = Order(
            email_id="test@example.com",
            overall_status="created",
            lines=[
                OrderLine(
                    product_id="TST001",
                    name="Test Shirt",
                    description="Test Shirt",
                    quantity=4,
                    base_price=50.0,
                    unit_price=50.0,
                    total_price=200.0,
                )
            ],
            total_price=200.0,
        )

        promotion_specs = [
            {
                "description": "Buy 3, get 1 free",
                "conditions": {"min_quantity": 4},
                "effects": {"free_items": 1},
            }
        ]

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # Verify result
        assert isinstance(result, Order)
        assert result.email_id == "test@example.com"
        assert result.overall_status == "created"
        assert len(result.lines) == 1

        # Check the order line
        line = result.lines[0]
        assert line.product_id == "TST001"
        assert line.quantity == 4
        assert line.base_price == 50.0
        assert line.promotion_applied
        # With 1 free item out of 4, effective price should be 37.5 per item
        assert line.unit_price == 37.5

        # Check order totals
        assert result.total_discount == 50.0
        assert result.total_price == 150.0

    def test_apply_promotion_free_gift(self):
        """Test applying a free gift promotion."""
        # Create an Order object
        order = Order(
            email_id="test@example.com",
            overall_status="created",
            lines=[
                OrderLine(
                    product_id="TST005",
                    name="Test Dress",
                    description="Test Dress",
                    quantity=1,
                    base_price=100.0,
                    unit_price=100.0,
                    total_price=100.0,
                )
            ],
            total_price=100.0,
        )

        promotion_specs = [
            {
                "description": "Free gift with dress purchase",
                "conditions": {"min_quantity": 1},
                "effects": {"free_gift": "Complementary scarf"},
            }
        ]

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # Verify result
        assert isinstance(result, Order)
        assert result.email_id == "test@example.com"
        assert result.overall_status == "created"
        assert len(result.lines) == 1

        # Check the order line
        line = result.lines[0]
        assert line.product_id == "TST005"
        assert line.quantity == 1
        assert line.base_price == 100.0
        assert line.unit_price == 100.0  # Price unchanged for free gift
        assert line.promotion_applied
        assert line.promotion_description is not None
        assert "Free gift" in line.promotion_description

    def test_apply_promotion_multiple_items(self):
        """Test applying promotions to multiple items."""
        # Create an Order object
        order = Order(
            email_id="test@example.com",
            overall_status="created",
            lines=[
                OrderLine(
                    product_id="TST001",
                    name="Test Shirt",
                    description="Test Shirt",
                    quantity=2,
                    base_price=50.0,
                    unit_price=50.0,
                    total_price=100.0,
                ),
                OrderLine(
                    product_id="TST002",
                    name="Test Pants",
                    description="Test Pants",
                    quantity=1,
                    base_price=100.0,
                    unit_price=100.0,
                    total_price=100.0,
                ),
            ],
            total_price=200.0,
        )

        promotion_specs = [
            {
                "description": "10% off shirts",
                "conditions": {"min_quantity": 1},
                "effects": {
                    "apply_discount": {
                        "type": "percentage",
                        "amount": 10.0,
                        "to_product_id": "TST001",
                    }
                },
            }
        ]

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # Verify result
        assert isinstance(result, Order)
        assert result.email_id == "test@example.com"
        assert result.overall_status == "created"
        assert len(result.lines) == 2

        # Check the first line (should have discount)
        shirt_line = result.lines[0]
        assert shirt_line.product_id == "TST001"
        assert shirt_line.unit_price == 45.0  # 10% discount
        assert shirt_line.promotion_applied

        # Check the second line (should not have discount)
        pants_line = result.lines[1]
        assert pants_line.product_id == "TST002"
        assert pants_line.unit_price == 100.0  # No discount
        assert not pants_line.promotion_applied

    def test_apply_promotion_invalid_input(self):
        """Test applying promotions with invalid input."""
        # Create an Order object
        order = Order(
            email_id="test@example.com",
            overall_status="created",
            lines=[],
            total_price=0.0,
        )

        promotion_specs = []

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # Verify result
        assert isinstance(result, Order)
        assert result.email_id == "test@example.com"
        assert len(result.lines) == 0
        assert result.total_discount == 0.0
        assert result.total_price == 0.0


class TestPromotionToolsWithTestData:
    """Tests for promotion_tools using test data from CSV."""

    def create_order_from_test_products(self):
        """Create an Order object using actual product data from products.csv."""
        # Load products from actual data (not test fixtures)
        from hermes.data.load_data import load_products_df

        products_df = load_products_df()

        # Extract a few products with known promotions mentioned in descriptions
        order_lines = []

        # QTP5432 - Quilted Tote with "Limited-time sale - get 25% off!"
        tote_row = products_df[products_df["product_id"] == "QTP5432"].iloc[0]
        order_lines.append(
            OrderLine(
                product_id="QTP5432",
                name=tote_row["name"],
                description=tote_row["name"],
                quantity=1,
                base_price=float(tote_row["price"]),
                unit_price=float(tote_row["price"]),
                total_price=float(tote_row["price"]),
            )
        )

        # CBG9876 - Canvas Beach Bag with "Buy one, get one 50% off!"
        bag_row = products_df[products_df["product_id"] == "CBG9876"].iloc[0]
        bag_price = float(bag_row["price"])
        order_lines.append(
            OrderLine(
                product_id="CBG9876",
                name=bag_row["name"],
                description=bag_row["name"],
                quantity=2,  # Order 2 to trigger BOGO
                base_price=bag_price,
                unit_price=bag_price,
                total_price=bag_price * 2,
            )
        )

        # Regular product with no promotion
        regular_row = products_df[products_df["product_id"] == "RSG8901"].iloc[0]
        regular_price = float(regular_row["price"])
        order_lines.append(
            OrderLine(
                product_id="RSG8901",
                name=regular_row["name"],
                description=regular_row["name"],
                quantity=1,
                base_price=regular_price,
                unit_price=regular_price,
                total_price=regular_price,
            )
        )

        total_price = sum(line.total_price for line in order_lines)

        return Order(
            email_id="test@example.com",
            overall_status="created",
            lines=order_lines,
            total_price=total_price,
        )

    def test_apply_percentage_promotion_with_test_data(self):
        """Test applying a percentage discount promotion with test product data."""
        # Create order with test products
        order = self.create_order_from_test_products()

        # Get only the Quilted Tote line
        tote_line = next(line for line in order.lines if line.product_id == "QTP5432")
        order.lines = [tote_line]
        order.total_price = tote_line.total_price

        promotion_specs = [
            {
                "description": "25% off Quilted Tote",
                "conditions": {"min_quantity": 1},
                "effects": {
                    "apply_discount": {
                        "type": "percentage",
                        "amount": 25.0,
                        "to_product_id": "QTP5432",
                    }
                },
            }
        ]

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # The result should be an Order object
        assert isinstance(result, Order)
        assert result.email_id == "test@example.com"
        assert len(result.lines) == 1

        # Check line details
        line = result.lines[0]
        assert line.product_id == "QTP5432"
        base_price = tote_line.base_price

        # Expect 25% off
        expected_discounted_price = base_price * 0.75
        assert line.unit_price is not None
        assert (
            abs(line.unit_price - expected_discounted_price) < 0.01
        )  # Use pytest.approx or abs for float comparison
        assert line.promotion_applied

    def test_apply_bogo_promotion_with_test_data(self):
        """Test applying a BOGO promotion with test product data."""
        # Create order with test products
        order = self.create_order_from_test_products()

        # Get only the Canvas Beach Bag line
        bag_line = next(line for line in order.lines if line.product_id == "CBG9876")
        order.lines = [bag_line]
        order.total_price = bag_line.total_price

        promotion_specs = [
            {
                "description": "Buy one get one 50% off beach bags",
                "conditions": {"min_quantity": 2},
                "effects": {
                    "apply_discount": {
                        "type": "percentage",
                        "amount": 25.0,  # 25% off each item = 50% off one of two items
                        "to_product_id": "CBG9876",
                    }
                },
            }
        ]

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # The result should be an Order object
        assert isinstance(result, Order)
        assert len(result.lines) == 1

        # Check line details
        line = result.lines[0]
        assert line.product_id == "CBG9876"
        base_price = bag_line.base_price
        quantity = bag_line.quantity
        assert quantity == 2

        # For BOGO 50% off with 2 items, we're applying 25% off each item
        expected_discount = base_price * 0.25 * quantity
        expected_total = base_price * quantity - expected_discount

        assert result.total_discount is not None
        assert (
            abs(result.total_discount - expected_discount) < 0.01
        )  # Use pytest.approx or abs for float comparison
        assert result.total_price is not None
        assert (
            abs(result.total_price - expected_total) < 0.01
        )  # Use pytest.approx or abs for float comparison
        assert line.promotion_applied

    def test_apply_multiple_promotions_with_test_data(self):
        """Test applying multiple promotions to different products."""
        # Create order with all test products
        order = self.create_order_from_test_products()

        promotion_specs = [
            {
                "description": "25% off Quilted Tote",
                "conditions": {"min_quantity": 1},
                "effects": {
                    "apply_discount": {
                        "type": "percentage",
                        "amount": 25.0,
                        "to_product_id": "QTP5432",
                    }
                },
            },
            {
                "description": "Buy one get one 50% off beach bags",
                "conditions": {"min_quantity": 2},
                "effects": {
                    "apply_discount": {
                        "type": "percentage",
                        "amount": 25.0,
                        "to_product_id": "CBG9876",
                    }
                },
            },
        ]

        # Call function with new signature
        result = apply_promotion(
            order=order,
            promotion_specs=promotion_specs,
        )

        # The result should be an Order object
        assert isinstance(result, Order)
        assert len(result.lines) == 3

        # Check that promotions were applied to the right products
        tote_line = next(line for line in result.lines if line.product_id == "QTP5432")
        bag_line = next(line for line in result.lines if line.product_id == "CBG9876")
        regular_line = next(
            line for line in result.lines if line.product_id == "RSG8901"
        )

        # Tote should have 25% discount
        assert tote_line.promotion_applied
        assert tote_line.unit_price is not None
        assert tote_line.base_price is not None
        assert tote_line.unit_price < tote_line.base_price

        # Bag should have 25% discount (BOGO effect)
        assert bag_line.promotion_applied
        assert bag_line.unit_price is not None
        assert bag_line.base_price is not None
        assert bag_line.unit_price < bag_line.base_price

        # Regular product should have no discount
        assert not regular_line.promotion_applied
