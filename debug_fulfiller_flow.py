#!/usr/bin/env python3

from hermes.model.order import Order, OrderLine, OrderLineStatus
from hermes.model.promotions import (
    PromotionSpec,
    PromotionConditions,
    PromotionEffects,
    DiscountSpec,
)
from hermes.tools.promotion_tools import apply_promotion


def simulate_fulfiller_flow():
    # Step 1: Simulate what the LLM might return
    print("=== Step 1: LLM Creates Order ===")

    # This simulates what the LLM might create based on the prompt
    llm_order = Order(
        email_id="test_002",
        overall_status="created",
        lines=[
            OrderLine(
                product_id="QTP5432",
                description="Quilted Tote",
                quantity=1,
                base_price=29.0,
                unit_price=29.0,  # LLM sets this to base_price initially
                total_price=29.0,  # LLM calculates 1 * 29.0
                status=None,  # Will be set by agent later
                promotion_applied=False,  # LLM doesn't apply promotions
                promotion_description="Limited-time sale - get 25% off!",  # LLM might set this
            )
        ],
        total_price=29.0,  # LLM calculates total
        total_discount=0.0,  # LLM starts with 0 discount
    )

    print(f"LLM Order - Line unit_price: ${llm_order.lines[0].unit_price}")
    print(f"LLM Order - Total price: ${llm_order.total_price}")
    print(f"LLM Order - Total discount: ${llm_order.total_discount}")

    # Step 2: Agent processes items and updates totals
    print("\n=== Step 2: Agent Processes Stock ===")

    # Simulate stock processing
    for item in llm_order.lines:
        item.status = OrderLineStatus.CREATED  # Stock available

    # Agent recalculates total_amount based on current item prices
    total_amount = 0.0
    for item in llm_order.lines:
        total_amount += (item.unit_price or item.base_price) * item.quantity

    llm_order.total_price = total_amount  # Agent overwrites LLM total

    print(f"After Stock Processing - Line unit_price: ${llm_order.lines[0].unit_price}")
    print(f"After Stock Processing - Total price: ${llm_order.total_price}")
    print(f"After Stock Processing - Total discount: ${llm_order.total_discount}")

    # Step 3: Apply promotions
    print("\n=== Step 3: Apply Promotions ===")

    promotion_spec = PromotionSpec(
        conditions=PromotionConditions(min_quantity=1),
        effects=PromotionEffects(
            apply_discount=DiscountSpec(
                type="percentage", amount=25.0, to_product_id="QTP5432"
            )
        ),
    )

    print(f"Before promotion - Line unit_price: ${llm_order.lines[0].unit_price}")
    print(f"Before promotion - Total price: ${llm_order.total_price}")
    print(f"Before promotion - Total discount: ${llm_order.total_discount}")

    final_order = apply_promotion(
        order=llm_order,
        promotion_specs=[promotion_spec],
    )

    print(f"\nAfter promotion - Line unit_price: ${final_order.lines[0].unit_price}")
    print(f"After promotion - Line total_price: ${final_order.lines[0].total_price}")
    print(f"After promotion - Total price: ${final_order.total_price}")
    print(f"After promotion - Total discount: ${final_order.total_discount}")
    print(
        f"After promotion - Promotion applied: {final_order.lines[0].promotion_applied}"
    )
    print(
        f"After promotion - Promotion description: {final_order.lines[0].promotion_description}"
    )

    print(f"\n=== Summary ===")
    print(f"Expected discount: ${29.0 * 0.25}")
    print(f"Actual discount: ${final_order.total_discount}")
    print(f"Difference: ${abs(final_order.total_discount - 29.0 * 0.25)}")

    expected_unit_price = 29.0 - (29.0 * 0.25)
    print(f"Expected unit price: ${expected_unit_price}")
    print(f"Actual unit price: ${final_order.lines[0].unit_price}")
    print(
        f"Unit price difference: ${abs(final_order.lines[0].unit_price - expected_unit_price)}"
    )


if __name__ == "__main__":
    simulate_fulfiller_flow()
