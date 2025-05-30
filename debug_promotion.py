#!/usr/bin/env python3

from hermes.tools.promotion_tools import apply_promotion
from hermes.model.order import Order, OrderLine
from hermes.model.promotions import (
    PromotionSpec,
    PromotionConditions,
    PromotionEffects,
    DiscountSpec,
)

# Create a simple order with all required fields
order = Order(
    email_id="test",
    overall_status="created",
    lines=[
        OrderLine(
            product_id="QTP5432",
            description="Quilted Tote",
            quantity=1,
            base_price=29.0,
            unit_price=29.0,
            total_price=29.0,
        )
    ],
    total_price=29.0,
    total_discount=0.0,
)

# Create a 25% off promotion
promotion = PromotionSpec(
    conditions=PromotionConditions(min_quantity=1),
    effects=PromotionEffects(
        apply_discount=DiscountSpec(
            type="percentage", amount=25.0, to_product_id="QTP5432"
        )
    ),
)

print("Before promotion:")
print(f"Base price: ${order.lines[0].base_price}")
print(f"Unit price: ${order.lines[0].unit_price}")
print(f"Total discount: ${order.total_discount}")

# Apply promotion
result = apply_promotion(order, [promotion])

print("\nAfter promotion:")
print(f"Base price: ${result.lines[0].base_price}")
print(f"Unit price: ${result.lines[0].unit_price}")
print(f"Total discount: ${result.total_discount}")
print(f"Expected discount: ${29.0 * 0.25}")
print(f"Actual discount: ${result.total_discount}")
print(f"Difference: ${abs(result.total_discount - 29.0 * 0.25)}")
print(f"Promotion applied: {result.lines[0].promotion_applied}")
print(f"Promotion description: {result.lines[0].promotion_description}")
